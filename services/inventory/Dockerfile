FROM alpine:3

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN ["apk", "add", "--no-cache", "uv"]

COPY pyproject.toml ./
COPY uv.lock ./

RUN ["uv", "sync"]

COPY main.py ./

# Run the application in simulation mode
ENTRYPOINT ["uv", "run", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8103"]
