 # LiteRAG 企业知识图谱系统 — 设计文档

 **日期：** 2026-06-26
 **状态：** 设计稿（待实现）

 ---

 ## 1. 项目概述

 基于 [LightRAG](https://github.com/HKUDS/LightRAG) 构建企业级知识图谱系统，管理混合格式的企业知识资产（PDF、Office、图片、Markdown 等，万级文档量），通过 MCP 协议向 AI Agent（Claude Code）提供知识检索与文档管理能力，使用 Docker 部署到本地。

 **核心组件：**
 - LightRAG 引擎（知识图谱构建 + 双级检索 + REST API + WebUI）
 - PostgreSQL + pgvector（KV 存储 + 向量索引 + 文档元数据）
 - Neo4J（知识图谱持久化）
 - Ollama（本地 Embedding）
 - DeepSeek API（远程 LLM）
 - LiteRAG MCP Server（MCP 协议适配层）

 > **注：** LightRAG v1.5+ 已原生集成 RAG-Anything 的多模态文档解析能力（MinerU / Docling），不再需要独立 RAG-Anything 容器。

 **参考项目：**
 - [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) — 核心 RAG 引擎
 - [HKUDS/RAG-Anything](https://github.com/HKUDS/RAG-Anything) — 多模态文档解析

 ---

 ## 2. 系统架构

 ### 2.1 总体架构

 ```
 ┌─────────────────────────────────────────────────────────┐
 │                   远程 LLM API                           │
 │               DeepSeek (LLM 角色)                        │
 └────────────────────┬────────────────────────────────────┘
                      │ HTTP
 ┌────────────────────┴────────────────────────────────────┐
 │                  LightRAG 核心引擎                        │
 │    知识图谱构建 / 实体关系抽取 / 双级检索 / 增量更新        │
 └──┬────────────┬────────────┬────────────┬───────────────┘
    │            │            │            │
    ▼            ▼            ▼            ▼
 ┌──────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
 │Neo4J │  │PostgreSQL│  │ Ollama   │  │ 文档解析      │
 │图存储│  │KV+向量+   │  │Embedding │  │(LightRAG内嵌) │
 │      │  │文档状态   │  │(本地)    │  │              │
 └──────┘  └──────────┘  └──────────┘  └──────────────┘

 ┌─────────────────────────────────────────────────────────┐
 │                  对外接口层                                │
 │  ┌──────────────┐  ┌──────────────────────────────────┐ │
 │  │ LightRAG     │  │  LiteRAG MCP Server               │ │
 │  │ WebUI + REST │  │  (MCP 协议适配, stdio 传输)       │ │
 │  │ Port 9621    │  │                                  │ │
 │  └──────────────┘  └──────────────┬───────────────────┘ │
 └───────────────────────────────────┼─────────────────────┘
                                     │ MCP Protocol
                              ┌──────┴──────┐
                              │  Claude Code │
                              │  AI Agent    │
                              └─────────────┘
 ```

 ### 2.2 数据流

 **文档入库流程：**

 1. 用户 / AI Agent 上传文档到 `data/inputs/` 或通过 API 提交
 2. LightRAG 原生解析文档（多模态引擎自动处理 PDF → 文本+表格+图片，Office → 结构化内容）
 3. LightRAG 调用 Ollama 生成 Embedding
 4. LightRAG 调用 DeepSeek API 抽取实体和关系，构建知识图谱
 5. 实体和关系存入 Neo4J，向量存入 PostgreSQL(pgvector)，KV 和文档元数据存入 PostgreSQL
 6. 返回文档 ID 和索引状态

 **查询流程：**

 1. AI Agent（Claude Code）通过 MCP Tool 发起查询
 2. MCP Server 将请求转发到 LightRAG REST API
 3. LightRAG 从 Neo4J 检索图结构，从 PostgreSQL 检索向量相似度
 4. LightRAG 调用 DeepSeek 做最终生成
 5. MCP Server 格式化结果（含来源引用）返回给 Claude Code

 ---

 ## 3. 容器编排

 ### 3.1 项目目录结构

 ```
 literag/
 ├── docker-compose.yml           # 主编排文件
 ├── .env                         # 环境配置
 ├── config.ini                   # LightRAG 额外配置
 ├── Dockerfile.mcp               # MCP Server 构建文件
 ├── mcp_server/
 │   ├── server.py                # MCP Tool 实现
 │   └── requirements.txt
 ├── data/
 │   ├── rag_storage/             # LightRAG 持久化
 │   ├── inputs/                  # 文档上传目录
 │   ├── prompts/                 # 自定义 prompt 模板
 │   ├── neo4j/                   # Neo4J 数据持久化
 │   └── postgres/                # PostgreSQL 数据持久化
 └── scripts/
     └── setup.sh                 # 初始化脚本
 ```

 ### 3.2 容器清单

 | 容器 | 镜像 | 端口 | 职责 |
 |---|---|---|---|
 | `lightrag` | `ghcr.io/hkuds/lightrag:latest` | 9621 | 核心 RAG 引擎 + WebUI + REST API |
 | `neo4j` | `neo4j:5-community` | 7687(bolt), 7474(web) | 知识图谱持久化 |
 | `postgres` | `pgvector/pgvector:pg18` | 5432 | KV + 向量 + 文档元数据 |
 | `mcp-server` | 自建 (`Dockerfile.mcp`) | 7463 | MCP 协议适配 |
 | `ollama` | (用户已有，通过 host.docker.internal 访问) | — | Embedding 模型推理 |

 ### 3.3 网络与安全

 - 所有容器在 `literag-net` bridge 网络内
 - 对外暴露端口：
   - `9621` — LightRAG WebUI + REST API（需配置 `LIGHTRAG_API_KEY` 认证）
   - `7463` — MCP Server（Claude Code 连接用）
   - `7474` — Neo4J Browser（开发调试用，可选）
 - 内部通信不走认证，同网络内安全

 ### 3.4 数据卷

 | 卷 | 容器内路径 | 宿主路径 |
 |---|---|---|
 | `rag_storage` | `/app/data/rag_storage` | `./data/rag_storage` |
 | `inputs` | `/app/data/inputs` | `./data/inputs` |
 | `prompts` | `/app/data/prompts` | `./data/prompts` |
 | `neo4j_data` | `/data` | `./data/neo4j` |
 | `postgres_data` | `/var/lib/postgresql` | `./data/postgres` |

 ---

 ## 4. LLM / Embedding / Storage 配置 (.env)

 ### 4.1 LLM 配置（DeepSeek 远程 API）

 ```
 # LLM 角色 — 查询生成
 LLM_BINDING_HOST=https://api.deepseek.com
 LLM_BINDING_API_KEY=sk-your-deepseek-key
 LLM_BINDING_MODEL=deepseek-chat

 # 抽取角色（可选，单独指定抽取用的模型，默认同 LLM）
 # EXTRACT_LLM_BINDING_HOST=
 # EXTRACT_LLM_BINDING_MODEL=
 ```

 ### 4.2 Embedding 配置（本地 Ollama）

 ```
 EMBEDDING_BINDING_HOST=http://host.docker.internal:11434/v1
 EMBEDDING_BINDING_API_KEY=
 EMBEDDING_BINDING_MODEL=bge-m3
 ```

 ### 4.3 存储配置

 ```
 # PostgreSQL — KV + 向量 + 文档元数据
 LIGHTRAG_STORAGE_TYPE=PostgresStorage
 POSTGRES_HOST=postgres
 POSTGRES_PORT=5432
 POSTGRES_USER=rag
 POSTGRES_PASSWORD=rag
 POSTGRES_DATABASE=rag

 # Neo4J — 知识图谱
 LIGHTRAG_GRAPH_STORAGE_TYPE=Neo4JStorage
 NEO4J_URI=neo4j://neo4j:7687
 NEO4J_USERNAME=neo4j
 NEO4J_PASSWORD=lightrag_neo4j
 ```

 ### 4.4 安全配置

 ```
 LIGHTRAG_API_KEY=your-lightrag-api-key
 HOST=0.0.0.0
 PORT=9621
 ```

 ---

 ## 5. MCP Server 设计

 ### 5.1 实现方式

 - 基于 `mcp` Python SDK（`pip install mcp`）
 - 使用 `stdio` 传输协议（Claude Code 默认模式）
 - 服务端收到 Tool 调用后，HTTP 请求 LightRAG REST API（带 `X-API-Key` 认证）
 - 结果格式化后返回给 Claude Code

 ### 5.2 Tool 清单

 | Tool 名 | 作用 | 参数 |
 |---|---|---|
 | `knowledge_query` | 知识库查询 | `query: str`, `mode: "local"|"global"|"hybrid"|"mix"` (默认 mix) |
 | `knowledge_insert` | 上传并索引文档 | `file_path: str` |
 | `knowledge_list_documents` | 列出已索引文档 | `page: int`, `page_size: int` |
 | `knowledge_delete_document` | 删除文档并重建图 | `doc_id: str` |
 | `knowledge_get_context` | 获取查询上下文（含来源引用） | `query: str`, `top_k: int` |
 | `knowledge_status` | 系统概览（文档数/实体数/关系数） | 无 |
 | `knowledge_search_entities` | 按关键词搜索图实体 | `keyword: str`, `limit: int` |
 | `knowledge_search_relations` | 查询实体间关系 | `entity: str`, `depth: int` |

 ### 5.3 关键实现约束

 - 返回结果长度需要适配 Claude Code 的上下文窗口，超长内容自动截断或分页
 - `knowledge_query` 返回结果需要包含文档来源链接和引用供 Agent 溯源
 - 错误处理：网络超时、API 错误、空结果都返回清晰的错误信息

 ---

 ## 6. 预期工作流

 ### 6.1 管理员初始化

 ```bash
 git clone <repo> literag
 cd literag
 docker compose up -d
 # 访问 http://localhost:9621 确认 LightRAG 运行正常
 ```

 ### 6.2 文档录入

 - 通过 LightRAG WebUI 上传文档（开发调试用）
 - 通过 MCP Tool `knowledge_insert` 批量上传（生产用）
 - 文档自动经 LightRAG 原生多模态解析 → 建索引 → 存入 Neo4J + PostgreSQL

 ### 6.3 Claude Code 集成

 Claude Code 通过 MCP 协议连接 `mcp-server`，在对话中自然调用知识库查询：

 - "搜索公司最新的技术架构文档" → `knowledge_query`
 - "上传这份季度报告 PDF" → `knowledge_insert`
 - "这个需求的背景在我之前存的设计文档里，帮我查一下" → `knowledge_query`

 ---

 ## 7. 暂未纳入（YAGNI）

 - GPU 加速向量检索：万级文档 pgvector HNSW 已够用
 - 独立的图分析工作台：Neo4J Browser 满足调试需求，暂不需要定制前端
 - 多租户隔离：当前设计为单团队使用，未来可按需在 REST API 层扩展
 - 分布式部署：单机 Docker Compose 够用，未来可通过 K8s/Docker Swarm 扩展
