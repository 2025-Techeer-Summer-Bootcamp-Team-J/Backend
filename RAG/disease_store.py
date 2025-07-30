"""DiseaseStore

피부 질환 정보를 Firestore에 저장/조회하기 위한 래퍼.
컬렉션 구조는 다음과 같다.
    diseases/{doc_id} : {
        "disease_name": str,
        "detailed_description": str,
        "precautions": list[str],
        "management": dict,
        "source": {"기관명": str, "url": str}
    }

FirestoreVectorStore 와 동일하게 환경 변수를 사용하여 클라이언트를 초기화한다.
"""
from __future__ import annotations

import os
import uuid
import logging
from typing import Any, Dict, List

from google.cloud import firestore  # type: ignore
from crud.firestore import get_firestore_client

logger = logging.getLogger(__name__)


class DiseaseStore:
    """Firestore 래퍼 클래스"""

    def __init__(self, collection_name: str = "diseases") -> None:
        self.client = get_firestore_client()
        self.collection = self.client.collection(collection_name)
        # 사진 전용 컬렉션
        self.col_photos = self.client.collection("disease_photos")



    # ---------------------------- 저장 ---------------------------
    def add_documents(self, docs: List[Dict[str, Any]], batch_size: int = 1) -> List[str]:
        """여러 질병 문서를 배치로 저장합니다.

        Args:
            docs: 저장할 문서 리스트
            batch_size: 한 번에 커밋할 문서 수
        Returns:
            저장된 document ID 리스트
        """
        all_ids: List[str] = []
        for i in range(0, len(docs), batch_size):
            batch_docs = docs[i:i + batch_size]
            batch = self.client.batch()

            for doc in batch_docs:
                doc_id = uuid.uuid4().hex
                all_ids.append(doc_id)
                # photo_url 분리
                photo_url = doc.pop("photo_url", "")
                batch.set(self.collection.document(doc_id), doc)
                if photo_url:
                    batch.set(self.col_photos.document(doc_id), {"photo_url": photo_url})

            batch.commit()
            logger.info("DiseaseStore: 총 %d개 문서를 저장 완료했습니다", len(docs))
        return all_ids

    def add_document(self, doc: Dict[str, Any]) -> str:
        """단일 질병 문서를 저장합니다."""
        doc_id = uuid.uuid4().hex
        photo_url = doc.pop("photo_url", "")
        self.collection.document(doc_id).set(doc)
        if photo_url:
            self.col_photos.document(doc_id).set({"photo_url": photo_url})
        logger.info("DiseaseStore: 문서 %s 저장", doc_id)
        return doc_id


    # -------------------------- 조회 --------------------------
    def get_document(self, doc_id: str) -> Dict[str, Any] | None:
        snap = self.collection.document(doc_id).get()
        if snap.exists:
            return snap.to_dict()  # type: ignore[return-value]
        return None

    def query_by_disease(self, disease_name: str) -> List[Dict[str, Any]]:
        snaps = self.collection.where("disease_name", "==", disease_name).stream()
        return [s.to_dict() for s in snaps]
