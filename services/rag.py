"""RAG 파이프라인 구성 모듈

FirestoreVectorStore + LangChain으로 RAG 체인을 생성한다.

사용 예시
---------
from services.rag import get_rag_chain

rag_chain = get_rag_chain()
result = rag_chain.invoke("아토피 피부염 관리 방법?")
print(result.content)
"""

from __future__ import annotations

import os
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore

from services.firestore_vector import FirestoreVectorStore

# ---- 환경 변수 ----
GCP_PROJECT = os.getenv("GCP_PROJECT")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

from functools import lru_cache

# ---- Vector Store & RAG 체인 Lazy 생성 ----
@lru_cache(maxsize=1)
def _build_rag_chain():
    """환경 변수를 확인하고 RAG 체인을 1회만 생성한다."""
    if not GCP_PROJECT or not GEMINI_API_KEY:
        raise RuntimeError("GCP_PROJECT 또는 GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", api_key=GEMINI_API_KEY)
    vector_store = FirestoreVectorStore(embedding=embeddings, project_id=GCP_PROJECT)
    retriever = vector_store.as_retriever(k=4)

    return (
        RunnableParallel({"context": retriever, "question": RunnablePassthrough()})
        | (lambda d: {"context": "\n".join([doc.page_content for doc in d["context"]]), "question": d["question"]})
        | (lambda d: _prompt.format(**d, output_schema=_OUTPUT_SCHEMA))
        | ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.2, api_key=GEMINI_API_KEY)
    )

# ---- Prompt ----
_TEMPLATE = (
    "너는 피부과 전문의 AI 어시스턴트다. 제공된 참고 문서를 바탕으로 질문에 답해라.\n"
    "문맥(참고 문서):\n{context}\n\n"
    "질문: {question}\n\n"
    "다음 JSON 형식으로만 대답해. 다른 설명은 금지.\n"
    "{output_schema}"
)

_OUTPUT_SCHEMA = """{
    "diagnosis_name": "질병명(한국어)",
    "ai_opinion": "요약 및 핵심 권장사항(1-2문장)",
    "detailed_description": "정의|특징|원인을 포함한 설명",
    "precautions": ["주의점1", "주의점2", "주의점3"],
    "management": {
        "보습관리": "...",
        "청결관리": "...",
        "환경관리": "...",
        "의복관리": "..."
    }
}"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _TEMPLATE),
])



def get_rag_chain():
    """외부에서 호출할 수 있도록 Lazy RAG 체인을 반환"""
    return _build_rag_chain()


def generate_disease_info(disease_name: str) -> Dict[str, Any]:
    """질병명을 입력받아 RAG 기반 JSON 정보를 반환"""
    res = get_rag_chain().invoke(disease_name)
    import json

    # 응답에서 첫 번째 JSON 블록 추출
    import re

    text = res.content if hasattr(res, "content") else str(res)

    # LLM 응답에서 JSON 블록 추출 (```json ... ```)
    match = re.search(r"```json[\r\n]+([\s\S]*?)```", text)
    json_str = match.group(1) if match else text

    # JSON 파싱 시 예외 처리로 안정성 강화
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # LLM 반환 형식 오류 시 명확한 예외 전달
        raise ValueError("모델 응답에서 JSON 파싱 실패") from e
