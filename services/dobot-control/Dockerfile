FROM alpine:3

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN ["apk", "add", "--no-cache", "uv"]

COPY pyproject.toml ./
COPY uv.lock ./

RUN ["uv", "sync"]

COPY config.yml ./
COPY src/ src/
COPY flows/ flows/

# Run the application in simulation mode
ENTRYPOINT ["uv", "run", "src/app.py", "-s"]
