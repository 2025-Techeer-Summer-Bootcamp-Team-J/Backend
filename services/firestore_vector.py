"""FirestoreVectorStore

LangChain VectorStore 래퍼가 아직 공식 지원되지 않으므로,
간단한 brute-force 코사인 유사도 검색으로 Firestore 컬렉션을 사용한다.
임베딩 모델은 LangChain Embeddings 인터페이스를 구현하는 객체(OpenAIEmbeddings 등)를 주입받는다.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

import numpy as np
from google.cloud import firestore  # type: ignore
from langchain_community.vectorstores.base import VectorStore
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
        query_emb = np.array(self.embedding.embed_query(query))

        # 모든 벡터 로드 (소규모 데이터셋 가정) → 대규모면 Vertex AI Matching Engine 추천
        vectors = list(self.col_vectors.stream())
        sims: List[Tuple[str, float]] = []
        for v in vectors:
            eid = v.id
            emb = np.asarray(v.get("embedding"), dtype=np.float32)
            if emb.size == 0:
                continue
            # 코사인 유사도
            score = float(np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb) + 1e-10))
            sims.append((eid, score))
        sims.sort(key=lambda x: x[1], reverse=True)
        top_ids = [eid for eid, _ in sims[:k]]

        docs: List[Document] = []
        for eid in top_ids:
            doc_ref = self.col_docs.document(eid).get()
            if not doc_ref.exists:
                continue
            data = doc_ref.to_dict()
            docs.append(Document(page_content=data["text"], metadata=data.get("metadata", {})))
        return docs

    # ------------------------ Helpers ------------------------
    @staticmethod
    def _gen_id() -> str:
        import uuid

        return uuid.uuid4().hex
