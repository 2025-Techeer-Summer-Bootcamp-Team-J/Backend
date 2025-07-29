"""crawl_to_firestore.py

지정한 CSV 또는 텍스트 파일에서 (disease_name, url, 기관명) 정보를 읽어
웹 페이지를 크롤링한 뒤 스키마에 맞게 Firestore `diseases` 컬렉션에 저장합니다.

사용 예시:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    python scripts/crawl_to_firestore.py --input urls.csv

CSV 형식:
    disease_name,url,기관명

필드 설명:
    disease_name : 질병명 (예: Eczema)
    url          : 크롤링할 페이지 URL
    기관명       : 출처 기관명 (예: 질병관리청)
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup  # type: ignore
from dotenv import load_dotenv # noqa: E402

# 내부 서비스 모듈 path 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))  # project root

from RAG.disease_store import DiseaseStore  # noqa: E402
from langchain_google_genai import GoogleGenerativeAIEmbeddings  # noqa: E402
from RAG.vector_store import FirestoreVectorStore  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}


def clean_text(html: str) -> str:
    """HTML → 깨끗한 텍스트로 단순 변환."""
    soup = BeautifulSoup(html, "html.parser")

    # script, style, noscript 태그 제거
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)

    # 연속 공백 줄 정리
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def extract_first_image_url(html: str, base_url: str | None = None) -> str:
    soup = BeautifulSoup(html, "html.parser")
    img = soup.find("img")
    if not img or not img.get("src"):
        return ""
    src = img["src"]
    # 절대 URL 보정
    if src.startswith("//"):
        src = "https:" + src
    elif src.startswith("/") and base_url:
        from urllib.parse import urljoin

        src = urljoin(base_url, src)
    return src


def crawl_page(url: str) -> Dict[str, str] | None:
    """url 의 HTML, main text, 대표 이미지 src 반환."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
        text = clean_text(html)

        # Firestore의 단일 문서 크기 제한(1MiB)을 초과하지 않도록 텍스트를 자릅니다.
        # 1MiB = 1,048,576 bytes. 여유를 두어 900,000 바이트로 제한합니다.
        max_bytes = 900000
        if len(text.encode("utf-8")) > max_bytes:
            logger.warning("크롤링한 텍스트가 너무 길어 자릅니다: %s", url)
            # utf-8 멀티바이트 문자가 잘리지 않도록 디코딩 후 다시 인코딩하여 자릅니다.
            text = text.encode("utf-8")[:max_bytes].decode("utf-8", "ignore")
        photo_url = extract_first_image_url(html, base_url=url)
        return {"html": html, "text": text, "photo_url": photo_url}
    except requests.exceptions.RequestException as e:
        logging.warning(f"크롤링 실패: {url} - {e}")
        return None


def process_row(row: Dict[str, str]) -> Dict[str, object] | None:
    disease_name = (row.get("disease_name") or "").strip()
    url = (row.get("url") or "").strip()
    if not disease_name or not url:
        logger.warning("필수 필드(disease_name, url) 누락 → 건너뜀: %s", row)
        return None
    source_name = row.get("기관명", "") or row.get("source", "")
    logger.info("크롤링: %s (%s)", disease_name, url)
    page = crawl_page(url)
    if not page:
        return None  # 크롤링 실패 시 건너뛰기

    # 스키마 변환 (placeholder 필드 채우기)
    doc = {
        "disease_name": disease_name,
        "photo_url": page["photo_url"],
        "detailed_description": page["text"],
        "precautions": [],  # 추후 LLM 또는 파싱으로 채움
        "management": {
            "일상 관리법(가정에서의 피부 관리, 샤워법 등)": "",
            "의학적 치료법(연고, 경구약, 물리치료 등)": "",
            "생활습관(재발 방지법, 환경 개선법)": "",
            "기타": "",
        },
        "출처": {
            "기관명": source_name,
            "url": url,
        },
    }
    return doc


def load_csv(input_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_columns = {"disease_name", "url"}
        if not required_columns.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV에 컬럼 {required_columns} 가 필요합니다.")
        for row in reader:
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="질병 페이지 크롤링 후 Firestore에 저장")
    parser.add_argument("--input", required=True, help="CSV 파일 경로")
    args = parser.parse_args()

    csv_path = Path(args.input)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    # .env 파일에서 환경 변수 로드 (GEMINI_API_KEY)
    load_dotenv()

    store = DiseaseStore()

    rows = load_csv(csv_path)
    docs = [doc for r in rows if (doc := process_row(r)) is not None]
    if not docs:
        logger.info("저장할 문서가 없습니다.")
        return

    # 1. 질병 정보 저장
    doc_ids = store.add_documents(docs)
    # 각 문서 dict에 Firestore 문서 ID 주입
    for doc, _id in zip(docs, doc_ids):
        doc["doc_id"] = _id
    logger.info("업로드 완료: %d 건", len(docs))

    # 2. 저장된 문서 내용으로 임베딩 생성 및 저장
    logger.info("이제 저장된 문서들의 임베딩을 생성합니다...")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수를 찾을 수 없습니다.")

    embedding_model = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001", google_api_key=gemini_api_key
    )
    vector_store = FirestoreVectorStore(embedding=embedding_model)
    # 저장된 문서들 중, 임베딩할 내용(detailed_description)이 있는 것만 필터링
    docs_to_embed = [doc for doc in docs if doc.get('detailed_description')]
    if not docs_to_embed:
        logger.warning("임베딩할 문서가 없습니다. 모든 문서의 detailed_description이 비어있습니다.")
        return

    logger.info(f"총 {len(docs)}개 문서 중 {len(docs_to_embed)}개의 문서에 대해 임베딩을 생성합니다.")

    texts_to_embed = [doc['detailed_description'] for doc in docs_to_embed]
    metadatas = [
        {
            "doc_id": doc["doc_id"],
            "disease_name": doc["disease_name"],
            "url": doc["출처"]["url"],
        }
        for doc in docs_to_embed
    ]
    vector_store.add_texts(
        texts=texts_to_embed,
        metadatas=metadatas,
        batch_size=5  # Gemini API 동시 요청 제한 고려
    )
    logger.info("임베딩 저장 완료: %d 건", len(texts_to_embed))


if __name__ == "__main__":
    main()
