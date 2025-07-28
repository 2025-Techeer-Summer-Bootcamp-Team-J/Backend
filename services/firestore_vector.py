"""FirestoreVectorStore

LangChain VectorStore 래퍼가 아직 공식 지원되지 않으므로,
간단한 brute-force 코사인 유사도 검색으로 Firestore 컬렉션을 사용한다.
임베딩 모델은 LangChain Embeddings 인터페이스를 구현하는 객체(OpenAIEmbeddings 등)를 주입받는다.
"""

from __future__ import annotations

import logging
import time
from typing import Any, List, Optional, Tuple

import numpy as np
from google.cloud import firestore  # type: ignore
from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class FirestoreVectorStore(VectorStore):
    """Google Firestore 기반 간단 VectorStore.

    Firestore 컬렉션 설계:
        documents/{doc_id}: {"text": str, "metadata": dict}
        vectors/{doc_id}:   {"embedding": List[float]}

    Args:
        project_id: GCP 프로젝트 ID (None 시 ADC 설정 값 사용)
        collection_docs: 문서 저장 컬렉션 이름
        collection_vectors: 벡터 저장 컬렉션 이름
        embedding: LangChain Embeddings 객체
    """

    def __init__(
        self,
        embedding: Embeddings,
        project_id: Optional[str] = None,
        collection_docs: str = "documents",
        collection_vectors: str = "vectors",
    ) -> None:
        self.embedding = embedding
        self.client = firestore.Client(project=project_id)
        self.col_docs = self.client.collection(collection_docs)
        self.col_vectors = self.client.collection(collection_vectors)

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> "FirestoreVectorStore":
        """텍스트 목록에서 FirestoreVectorStore를 생성하고 문서를 추가합니다."""
        # FirestoreVectorStore 인스턴스 생성
        store = cls(embedding=embedding, **kwargs)
        # 생성된 인스턴스에 텍스트 추가
        store.add_texts(texts=texts, metadatas=metadatas)
        return store

    # ------------------------ 저장 ------------------------
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[str]:
        metadatas = metadatas or [{} for _ in texts]
        ids = ids or [self._gen_id() for _ in texts]
        if not (len(texts) == len(metadatas) == len(ids)):
            raise ValueError("texts, metadatas, ids 길이가 동일해야 합니다.")

        embeddings: List[List[float]] = self.embedding.embed_documents(texts)
        batch = self.client.batch()
        for text, metadata, eid, emb in zip(texts, metadatas, ids, embeddings):
            batch.set(self.col_docs.document(eid), {"text": text, "metadata": metadata})
            batch.set(self.col_vectors.document(eid), {"embedding": emb})
        batch.commit()
        logger.info("FirestoreVectorStore: %d개 문서를 저장했습니다", len(texts))
        return ids

    # ------------------------ 검색 ------------------------
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> List[Document]:
        logger.info("FirestoreVectorStore: 유사도 검색을 시작합니다 (배치 처리 방식).")

        # 1. 쿼리 임베딩 (재시도 로직 추가)
        max_retries = 3
        query_emb = None
        for attempt in range(max_retries):
            try:
                logger.info(f"  - 1단계: 쿼리 임베딩 시도 ({attempt + 1}/{max_retries})...")
                query_emb = np.array(self.embedding.embed_query(query))
                logger.info("  - 1단계: 쿼리 임베딩 성공!")
                break
            except Exception as e:
                logger.warning(f"  - 1단계: 쿼리 임베딩 실패. 오류: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    logger.error("  - 1단계: 쿼리 임베딩 최종 실패.")
                    raise

        # 2. 모든 벡터를 배치로 나누어 로드하고 유사도 계산
        logger.info("  - 2단계: Firestore 벡터를 배치로 나누어 유사도를 계산합니다...")
        sims: List[Tuple[str, float]] = []
        batch_size = 100
        cursor = None
        total_vectors = 0

        while True:
            if cursor:
                query_ref = self.col_vectors.order_by("__name__").start_after(cursor).limit(batch_size)
            else:
                query_ref = self.col_vectors.order_by("__name__").limit(batch_size)
            
            vectors_batch = list(query_ref.stream())
            if not vectors_batch:
                break

            for v in vectors_batch:
                total_vectors += 1
                eid = v.id
                emb = np.asarray(v.get("embedding"), dtype=np.float32)
                if emb.size == 0:
                    continue
                score = float(np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb) + 1e-10))
                sims.append((eid, score))
            
            logger.info(f"    - {total_vectors}개 벡터 처리 완료...")
            cursor = vectors_batch[-1]

        logger.info(f"  - 2단계: 총 {total_vectors}개 벡터에 대한 유사도 계산 완료.")

        # 3. 상위 K개 결과 정렬 및 선택
        sims.sort(key=lambda x: x[1], reverse=True)
        top_ids = [eid for eid, _ in sims[:k]]
        logger.info(f"  - 3단계: 가장 유사한 문서 ID {len(top_ids)}개를 찾았습니다.")

        # 4. 원본 문서 조회
        logger.info(f"  - 4단계: 원본 문서 {len(top_ids)}개를 조회합니다...")
        docs: List[Document] = []
        for eid in top_ids:
            doc_ref = self.col_docs.document(eid).get()
            if not doc_ref.exists:
                continue
            data = doc_ref.to_dict()
            docs.append(Document(page_content=data["text"], metadata=data.get("metadata", {})))
        
        logger.info("FirestoreVectorStore: 유사도 검색을 완료했습니다.")
        return docs

    # ------------------------ Helpers ------------------------
    @staticmethod
    def _gen_id() -> str:
        import uuid

        return uuid.uuid4().hex
