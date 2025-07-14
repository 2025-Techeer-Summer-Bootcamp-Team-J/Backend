#!/bin/bash

# SSL 디렉토리 생성
mkdir -p ssl
mkdir -p certbot/conf
mkdir -p certbot/www

# 자체 서명 인증서 생성 (개발용)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=KR/ST=Seoul/L=Seoul/O=Development/CN=localhost"

echo "SSL 인증서가 생성되었습니다."
echo "개발 환경에서 https://localhost 로 접속할 수 있습니다."
echo "브라우저에서 보안 경고가 나타날 수 있습니다. (개발용 인증서이므로 정상입니다)" 