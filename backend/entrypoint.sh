#!/bin/bash

set -e

# uvicorn 명령으로 시작할 때만 마이그레이션 수행
if [[ "$1" == "uvicorn"* ]]; then
    echo "Waiting for database..."
    # 필요시 여기에 db 대기 로직 추가 가능
    
    echo "Running migrations..."
    python manage.py migrate --noinput
fi

echo "Starting command: $@"
exec "$@"