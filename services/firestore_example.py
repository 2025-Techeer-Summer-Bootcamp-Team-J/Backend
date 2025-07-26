# 전체 예제 동작을 함수로 정의

from crud.firestore import (
    set_document, get_document, update_document,
    delete_document, query_documents
)

def firestore_demo():
    # 1. 문서 추가
    set_document('users', 'user_01', {
        'name': '홍길동',
        'age': 30,
        'email': 'hong@example.com'
    })

    # 2. 문서 조회
    user = get_document('users', 'user_01')
    if user:
        print('[문서 조회 결과]', user)
    else:
        print('[문서 조회] 문서를 찾을 수 없음')

    # 3. 문서 업데이트
    update_document('users', 'user_01', {'age': 31})
    print('[문서 업데이트] age = 31')

    # 4. 조건 검색
    users = query_documents('users', 'age', '>=', 25)
    print('[조건 검색 결과]')
    for u in users:
        print(u)

    # # 5. 문서 삭제
    # delete_document('users', 'user_01')
    # print('[문서 삭제 완료]')
