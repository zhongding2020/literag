 # LiteRAG 本地构建（通过 pip 安装，无需克隆源码）

 FROM python:3.12-slim-bookworm AS builder

 WORKDIR /app

 # 安装系统依赖
 RUN apt-get update && apt-get install -y --no-install-recommends \
     git curl build-essential pkg-config \
     && rm -rf /var/lib/apt/lists/*

 # 安装 LightRAG（API 版本，包含 WebUI）
 RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
     "lightrag-hku[api]" \
     && python -c "import lightrag; print('LightRAG', lightrag.__version__)"

 # 下载 tiktoken 缓存（可选，离线加速）
 RUN python -m lightrag.tools.download_cache --cache-dir /app/data/tiktoken || true

 FROM python:3.12-slim-bookworm

 WORKDIR /app

 # 复制 Python 包和依赖
 COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
 COPY --from=builder /usr/local/bin /usr/local/bin
 COPY --from=builder /app/data/tiktoken /app/data/tiktoken

 # 数据目录
 RUN mkdir -p /app/data/rag_storage /app/data/inputs /app/data/prompts /app/data/tiktoken

 ENV WORKING_DIR=/app/data/rag_storage \
     INPUT_DIR=/app/data/inputs \
     PROMPT_DIR=/app/data/prompts \
     TIKTOKEN_CACHE_DIR=/app/data/tiktoken

 EXPOSE 9621
 CMD ["python", "-m", "lightrag.api.lightrag_server"]
 # LiteRAG 本地构建
 FROM python:3.12-slim
 
 WORKDIR /app
 
 # 安装 LightRAG（API 版本，含 REST API + WebUI）
 RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
     "lightrag-hku[api]"
 
 RUN mkdir -p /app/data/rag_storage /app/data/inputs /app/data/prompts /app/data/tiktoken
 
 ENV WORKING_DIR=/app/data/rag_storage \
     INPUT_DIR=/app/data/inputs \
     PROMPT_DIR=/app/data/prompts \
     TIKTOKEN_CACHE_DIR=/app/data/tiktoken
 
 EXPOSE 9621
 CMD ["python", "-m", "lightrag.api.lightrag_server"]
