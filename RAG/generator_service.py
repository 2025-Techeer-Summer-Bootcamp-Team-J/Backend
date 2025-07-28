"""RAG 파이프라인 모듈

FirestoreVectorStore와 Gemini 기반 LLM을 활용하여 질병 정보를 생성합니다.
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

import google.generativeai as genai
from langchain.prompts import ChatPromptTemplate

from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore

from RAG.vector_store import FirestoreVectorStore

from functools import lru_cache
from PIL import Image
import io
import re

# RAG prompt & schema
from RAG.prompt import OUTPUT_SCHEMA as _OUTPUT_SCHEMA, PROMPT as _prompt

logger = logging.getLogger(__name__)

# ---- 유틸 함수 ----

def _clean_context(context: str, max_chars: int = 4000) -> str:
    """Markdown 헤더·공백 제거 후 최대 길이로 자르기"""
    # 헤더 제거
    cleaned = re.sub(r"^#+ .*", "", context, flags=re.MULTILINE)
    # 공백 줄 2개 이상 → 1개
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    return cleaned[:max_chars]


def _resize_image_to_512(image: Image.Image) -> Image.Image:
    """가장 긴 변을 512px로 리사이즈 (PIL 이미지 반환)"""
    w, h = image.size
    if max(w, h) <= 512:
        return image
    ratio = 512 / max(w, h)
    new_size = (int(w * ratio), int(h * ratio))
    return image.resize(new_size, Image.LANCZOS)

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

    # google-generativeai 설정
    genai.configure(api_key=GEMINI_API_KEY.get_secret_value() if hasattr(GEMINI_API_KEY, "get_secret_value") else GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    logger.info("Retriever 및 LLM 초기화 완료.")
    return retriever, model




def generate_disease_info(image_bytes: bytes, disease_name: str, symptoms: str | None = None) -> Dict[str, Any]:
    """이미지 바이트와 질병명을 받아 RAG + 이미지 분석 JSON 반환"""
    retriever, model = _get_retriever_and_llm()

    logger.info("컨텍스트 문서를 검색합니다...")
    docs = retriever.invoke(disease_name)
    raw_context = "\n".join([doc.page_content for doc in docs])
    context_str = _clean_context(raw_context)

    symptoms_text = symptoms if symptoms else "증상 정보 없음"
    prompt_str = _prompt.format(context=context_str, symptoms=symptoms_text, question=disease_name, output_schema=_OUTPUT_SCHEMA)

    logger.info("LLM 호출(이미지 + 텍스트) 시작...")
    # 이미지 리사이즈
    image = Image.open(io.BytesIO(image_bytes))
    image = _resize_image_to_512(image)

    # 증상 텍스트가 없으면 텍스트-only 호출로 분기
    if symptoms_text.strip() == "증상 정보 없음":
        res = model.generate_content(prompt_str)
    else:
        res = model.generate_content([prompt_str, image])
    logger.info("LLM 응답 수신. JSON 파싱 시도...")

    import json, re
    # Gemini SDK 응답에서 텍스트 추출
    if hasattr(res, "text") and res.text:
        text = res.text
    elif getattr(res, "candidates", None):
        first = res.candidates[0]
        text = first.content.parts[0].text if first.content.parts else ""
    else:
        text = str(res)

    match = re.search(r"```json[\r\n]+([\s\S]*?)```", text)
    json_str = match.group(1) if match else text

    try:
        parsed_json = json.loads(json_str)
        logger.info("JSON 파싱 성공!")
        return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"모델 응답에서 JSON 파싱 실패. 원본 응답: {text}")
        raise ValueError("모델 응답에서 JSON 파싱 실패") from e
