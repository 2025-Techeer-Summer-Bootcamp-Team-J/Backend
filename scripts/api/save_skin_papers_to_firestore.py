"""save_skin_papers_to_firestore.py

피부질환 관련 키워드(질병명) 리스트를 대상으로 Semantic Scholar에서 인용수 300 이상인 논문
메타데이터를 수집해 Firestore `papers` 컬렉션에 저장합니다.

Usage:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    export SEMANTIC_SCHOLAR_API_KEY=your_key   # 없으면 비인증 요청

    python scripts/save_skin_papers_to_firestore.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, List, Set
from datetime import datetime, timezone
from time import sleep

from dotenv import load_dotenv  # type: ignore

# ---- 프로젝트 루트 path 조정 ----
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from RAG.scholar import bulk_search_scholar  # noqa: E402
from RAG.paper_store import PaperStore  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DISEASE_QUERIES: List[str] = [
    "Eczema",
    "Warts, Molluscum and other Viral Infections",
    "Melanoma",
    "Atopic Dermatitis",
    "Basal Cell Carcinoma",
    "Melanocytic Nevi",
    "Benign Keratosis-like Lesions",
    "Psoriasis, Lichen Planus and related diseases",
    "Seborrheic Keratoses",
    "Tinea/Ringworm/Candidiasis",
    "Dermatofibroma",
    "Actinic Keratosis",
    "Vascular Malformations",
    "Acne",
    "Vitiligo",
    "Hyperpigmentation",
]

DEFAULT_MIN_CITATIONS = 300
DEFAULT_PAGE_LIMIT = 1000  # 최초 검색 시 최대 1000건까지 토큰 페이지네이션 포함
DEFAULT_SLEEP_SECS = 1.5   # API 남용 방지


def _build_docs(data: List[Dict[str, object]], query: str) -> List[Dict[str, object]]:
    """검색 결과를 Firestore 스키마로 변환"""
    ts = datetime.now(timezone.utc)
    docs: List[Dict[str, object]] = []
    for p in data:
        docs.append(
            {
                "title": p.get("title", ""),
                "year": p.get("year"),
                "citationCount": p.get("citationCount", 0),
                "openAccessPdf": p.get("openAccessPdf"),
                "query": query,
                "createdAt": ts,
            }
        )
    return docs


def _parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="피부 질환 관련 논문 메타데이터를 Firestore에 저장"
    )
    parser.add_argument(
        "--min_citations",
        type=int,
        default=DEFAULT_MIN_CITATIONS,
        help="논문 최소 인용 수 필터",
    )
    parser.add_argument(
        "--page_limit",
        type=int,
        default=DEFAULT_PAGE_LIMIT,
        help="API 호출 시 limit 값 (1~1000)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_SLEEP_SECS,
        help="API 호출 간 대기 시간(초)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    load_dotenv()

    store = PaperStore()
    seen_titles: Set[str] = set()
    total_saved = 0

    for q in DISEASE_QUERIES:
        logger.info("=== 질병명 검색: %s ===", q)
        results = bulk_search_scholar(
            q, limit=args.page_limit, min_citations=args.min_citations
        )
        logger.info("검색 결과: %d건", len(results))

        # Firestore 저장 전 중복 제거
        new_items = []
        for p in results:
            title = p.get("title", "").strip().lower()
            if title and title not in seen_titles:
                seen_titles.add(title)
                new_items.append(p)

        if not new_items:
            logger.info("신규 논문 없음, 건너뜀")
            sleep(args.sleep)
            continue

        docs = _build_docs(new_items, q)
        store.add_documents(docs, batch_size=500)
        total_saved += len(docs)
        logger.info("저장 완료: %d건 (누적 %d)", len(docs), total_saved)
        sleep(args.sleep)

    logger.info("파이프라인 완료. 총 저장된 논문 수: %d", total_saved)


if __name__ == "__main__":
    main()
