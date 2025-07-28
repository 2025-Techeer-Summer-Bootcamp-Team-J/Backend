"""PaperStore

Semantic Scholar API에서 수집한 논문 메타데이터를 Firestore에 저장/조회하기 위한 래퍼.
컬렉션 구조는 다음과 같다.
    papers/{doc_id} : {
        "title": str,
        "year": int | None,
        "citationCount": int,
        "openAccessPdf": {"url": str} | None,
        "query": str,              # 검색 질의어
        "createdAt": firestore.SERVER_TIMESTAMP,
    }

`DiseaseStore` 와 마찬가지로 Firestore Vector Store와 동일한 환경 변수를 사용해
클라이언트를 초기화한다.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from google.cloud import firestore  # type: ignore
from crud.firestore import get_firestore_client

logger = logging.getLogger(__name__)


class PaperStore:
    """Firestore 논문 정보 래퍼 클래스"""

    def __init__(self, collection_name: str = "papers") -> None:
        self.client = get_firestore_client()
        self.collection = self.client.collection(collection_name)

    # ---------------------------- 저장 ---------------------------
    def add_documents(
        self,
        docs: List[Dict[str, Any]],
        batch_size: int = 500,
    ) -> List[str]:
        """여러 논문 문서를 배치로 저장합니다.

        Args:
            docs: 저장할 문서 리스트
            batch_size: Firestore batch 커밋 단위 (최대 500)
        Returns:
            저장된 document ID 리스트
        """
        all_ids: List[str] = []
        for i in range(0, len(docs), batch_size):
            batch_docs = docs[i : i + batch_size]
            batch = self.client.batch()
            for doc in batch_docs:
                doc_id = uuid.uuid4().hex
                all_ids.append(doc_id)
                # 서버 타임스탬프
                if "createdAt" not in doc:
                    doc["createdAt"] = firestore.SERVER_TIMESTAMP
                batch.set(self.collection.document(doc_id), doc)
            batch.commit()
            logger.info("PaperStore: %d개 문서를 저장했습니다", len(batch_docs))
        return all_ids

    # -------------------------- 조회 --------------------------
    def get_document(self, doc_id: str) -> Dict[str, Any] | None:
        snap = self.collection.document(doc_id).get()
        return snap.to_dict() if snap.exists else None

    def query_by_title(self, title: str, limit: int = 5) -> List[Dict[str, Any]]:
        snaps = (
            self.collection.where("title", "==", title).limit(limit).stream()
        )
        return [s.to_dict() for s in snaps]
