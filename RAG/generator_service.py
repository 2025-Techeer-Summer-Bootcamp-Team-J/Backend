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
import asyncio

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
def _get_retriever_and_llm(model_name: str | None = None):
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
    chosen_model = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    model = genai.GenerativeModel(chosen_model)
    logger.info("Retriever 및 LLM 초기화 완료.")
    return retriever, model




@lru_cache(maxsize=128)
def _get_context_from_store(disease_name: str) -> str:
    """Firestore retriever 결과를 캐싱 (LRU)"""
    retriever, _ = _get_retriever_and_llm()
    docs = retriever.invoke(disease_name)
    raw = "\n".join([d.page_content for d in docs])
    return _clean_context(raw)


def _image_hash(image_bytes: bytes) -> str:
    import hashlib
    return hashlib.sha1(image_bytes).hexdigest()

@lru_cache(maxsize=64)
def _cached_llm_response(img_hash: str, disease_name: str, symptoms_text: str) -> Dict[str, Any]:
    """LLM 응답 캐싱: key = (img_hash, disease_name, symptoms_text)"""
    # 이 함수는 generate_disease_info 내부에서 처음 호출될 때만 실행되며,
    # 실제 LLM 호출 로직은 여기서 수행된다.
    retriever, model = _get_retriever_and_llm()  # 재사용
    context_str = _get_context_from_store(disease_name)

    prompt_str = _prompt.format(
        context=context_str,
        symptoms=symptoms_text,
        question=disease_name,
        output_schema=_OUTPUT_SCHEMA,
    )

    if symptoms_text.strip() == "증상 정보 없음":
        res = model.generate_content(prompt_str)
    else:
        # img_hash 는 generate_disease_info 에서 리사이즈된 이미지 바이트로 계산됨
        from PIL import Image
        import io, base64
        img_bytes = base64.b16decode(img_hash.encode())  # dummy to satisfy type; actual bytes 전달은 외부
        image = Image.open(io.BytesIO(img_bytes))
        res = model.generate_content([prompt_str, image])

    # 응답 파싱 (텍스트 → JSON)
    if hasattr(res, "text") and res.text:
        text = res.text
    elif getattr(res, "candidates", None):
        first = res.candidates[0]
        text = first.content.parts[0].text if first.content.parts else ""
    else:
        text = str(res)
    import json, re as _re
    match = _re.search(r"```json[\r\n]+([\s\S]*?)```", text)
    json_str = match.group(1) if match else text
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {"raw": text}


def generate_disease_info(image_bytes: bytes, disease_name: str, symptoms: str | None = None) -> Dict[str, Any]:
    """이미지 바이트와 질병명을 받아 RAG + 이미지 분석 JSON 반환"""
    retriever, model = _get_retriever_and_llm()

    # ---- 캐싱된 컨텍스트 사용 ----
    context_str = _get_context_from_store(disease_name)

    symptoms_text = symptoms if symptoms else "증상 정보 없음"
    prompt_str = _prompt.format(context=context_str, symptoms=symptoms_text, question=disease_name, output_schema=_OUTPUT_SCHEMA)

    logger.info("LLM 호출(이미지 + 텍스트) 시작...")
    # 이미지 리사이즈
    image = Image.open(io.BytesIO(image_bytes))
    image = _resize_image_to_512(image)
    # 캐시 키용 해시
    img_bytes_resized = io.BytesIO()
    image.save(img_bytes_resized, format="PNG")
    img_hash_val = _image_hash(img_bytes_resized.getvalue())

    # ---- LLM 응답 캐싱 ----
    cached = _cached_llm_response(img_hash_val, disease_name, symptoms_text)
    if cached:
        return cached

    # 캐시 미스 시 실제 호출 (텍스트-only 분기 포함)
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

# ---- Async Wrapper ----
async def async_generate_disease_info(image_bytes: bytes, disease_name: str, symptoms: str | None = None) -> Dict[str, Any]:
    """FastAPI 엔드포인트용 비동기 래퍼 (쓰레드 오프로딩)"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_disease_info, image_bytes, disease_name, symptoms)
