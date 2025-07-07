# Python 3.13.1 slim 이미지 사용
FROM python:3.13.1-slim

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# 최신 uv 설치 프로그램 다운로드
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# uv 설치 프로그램을 실행한 다음 제거합니다.
RUN sh /uv-installer.sh && rm /uv-installer.sh

# 설치된 바이너리가 `PATH`에 있는지 확인합니다.
ENV PATH="/root/.local/bin/:$PATH"

    
# Python 의존성 파일 복사
COPY requirements.txt .
# 작업 디렉토리 설정
WORKDIR /app

# Python 패키지 설치
RUN uv pip install --system -r requirements.txt
RUN uv pip install --system gunicorn

# 애플리케이션 코드 복사
COPY . .
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
