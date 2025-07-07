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
   - docker ps로 containerID 확인
     docker exec -it containerID bash
   
   - docker-compose ps 로 서비스명 확인
     docker-compose exec -it 서비스명 bash
   
   - 패키지를 설치하려면
     ```bash
     docker-compose exec -it backend
     pip install requests
     ```
     와 같이 설치하고
     ```bash
     pip freeze > requirements.txt
     ```
     도 해주자

6. 애플리케이션에 접속:
   브라우저에서 [http://localhost:8000]를 열어 프로젝트를 확인
    - http://localhost:8000/docs#/default 로 접속하면 반응형 페이지로 접속

## 로컬환경에서 fastAPI 서버를 실행하려면
https://humble-orca-498.notion.site/uv-pip-228a2f53cce8801a94f4e90a79e37cb6?source=copy_link
참고해서 uv 가상환경 설치 후 진행

## fastAPI 기초적인 부분
https://humble-orca-498.notion.site/fastAPI-229a2f53cce8808aa4a1f73c1607b969?source=copy_link
