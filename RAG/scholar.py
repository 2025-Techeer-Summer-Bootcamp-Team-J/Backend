"""scholar.py

Semantic Scholar Graph API 래퍼.
환경 변수 `SEMANTIC_SCHOLAR_API_KEY` 가 필요합니다.
"""
from __future__ import annotations

import os
import logging

import time

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

        "fields": "title,year",
    }
    if min_citations is not None and min_citations > 0:
        params["minCitationCount"] = min_citations
    # --- 간단한 Rate Limit: 초당 1회 ---
    last_called_at: float = getattr(bulk_search_scholar, "_last_called_at", 0.0)
    elapsed = time.time() - last_called_at
    if elapsed < 1.0:
        sleep_sec = 1.0 - elapsed
        logger.debug("Rate limiting: %.2f초 대기", sleep_sec)
        time.sleep(sleep_sec)

    logger.info("Semantic Scholar API 호출: %s (limit=%d)", query, params["limit"])
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    # 호출 후 타임스탬프 저장
    bulk_search_scholar._last_called_at = time.time()

    resp.raise_for_status()
    data = resp.json().get("data", [])
    data.sort(key=lambda x: x.get("citationCount", 0), reverse=True)
    logger.info("검색 결과 %d건 수신", len(data))
    return data