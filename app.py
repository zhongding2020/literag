#!/usr/bin/env python3
"""
LightRAG 简易启动器
用法：
  1. pip install "lightrag-hku[api]"
  2. python app.py
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()

# ── 配置 ────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "9621"))
WORKING_DIR = os.getenv("WORKING_DIR", "./rag_storage")
INPUT_DIR = os.getenv("INPUT_DIR", "./inputs")
LLM_BINDING = os.getenv("LLM_BINDING", "openai")
LLM_HOST = os.getenv("LLM_BINDING_HOST", "https://api.deepseek.com/v1")
LLM_KEY = os.getenv("LLM_BINDING_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
EMBED_BINDING = os.getenv("EMBEDDING_BINDING", "ollama")
EMBED_HOST = os.getenv("EMBEDDING_BINDING_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")
EMBED_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
API_KEY = os.getenv("LIGHTRAG_API_KEY", "")

# ── 显示配置 ────────────────────────────────────────
print("=" * 50)
print("LightRAG 启动配置")
print("=" * 50)
print(f"  LLM:           {LLM_BINDING}/{LLM_MODEL}")
print(f"  LLM Host:      {LLM_HOST}")
print(f"  LLM API Key:   {'***' + LLM_KEY[-4:] if LLM_KEY else '(未设置)'}")
print(f"  Embedding:     {EMBED_BINDING}/{EMBED_MODEL} (dim={EMBED_DIM})")
print(f"  Embed Host:    {EMBED_HOST}")
print(f"  OLLAMA_HOST:   {OLLAMA_HOST}")
print(f"  Server:        {HOST}:{PORT}")
print(f"  Working Dir:   {WORKING_DIR}")
print(f"  Input Dir:     {INPUT_DIR}")
print(f"  API Key:       {'已设置' if API_KEY else '未设置（开放访问）'}")
print("=" * 50)
print()

# ── 创建数据目录 ────────────────────────────────────
Path(WORKING_DIR).mkdir(parents=True, exist_ok=True)
Path(INPUT_DIR).mkdir(parents=True, exist_ok=True)

# ── 设置环境变量（LightRAG 会读取这些）───────────────
os.environ.setdefault("HOST", HOST)
os.environ.setdefault("PORT", str(PORT))
os.environ.setdefault("WORKING_DIR", WORKING_DIR)
os.environ.setdefault("INPUT_DIR", INPUT_DIR)
os.environ.setdefault("LLM_BINDING", LLM_BINDING)
os.environ.setdefault("LLM_BINDING_HOST", LLM_HOST)
os.environ.setdefault("LLM_BINDING_API_KEY", LLM_KEY)
os.environ.setdefault("LLM_MODEL", LLM_MODEL)
os.environ.setdefault("EMBEDDING_BINDING", EMBED_BINDING)
os.environ.setdefault("EMBEDDING_BINDING_HOST", EMBED_HOST)
os.environ.setdefault("EMBEDDING_MODEL", EMBED_MODEL)
os.environ.setdefault("EMBEDDING_DIM", str(EMBED_DIM))
os.environ.setdefault("OLLAMA_HOST", OLLAMA_HOST)
os.environ.setdefault("TIKTOKEN_CACHE_DIR", os.path.join(WORKING_DIR, "tiktoken"))
if API_KEY:
    os.environ.setdefault("LIGHTRAG_API_KEY", API_KEY)

# ── tiktoken 缓存配置（支持 0.13.0+）─────────────────
TIKTOKEN_CACHE = os.path.join(WORKING_DIR, "tiktoken")
os.environ["TIKTOKEN_CACHE_DIR"] = TIKTOKEN_CACHE  # 旧版本兼容
os.environ["TIKTOKEN_CACHE"] = TIKTOKEN_CACHE      # 部分新版本
Path(TIKTOKEN_CACHE).mkdir(parents=True, exist_ok=True)

try:
    import tiktoken
    # 强制缓存目录（tiktoken 0.13.0+ 不再读环境变量）
    try:
        from pathlib import Path as _Path
        _cache = _Path(TIKTOKEN_CACHE)
        # 在可能的位置 patchtiktoken.core.cache_dir
        for _mod_name in ['tiktoken._cache', 'tiktoken.core']:
            try:
                _mod = __import__(_mod_name, fromlist=[''])
                if hasattr(_mod, 'cache_dir'):
                    _mod.cache_dir = lambda p=_cache: p
            except ImportError:
                pass
    except Exception:
        pass
    
    # 尝试预下载编码文件（有代理的情况下）
    for enc_name in ["cl100k_base", "o200k_base"]:
        try:
            tiktoken.get_encoding(enc_name)
            print(f"  ✅ {enc_name}")
        except Exception as e:
            print(f"  ⚠️  {enc_name} 下载失败（运行时会重试）: {e}")
    print(f"✅ tiktoken cache: {TIKTOKEN_CACHE}")
except ImportError:
    print("⚠️  tiktoken not installed")

# ── 启动 LightRAG API Server ────────────────────────
print("\n🚀 启动 LightRAG Server...\n")

# 用命令行参数方式启动（与 python -m lightrag.api.lightrag_server 等价）
sys.argv = [
    "lightrag_server",
    "--host", HOST,
    "--port", str(PORT),
    "--working-dir", WORKING_DIR,
    "--input-dir", INPUT_DIR,
]

from lightrag.api.lightrag_server import main
main()
