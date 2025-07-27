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
from PIL import Image
import io

logger = logging.getLogger(__name__)

# ---- Retriever & LLM Lazy 생성 ----
@lru_cache(maxsize=1)
def _get_retriever_and_llm():
    """임베딩 Retriever와 Gemini LLM을 1회만 초기화해 재사용"""
    logger.info("(once) Retriever & LLM 초기화합니다…")
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

    logger.info("Retriever & LLM 초기화 완료.")
    return retriever, llm

# ---- Prompt ----
_TEMPLATE = (
    "너는 피부과 전문의 AI 어시스턴트다. 제공된 참고 문서를 바탕으로 질문에 답해라.\n"
    "문맥(참고 문서):\n{context}\n\n"
    "질문: {question}\n\n"
    "다음 JSON 형식으로만 대답해. 다른 설명은 금지.\n"
    "{output_schema}"
)

_OUTPUT_SCHEMA = """{
    "image_analysis": {
        "skin_score": "(예시: 1~100사이의 정수)",
        "estimated_treatment_period": "(예시: 2-4주등 의 기간)"
    },
    "disease_name": "질병명(한국어)",
    "photo_url": "신뢰할 수 있는 사이트의 사진 URL",
    "detailed_description": "정의|특징(증상)|원인을 포함한 설명",
    "precautions": ["주의점1", "주의점2", "주의점3"],
    "management": {
        "일상 관리법(가정에서의 피부 관리, 샤워법 등)": "",
        "의학적 치료법(연고, 경구약, 물리치료 등)": "",
        "생활습관(재발 방지법, 환경 개선법)": "",
        "기타": ""
    },
    "출처": {
        "기관명": "",
        "출처url": ""
    }
}"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _TEMPLATE),
])


def generate_disease_info(image_bytes: bytes, disease_name: str) -> Dict[str, Any]:
    """이미지 바이트와 질병명을 받아 RAG + 이미지 분석 JSON 반환"""
    retriever, llm = _get_retriever_and_llm()

    logger.info("컨텍스트 문서를 검색합니다...")
    docs = retriever.invoke(disease_name)
    context_str = "\n".join([doc.page_content for doc in docs])

    prompt_str = _prompt.format(context=context_str, question=disease_name, output_schema=_OUTPUT_SCHEMA)

    logger.info("LLM 호출(이미지 + 텍스트) 시작...")
    image = Image.open(io.BytesIO(image_bytes))
    res = llm.invoke([prompt_str, image])
    logger.info("LLM 응답 수신. JSON 파싱 시도...")

    import json, re
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


