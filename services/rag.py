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
from pydantic.v1.types import SecretStr

# ---- SecretStr → str 우회 패치 ----

def _to_str(val: str | SecretStr | None) -> str:
    if isinstance(val, SecretStr):
        return val.get_secret_value()
    return val or ""

os.environ["GOOGLE_API_KEY"] = _to_str(os.getenv("GOOGLE_API_KEY"))
os.environ["GEMINI_API_KEY"] = _to_str(os.getenv("GEMINI_API_KEY"))

import os
import logging
from typing import Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableParallel, RunnablePassthrough
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore

from services.firestore_vector import FirestoreVectorStore

from functools import lru_cache

logger = logging.getLogger(__name__)

# ---- Vector Store & RAG 체인 Lazy 생성 ----
@lru_cache(maxsize=1)
def _build_rag_chain():
    """환경 변수를 확인하고 RAG 체인을 1회만 생성한다."""
    logger.info("RAG 체인 생성을 시작합니다 (최초 1회 실행)...")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

    logger.info("  - 임베딩 모델(embedding-001)을 초기화합니다.")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GEMINI_API_KEY.get_secret_value() if hasattr(GEMINI_API_KEY, "get_secret_value") else GEMINI_API_KEY
    )
    
    logger.info("  - Firestore 벡터 스토어를 초기화합니다.")
    vector_store = FirestoreVectorStore(embedding=embeddings)
    retriever = vector_store.as_retriever(k=4)
    logger.info("  - Retriever(문서 검색기)를 생성했습니다.")

    # SecretStr가 하위 gRPC 라이브러리에서 문제를 일으키므로, .get_secret_value()로 일반 str을 추출합니다.
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro", 
        temperature=0.2, 
        google_api_key=GEMINI_API_KEY.get_secret_value() if hasattr(GEMINI_API_KEY, "get_secret_value") else GEMINI_API_KEY
    )

    chain = (
        RunnableParallel({"context": retriever, "question": RunnablePassthrough()})
        | (lambda d: {"context": "\n".join([doc.page_content for doc in d["context"]]), "question": d["question"]})
        | (lambda d: _prompt.format(**d, output_schema=_OUTPUT_SCHEMA))
        | llm
    )
    logger.info("RAG 체인 생성을 완료했습니다.")
    return chain

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
    logger.info("RAG 체인을 가져옵니다...")
    rag_chain = get_rag_chain()
    
    logger.info(f'RAG 체인 실행을 시작합니다. 질문: "{disease_name}"')
    res = rag_chain.invoke(disease_name)
    logger.info("RAG 체인 실행 완료. 응답을 파싱합니다...")
    
    import json
    import re

    text = res.content if hasattr(res, "content") else str(res)

    match = re.search(r"```json[\r\n]+([\s\S]*?)```", text)
    json_str = match.group(1) if match else text

    try:
        parsed_json = json.loads(json_str)
        logger.info("JSON 파싱 성공!")
        return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"모델 응답에서 JSON 파싱 실패. 원본 응답: {text}")
        raise ValueError("모델 응답에서 JSON 파싱 실패") from e
