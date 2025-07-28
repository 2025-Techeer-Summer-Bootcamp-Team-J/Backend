from google.cloud import firestore

# Firestore 클라이언트 초기화 (단일 인스턴스로 재사용)
def get_firestore_client():
    return firestore.Client()

# 문서 추가 또는 덮어쓰기
def set_document(collection_name: str, document_id: str, data: dict):
    db = get_firestore_client()
    doc_ref = db.collection(collection_name).document(document_id)
    doc_ref.set(data)

# 문서 읽기
def get_document(collection_name: str, document_id: str) -> dict | None:
    db = get_firestore_client()
    doc_ref = db.collection(collection_name).document(document_id)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None

# 문서 업데이트 (특정 필드만)
def update_document(collection_name: str, document_id: str, updates: dict):
    db = get_firestore_client()
    doc_ref = db.collection(collection_name).document(document_id)
    doc_ref.update(updates)

# 문서 삭제
def delete_document(collection_name: str, document_id: str):
    db = get_firestore_client()
    doc_ref = db.collection(collection_name).document(document_id)
    doc_ref.delete()

# 조건 검색 (쿼리)
def query_documents(collection_name: str, field: str, operator: str, value, limit: int = 10):
    db = get_firestore_client()
    collection_ref = db.collection(collection_name)
    query = collection_ref.where(field, operator, value).limit(limit)
    return [doc.to_dict() for doc in query.stream()]

