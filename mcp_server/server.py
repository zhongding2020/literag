"""
LiteRAG MCP Server - wraps LightRAG REST API as MCP tools for AI agents.
"""

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Literal, Optional

import httpx
import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv("/app/.env")

logger = logging.getLogger("literag-mcp")
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger.info("Log level: %s", _log_level)

LIGHTRAG_HOST = os.getenv("LIGHTRAG_HOST", "host.docker.internal")
LIGHTRAG_PORT = os.getenv("LIGHTRAG_PORT", "9621")
LIGHTRAG_BASE = f"http://{LIGHTRAG_HOST}:{LIGHTRAG_PORT}"
LIGHTRAG_API_KEY = os.getenv("LIGHTRAG_API_KEY", "")

mcp = FastMCP("literag-knowledge-base", host="0.0.0.0")


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if LIGHTRAG_API_KEY:
        h["X-API-Key"] = LIGHTRAG_API_KEY
    return h


async def _api_post(path: str, body: dict) -> dict:
    url = f"{LIGHTRAG_BASE}{path}"
    logger.info("[REQ] POST %s | body_tail=%s", url, str(body)[:500])
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, headers=_headers(), json=body)
            logger.info("[RES] POST %s \u2192 %s | len=%s", url, resp.status_code, len(resp.text))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError:
            logger.error("[ERR] POST %s \u2192 %s: %s", url, resp.status_code, resp.text[:500])
            raise
        except httpx.RequestError as e:
            logger.error("[ERR] POST %s \u2192 Connection FAILED: %s", url, e)
            raise


async def _api_get(path: str) -> dict:
    url = f"{LIGHTRAG_BASE}{path}"
    logger.info("[REQ] GET %s", url)
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=_headers())
            logger.info("[RES] GET %s \u2192 %s | len=%s", url, resp.status_code, len(resp.text))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError:
            logger.error("[ERR] GET %s \u2192 %s: %s", url, resp.status_code, resp.text[:500])
            raise
        except httpx.RequestError as e:
            logger.error("[ERR] GET %s \u2192 Connection FAILED: %s", url, e)
            raise


async def _api_delete(path: str) -> dict:
    url = f"{LIGHTRAG_BASE}{path}"
    logger.info("[REQ] DELETE %s", url)
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.delete(url, headers=_headers())
            logger.info("[RES] DELETE %s \u2192 %s | len=%s", url, resp.status_code, len(resp.text))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError:
            logger.error("[ERR] DELETE %s \u2192 %s: %s", url, resp.status_code, resp.text[:500])
            raise
        except httpx.RequestError as e:
            logger.error("[ERR] DELETE %s \u2192 Connection FAILED: %s", url, e)
            raise


def _truncate(text: str, max_chars: int = 8000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n(truncated {len(text)} chars, showing first {max_chars})"


@mcp.tool()
async def knowledge_query(
    query: str,
    mode: Literal["local", "global", "hybrid", "naive", "mix"] = "mix",
) -> str:
    logger.info("[TOOL] knowledge_query query=%s mode=%s", query[:200], mode)
    try:
        result = await _api_post("/query", {"query": query, "mode": mode})
        return _truncate(json.dumps(result, ensure_ascii=False, indent=2))
    except httpx.HTTPStatusError as e:
        return f"[Error] LightRAG returned {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"[Error] Cannot connect to LightRAG ({LIGHTRAG_BASE}): {e}"


@mcp.tool()
async def knowledge_insert(file_path: str) -> str:
    logger.info("[TOOL] knowledge_insert file_path=%s", file_path)
    path = Path(file_path)
    if not path.exists():
        logger.warning("[TOOL] knowledge_insert file not found: %s", file_path)
        return f"[Error] File not found: {file_path}"

    try:
        file_size = path.stat().st_size
        logger.info("[TOOL] knowledge_insert uploading file=%s size=%s bytes", file_path, file_size)
        content = path.read_bytes()
        async with httpx.AsyncClient(timeout=300.0) as client:
            upload_url = f"{LIGHTRAG_BASE}/documents/text"
            logger.info("[REQ] POST %s multipart file=%s", upload_url, path.name)
            resp = await client.post(
                upload_url,
                headers=_headers(),
                files={"file": (path.name, content)},
            )
            logger.info("[RES] POST %s \u2192 %s | len=%s", upload_url, resp.status_code, len(resp.text))
            resp.raise_for_status()
            result = resp.json()
            logger.info("[TOOL] knowledge_insert success doc_id=%s",
                        result.get("document_id", result.get("id", "unknown")))
        return json.dumps(result, ensure_ascii=False, indent=2)
    except httpx.HTTPStatusError as e:
        return f"[Error] LightRAG returned {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"[Error] Cannot connect to LightRAG ({LIGHTRAG_BASE}): {e}"


@mcp.tool()
async def knowledge_list_documents(page: int = 1, page_size: int = 20) -> str:
    logger.info("[TOOL] knowledge_list_documents page=%s page_size=%s", page, page_size)
    try:
        result = await _api_get(f"/documents?page={page}&page_size={page_size}")
        return _truncate(json.dumps(result, ensure_ascii=False, indent=2))
    except httpx.HTTPStatusError as e:
        return f"[Error] LightRAG returned {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"[Error] Cannot connect to LightRAG ({LIGHTRAG_BASE}): {e}"


@mcp.tool()
async def knowledge_delete_document(doc_id: str) -> str:
    logger.info("[TOOL] knowledge_delete_document doc_id=%s", doc_id)
    try:
        result = await _api_delete(f"/documents/{doc_id}")
        return json.dumps(result, ensure_ascii=False, indent=2)
    except httpx.HTTPStatusError as e:
        return f"[Error] LightRAG returned {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"[Error] Cannot connect to LightRAG ({LIGHTRAG_BASE}): {e}"


@mcp.tool()
async def knowledge_get_context(query: str, top_k: int = 5) -> str:
    logger.info("[TOOL] knowledge_get_context query=%s top_k=%s", query[:200], top_k)
    try:
        result = await _api_post(
            "/query",
            {"query": query, "mode": "naive", "only_context": True, "top_k": top_k},
        )
        return _truncate(json.dumps(result, ensure_ascii=False, indent=2))
    except httpx.HTTPStatusError as e:
        return f"[Error] LightRAG returned {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"[Error] Cannot connect to LightRAG ({LIGHTRAG_BASE}): {e}"


@mcp.tool()
async def knowledge_status() -> str:
    logger.info("[TOOL] knowledge_status")
    try:
        result = await _api_get("/health")
        return json.dumps(result, ensure_ascii=False, indent=2)
    except httpx.HTTPStatusError as e:
        return f"[Error] LightRAG returned {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"[Error] Cannot connect to LightRAG ({LIGHTRAG_BASE}): {e}"


@mcp.tool()
async def knowledge_search_entities(keyword: str, limit: int = 20) -> str:
    logger.info("[TOOL] knowledge_search_entities keyword=%s limit=%s", keyword, limit)
    try:
        result = await _api_get(f"/entities?keyword={keyword}&limit={limit}")
        return _truncate(json.dumps(result, ensure_ascii=False, indent=2))
    except httpx.HTTPStatusError as e:
        return f"[Error] LightRAG returned {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"[Error] Cannot connect to LightRAG ({LIGHTRAG_BASE}): {e}"


@mcp.tool()
async def knowledge_search_relations(entity: str, depth: int = 1) -> str:
    logger.info("[TOOL] knowledge_search_relations entity=%s depth=%s", entity, depth)
    depth = min(max(depth, 1), 3)
    try:
        result = await _api_get(f"/entities/{entity}/relations?depth={depth}")
        return _truncate(json.dumps(result, ensure_ascii=False, indent=2))
    except httpx.HTTPStatusError as e:
        return f"[Error] LightRAG returned {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"[Error] Cannot connect to LightRAG ({LIGHTRAG_BASE}): {e}"


def main():
    parser = argparse.ArgumentParser(description="LiteRAG MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport: stdio (Claude Code default) or sse",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="SSE mode bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7463, help="SSE mode port (default 7463)")
    args = parser.parse_args()

    # Allow all Host headers (required when accessed via public IP / different domain)
    if args.transport == "sse":
        print(f"[MCP] SSE mode on {args.host}:{args.port}", flush=True)
        app = mcp.sse_app()
        uvicorn.run(app, host=args.host, port=args.port, log_level="info", proxy_headers=False, http="httptools")
    else:
        print("[MCP] stdio mode, waiting for Claude Code...", flush=True)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
