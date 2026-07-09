# DIP 앱 이미지 — api/worker/scheduler 공용. 역할은 compose 의 command 로 선택.
# 소스에서 실행(editable 설치)한다: prompts/config/knowledge 를 파일 경로로 읽으므로
# site-packages 가 아니라 /app 에서 __file__ 이 해석되어야 한다.
FROM python:3.11-slim

WORKDIR /app

# 의존성 캐시 최적화: 메타데이터 먼저 복사
COPY pyproject.toml README.md ./

# 소스 + 자산(프롬프트/설정/지식/마이그레이션)
COPY apps ./apps
COPY modules ./modules
COPY dip_platform ./dip_platform
COPY infrastructure ./infrastructure
COPY shared ./shared
COPY prompts ./prompts
COPY config ./config
COPY knowledge ./knowledge
COPY database ./database

# editable 설치 → 런타임 의존성 + /app 경로 보존(자산 파일 접근)
RUN pip install --no-cache-dir -e .

# fastembed(로컬 임베딩) — xet 캐시 권한 이슈 회피. 모델은 최초 사용 시 캐시 볼륨에 받는다.
ENV HF_HUB_DISABLE_XET=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# 기본은 API. worker/scheduler 는 compose command 로 override.
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
