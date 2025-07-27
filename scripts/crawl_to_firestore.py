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

# 내부 서비스 모듈 path 추가
sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.disease_store import DiseaseStore  # noqa: E402

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
    # 스크립트, 스타일 제거
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
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


def crawl_page(url: str) -> Dict[str, str]:
    """url 의 HTML, main text, 대표 이미지 src 반환."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    html = resp.text
    text = clean_text(html)
    photo_url = extract_first_image_url(html, base_url=url)
    return {"html": html, "text": text, "photo_url": photo_url}


def process_row(row: Dict[str, str]) -> Dict[str, object]:
    disease_name = row["disease_name"].strip()
    url = row["url"].strip()
    source_name = row.get("기관명", "") or row.get("source", "")
    logger.info("크롤링: %s (%s)", disease_name, url)
    page = crawl_page(url)

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

    store = DiseaseStore()

    rows = load_csv(csv_path)
    docs = [process_row(r) for r in rows]
    store.add_documents(docs)
    logger.info("업로드 완료: %d 건", len(docs))


if __name__ == "__main__":
    main()
