# Stage 1: build frontend
FROM node:20-alpine AS frontend-builder

ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app

COPY frontend/ ./

RUN npm install -g pnpm && export CI='true' && pnpm install --frozen-lockfile
RUN pnpm build

# Stage 2: runtime
FROM nikolaik/python-nodejs:python3.12-nodejs22-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends aria2 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-builder /app/dist ./frontend/dist/

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1

CMD ["python", "-m", "backend.server"]
