"""save_papers_to_firestore.py

Semantic Scholar API를 사용해 논문 메타데이터를 검색하고 Firestore `papers` 컬렉션에 저장합니다.

사용 예시:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    export SEMANTIC_SCHOLAR_API_KEY=your_key

    python scripts/save_papers_to_firestore.py --query "atopic dermatitis" --limit 300
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

from dotenv import load_dotenv  # type: ignore

# 내부 패키지 import를 위한 path 조정 (프로젝트 루트 추가)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from RAG.scholar import bulk_search_scholar  # noqa: E402
from RAG.paper_store import PaperStore  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_docs(data: List[Dict[str, object]], query: str) -> List[Dict[str, object]]:
    """Semantic Scholar 응답 데이터를 Firestore 스키마로 변환합니다."""
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic Scholar 논문을 Firestore에 저장")
    parser.add_argument("--query", required=True, help="검색어 (예: 'atopic dermatitis')")
    parser.add_argument("--limit", type=int, default=100, help="검색 결과 수(최대 100)")
    args = parser.parse_args()

    load_dotenv()

    # 1. Semantic Scholar 검색
    papers = bulk_search_scholar(args.query, args.limit)
    if not papers:
        logger.warning("검색 결과가 없습니다: %s", args.query)
        return

    # 2. Firestore 저장
    store = PaperStore()
    docs = _build_docs(papers, args.query)
    store.add_documents(docs, batch_size=500)
    logger.info("Firestore 저장 완료: %d건", len(docs))


if __name__ == "__main__":
    main()
