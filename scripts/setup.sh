 #!/usr/bin/env bash
 set -euo pipefail

# ════════════════════════════════════════════
# LiteRAG 初始化脚本
# 用法: bash scripts/setup.sh
# ════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  LiteRAG 企业知识图谱系统 - 初始化"
echo "============================================"
echo ""

# ── 1. 检查环境 ──────────────────────────────

echo "[1/5] 检查依赖..."
if ! command -v docker &>/dev/null; then
    echo "❌ 未找到 Docker，请先安装: https://docs.docker.com/engine/install/"
    exit 1
fi
echo "   ✅ Docker $(docker --version | cut -d' ' -f3 | tr -d ',')"

if ! docker compose version &>/dev/null; then
    echo "❌ 未找到 Docker Compose，请安装: https://docs.docker.com/compose/install/"
    exit 1
fi
echo "   ✅ Docker Compose $(docker compose version | cut -d' ' -f4 | tr -d ',')"

# ── 2. 配置 Docker 国内镜像加速（可选）────────

echo ""
echo "[2/5] Docker 镜像加速配置..."
if [ -f /etc/docker/daemon.json ]; then
    echo "   ⚠️  /etc/docker/daemon.json 已存在，跳过自动配置"
    echo "   如需加速，请手动添加 registry-mirrors:"
    echo "     https://docker.mirrors.ustc.edu.cn"
    echo "     https://registry.cn-hangzhou.aliyuncs.com"
else
    read -rp "   是否配置 Docker 国内镜像加速？(y/n, default: y): " setup_mirror
    if [[ "${setup_mirror:-y}" =~ ^[Yy] ]]; then
        echo "   配置 Docker 镜像加速..."
        cat > /tmp/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.cn-hangzhou.aliyuncs.com"
  ]
}
EOF
        if [ "$(id -u)" -eq 0 ]; then
            cp /tmp/daemon.json /etc/docker/daemon.json
            echo "   ✅ 配置已写入 /etc/docker/daemon.json"
        else
            echo "   ⚠️  需要 root 权限写入 /etc/docker/daemon.json"
            echo "   请手动执行: sudo cp /tmp/daemon.json /etc/docker/daemon.json"
        fi
        echo "   重启 Docker 后生效: sudo systemctl restart docker"
    else
        echo "   ⏭️  跳过"
    fi
fi

# ── 3. 创建 .env（如果不存在）──────────────────

echo ""
echo "[3/5] 环境配置..."
if [ ! -f .env ]; then
    cp .env .env
    echo "   ⚠️  .env 已存在（模板），请编辑以下关键配置:"
else
    echo "   ✅ .env 已存在"
fi
echo ""
echo "   必须修改:"
echo "     - LLM_BINDING_API_KEY=sk-your-deepseek-api-key"
echo "     - LIGHTRAG_API_KEY=change-me-to-a-random-key"
echo "   按需修改:"
echo "     - EMBEDDING_BINDING_MODEL=bge-m3 （你的 Ollama 模型名）"
echo ""

# ── 4. 检查数据目录 ──────────────────────────

echo "[4/5] 创建数据目录..."
mkdir -p data/rag_storage data/inputs data/prompts data/neo4j data/postgres
echo "   ✅ 数据目录已就绪"

# ── 5. 启动服务 ──────────────────────────────

echo ""
echo "[5/5] 启动 Docker 服务..."
echo ""
echo "   执行以下命令启动所有服务:"
echo ""
echo "   docker compose build    # 构建 MCP Server 镜像"
echo "   docker compose up -d    # 启动所有服务"
echo ""
echo "   启动后访问:"
echo "     - LightRAG WebUI: http://localhost:9621"
echo "     - Neo4J Browser:  http://localhost:7474 (neo4j/lightrag_neo4j)"
echo "     - MCP Server:     stdio://localhost:7463"
echo ""
echo "============================================"
echo "  🚀 初始化完成！"
echo "============================================"
echo ""
echo "将 Claude Code 连接到 MCP Server 的配置示例:"
echo ""
echo '  claude_code_mcp_config.json:'
echo '  {'
echo '    "mcpServers": {'
echo '      "literag-kb": {'
echo '        "command": "docker",'
echo '        "args": ["exec", "-i", "literag-mcp-server-1", "python", "server.py", "--transport", "stdio"]'
echo '      }'
echo '    }'
echo '  }'
echo ""
echo "或者直接运行:"
echo "  docker exec -it literag-mcp-server-1 python server.py --transport sse --port 7463"
echo ""
