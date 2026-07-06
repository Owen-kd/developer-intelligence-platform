# DIP 앱 컨테이너 — API / 스케줄러 / CLI 공용 이미지
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 소스 복사 (프롬프트/마이그레이션은 런타임에 파일로 참조되므로 함께 둔다)
COPY pyproject.toml README.md ./
COPY apps ./apps
COPY modules ./modules
COPY dip_platform ./dip_platform
COPY infrastructure ./infrastructure
COPY shared ./shared
COPY database ./database
COPY prompts ./prompts

# editable 설치 → /app 이 sys.path 에 올라가 prompts/ · database/ 를 상대경로로 찾는다
RUN pip install -e .

# 비루트 사용자로 실행
RUN useradd --create-home --uid 10001 dip && chown -R dip:dip /app
USER dip

EXPOSE 8000

# 기본은 API. 스케줄러/CLI 는 `docker compose run app python -m apps.cli.<x>` 로 실행.
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
