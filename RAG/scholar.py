"""scholar.py

Semantic Scholar Graph API 래퍼.
환경 변수 `SEMANTIC_SCHOLAR_API_KEY` 가 필요합니다.
"""
from __future__ import annotations

import os
import logging
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


def bulk_search_scholar(query: str, limit: int = 100, *, min_citations: int | None = None) -> List[Dict[str, object]]:
    """Semantic Scholar에서 논문 메타데이터를 검색합니다.

    Args:
        query: 검색어(예: "atopic dermatitis")
        limit: 최대 검색 수(100 이하만 지원)
        min_citations: 필터링할 최소 인용 수(예: 300). None이면 필터 미적용
    Returns:
        `data` 필드에 담긴 논문 메타데이터 리스트
    """
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    # API 키가 없으면 비인증 요청 header 없이 진행합니다.
    if api_key:
        headers = {"x-api-key": api_key}
        logger.debug("API key provided, using authenticated request.")
    else:
        headers = {}
        logger.warning(
            "SEMANTIC_SCHOLAR_API_KEY 환경 변수가 설정되지 않았습니다. 비인증 요청을 시도합니다 (쿼터 제한 가능)."
        )

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": "title,openAccessPdf,year,citationCount",
    }
    if min_citations is not None and min_citations > 0:
        params["minCitationCount"] = min_citations
    logger.info("Semantic Scholar API 호출: %s (limit=%d)", query, params["limit"])
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    data.sort(key=lambda x: x.get("citationCount", 0), reverse=True)
    logger.info("검색 결과 %d건 수신", len(data))
    return data
