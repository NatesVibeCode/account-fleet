FROM node:22-bookworm-slim

RUN npm install -g opencode-ai@1.18.28 && \
    apt-get update && \
    apt-get install -y --no-install-recommends python3 ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 worker
USER worker
WORKDIR /task

ENV XDG_CONFIG_HOME=/tmp/config \
    XDG_DATA_HOME=/tmp/data \
    XDG_STATE_HOME=/tmp/state \
    XDG_CACHE_HOME=/tmp/cache

ENTRYPOINT ["opencode"]
