# backend

# 프로젝트명

## 요구사항
- Docker desktop
- Git
- .env 루트 디렉토리에 생성 및 노션 참고 복붙
   -  ( secretkey의 경우 settings.py 본인 키값 사용 )

## 설치 및 실행

1. 깃헙 저장소에서 프로젝트 클론:
   ```bash
   git clone https://github.com/yourusername/your-repository.git
   cd your-repository
   ```

2. `.env` 파일 복사 붙여넣기:
    팀 노션의 secret file/backend 페이지 참고
       .env 루트 디렉토리에 생성 및 노션 참고 복붙

3. Docker Compose 실행:
   ```bash
   docker-compose up -d
   ```

4. Docker Container 접속:
   docker ps로 containerID 확인
   docker exec -it containerID bash
   
   docker-compose ps 로 서비스명 확인
   docker-compose exec -it 서비스명 bash

5. 애플리케이션에 접속:
   브라우저에서 [http://localhost:8000]를 열어 프로젝트를 확인
    - http://localhost:8000/docs#/default 로 접속하면 반응형 페이지로 접속




