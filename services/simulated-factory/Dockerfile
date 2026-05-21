FROM alpine:3

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN ["apk", "add", "--no-cache", "uv"]

COPY pyproject.toml ./

RUN ["uv", "sync"]

COPY main.py ./
COPY presets.yml ./
COPY README.md ./
COPY api.md ./
COPY simulated_factory/ simulated_factory/
COPY web/ web/

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 CMD ["uv", "run", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8400/health', timeout=3)"]

ENTRYPOINT ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8400"]