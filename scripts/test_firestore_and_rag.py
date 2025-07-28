"""Firestore 및 RAG 동작을 빠르게 검증하기 위한 데모 스크립트.

실행 방법
---------
터미널에서 프로젝트 루트(Backend) 디렉터리에서 다음 명령을 실행하세요.

    python -m scripts.test_firestore_and_rag

필요 환경 변수
---------------
- GOOGLE_APPLICATION_CREDENTIALS: Firestore 서비스 계정 JSON 경로
- GEMINI_API_KEY: Gemini API Key (RAG용)

스크립트 동작
-------------
1. Firestore 데모
   - `users/user_demo` 문서를 생성(set) 후 읽기(get) → 출력
   - 나이(age)를 1 증가(update) 후 다시 읽기 → 출력
   - 나이(age) >= 20 조건으로 쿼리 → 출력

2. RAG 데모
   - `generate_disease_info()` 함수에 테스트 질문을 넣어 실행
   - 반환된 JSON을 pretty print
"""

from __future__ import annotations

import json
import logging
from pprint import pprint

# 로깅 기본 설정 추가
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from crud.firestore import (
    get_document,
    query_documents,
    set_document,
    update_document,
)
from RAG.generator_service import generate_disease_info


# ---------------- Firestore 데모 ----------------

def firestore_demo() -> None:
    """Firestore CRUD 기본 동작 확인"""
    print("\n===== Firestore Demo =====")

    collection = "users"
    doc_id = "user_demo"

    # 1) 문서 생성/덮어쓰기
    print("[1] 문서 생성/덮어쓰기 …")
    set_document(collection, doc_id, {"name": "홍길동", "age": 20, "email": "hong@example.com"})

    # 2) 문서 조회
    print("[2] 문서 조회 …")
    user = get_document(collection, doc_id)
    pprint(user)

    # 3) 문서 업데이트 (나이 +1)
    print("[3] 문서 업데이트 (age += 1) …")
    update_document(collection, doc_id, {"age": user.get("age", 0) + 1})
    user = get_document(collection, doc_id)
    pprint(user)

    # 4) 조건 검색 (age >= 20)
    print("[4] 조건 검색 (age >= 20) …")
    users = query_documents(collection, "age", ">=", 20)
    pprint(users)


# ---------------- RAG 데모 ----------------

def rag_demo() -> None:
    """RAG 체인 동작 확인"""
    print("\n===== RAG Demo =====")

    test_question = "아토피 피부염 관리 방법은 무엇인가요?"
    print(f"[질문] {test_question}")
    try:
        answer = generate_disease_info(test_question)
        print("[RAG 응답]")
        print(json.dumps(answer, ensure_ascii=False, indent=2))
    except Exception as e:
        print("⚠️  RAG 실행 중 오류 발생:", e)


if __name__ == "__main__":
    # firestore_demo() # Firestore 기본 동작 테스트는 건너뜁니다.
    rag_demo()
