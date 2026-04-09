# Stage 1: build frontend
ARG FRONTEND_BUILD_IMAGE=node:20-bookworm-slim
ARG PYTHON_RUNTIME_IMAGE=python:3.12-slim-bookworm
FROM ${FRONTEND_BUILD_IMAGE} AS frontend-builder

ARG VITE_API_BASE_URL=
ARG VITE_API_AUTH_TOKEN=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_API_AUTH_TOKEN=${VITE_API_AUTH_TOKEN}

WORKDIR /app

COPY frontend/ ./

RUN if ! command -v node >/dev/null 2>&1; then \
      apt-get update && \
      apt-get install -y --no-install-recommends nodejs npm && \
      rm -rf /var/lib/apt/lists/*; \
    fi
RUN npm install -g pnpm && export CI='true' && pnpm install --frozen-lockfile
RUN pnpm build

# Stage 2: runtime
FROM ${PYTHON_RUNTIME_IMAGE}

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_INDEX_URL=
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL}

RUN apt-get update && \
    apt-get install -y --no-install-recommends -o Acquire::Retries=5 aria2 nodejs npm && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN grep -v '^pywebview' requirements.txt > requirements.docker.txt && \
    pip install --no-cache-dir --retries 5 -r requirements.docker.txt

COPY . .
COPY --from=frontend-builder /app/dist ./frontend/dist/

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; token = os.getenv('DOUYIN_API_AUTH_TOKEN', '').strip(); headers = {'Authorization': f'Bearer {token}'} if token else {}; req = urllib.request.Request('http://127.0.0.1:8000/api/health', headers=headers); urllib.request.urlopen(req, timeout=3)" || exit 1

CMD ["python", "-m", "backend.server"]
