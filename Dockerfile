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
ENV PATH="/root/.local/bin:$PATH"

# 작업 디렉토리 설정
WORKDIR /app

# 2. 시스템 패키지 관리자 업데이트 및 OpenCV 실행에 필요한 모든 시스템 라이브러리 설치
# 이 부분이 libGL.so.1 오류를 포함한 대부분의 의존성 문제를 해결합니다.
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    
# Python 의존성 파일 복사
COPY requirements.txt .

# Python 패키지 설치
RUN uv pip install --system -r requirements.txt
RUN uv pip install --system gunicorn

# 애플리케이션 코드 복사
COPY . .
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
