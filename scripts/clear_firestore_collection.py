"""Firestore 컬렉션의 모든 문서를 삭제하는 스크립트

- 컬렉션 내 모든 문서를 배치로 삭제하여 초기화합니다.
- `vector_store`와 `documents` 두 컬렉션을 모두 삭제합니다.

실행 방법
----------
```bash
docker compose exec backend python -m scripts.clear_firestore_collection
```
"""

import logging

from google.cloud import firestore
from crud.firestore import get_firestore_client

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def delete_collection(db: firestore.Client, collection_name: str, batch_size: int = 50) -> None:
    """지정된 컬렉션의 모든 문서를 배치 삭제합니다."""
    coll_ref = db.collection(collection_name)
    deleted_count = 0

    while True:
        # 삭제할 문서들을 배치 크기만큼 가져옵니다.
        docs = coll_ref.limit(batch_size).stream()
        docs_list = list(docs)

        if not docs_list:
            break  # 더 이상 삭제할 문서가 없으면 종료

        batch = db.batch()
        for doc in docs_list:
            logger.info(f"{collection_name} 컬렉션에서 문서 삭제 중: {doc.id}")
            batch.delete(doc.reference)
        
        batch.commit()
        deleted_count += len(docs_list)

    if deleted_count > 0:
        logger.info(f"총 {deleted_count}개의 문서가 '{collection_name}' 컬렉션에서 삭제되었습니다.")
    else:
        logger.info(f"'{collection_name}' 컬렉션에 삭제할 문서가 없습니다.")


def main():
    """메인 실행 함수"""
    db = get_firestore_client()
    
    # 크롤링된 원본 문서가 저장되는 컬렉션
    DOCUMENTS_COLLECTION = "documents"
    # 벡터 데이터가 저장되는 컬렉션
    VECTORS_COLLECTION = "vectors"

    logger.info(f"'{DOCUMENTS_COLLECTION}' 컬렉션 초기화를 시작합니다.")
    delete_collection(db, DOCUMENTS_COLLECTION)

    logger.info(f"'{VECTORS_COLLECTION}' 컬렉션 초기화를 시작합니다.")
    delete_collection(db, VECTORS_COLLECTION)

    logger.info("모든 지정된 컬렉션의 초기화가 완료되었습니다.")


if __name__ == "__main__":
    main()
