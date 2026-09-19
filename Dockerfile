FROM node:22-bookworm-slim AS codec
WORKDIR /codec
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts

FROM python:3.14-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates tini libstdc++6 && rm -r /var/lib/apt/lists/*
COPY --from=codec /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY requirements-context.txt ./
RUN pip install --no-cache-dir -r requirements-context.txt
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 TIKTOKEN_CACHE_DIR=/opt/tiktoken IC_DATA_DIR=/data PORT=10000
RUN python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"
COPY --from=codec /codec/node_modules ./node_modules
COPY *.py ./
COPY package.json package-lock.json ./
COPY web ./web
COPY converselab ./converselab
COPY context_optimization ./context_optimization
COPY deploy ./deploy
RUN groupadd --gid 10001 demo && useradd --uid 10001 --gid demo --no-create-home demo && mkdir -p /data && chown demo:demo /data
USER 10001:10001
EXPOSE 10000
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["python", "deploy/launch.py"]
