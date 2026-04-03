FROM alpine:3

WORKDIR /app

RUN ["apk", "add", "--no-cache", "cargo"]

COPY Cargo.toml ./
COPY Cargo.lock ./
COPY src/ src/

ENTRYPOINT ["cargo", "run"]