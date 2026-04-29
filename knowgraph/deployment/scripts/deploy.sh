#!/bin/bash
# 学知图谱 — 一键部署脚本
# Usage: bash scripts/deploy.sh

set -e

echo "🧠 学知图谱 — 部署脚本"
echo "======================"
echo ""

# Check prerequisites
echo "📋 检查依赖..."
command -v docker >/dev/null 2>&1 || { echo "❌ 需要安装 Docker"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1 || { echo "❌ 需要安装 Docker Compose"; exit 1; }
echo "✅ Docker 就绪"

# Check for .env
if [ ! -f .env ]; then
  echo ""
  echo "⚠️  未找到 .env 文件"
  echo "   正在从 .env.example 创建..."
  cp .env.example .env
  echo "   请编辑 .env 文件填入你的 LLM API 密钥"
  echo "   $ nano .env"
  echo ""
  read -p "   按回车继续部署 (或 Ctrl+C 先配置密钥)..."
fi

# Choose deployment mode
echo ""
echo "请选择 LLM 模式:"
echo "  1) API 模式 (默认) — 使用 DeepSeek/OpenAI 等云端 API"
echo "  2) 本地模式 — 在双 4090 上运行本地模型 (vLLM)"
read -p "选择 [1/2]: " llm_mode

if [ "$llm_mode" = "2" ]; then
  # Local mode
  echo ""
  echo "📦 本地模式需准备模型文件"
  echo "   将 GGUF 或 HuggingFace 格式的模型放在 /path/to/models"
  read -p "   模型路径 [/data/models]: " model_path
  model_path=${model_path:-/data/models}

  export LLM_MODE=local
  sed -i "s|LLM_MODE=api|LLM_MODE=local|" .env
  echo "✅ 已切换到本地模式"
else
  export LLM_MODE=api
  echo "✅ 使用 API 模式"
fi

# Deploy
echo ""
echo "🚀 启动服务..."
docker compose up -d --build

echo ""
echo "✅ 部署完成!"
echo ""
echo "访问地址:"
echo "  🌐 前端界面:  http://localhost:3000"
echo "  🔌 API 文档:  http://localhost:8000/docs"
echo "  🎙️ Whisper:   http://localhost:8001/health"
echo "  🤖 LLM:       http://localhost:8002/health"
echo ""
echo "查看日志:"
echo "  docker compose logs -f"
echo ""
echo "停止服务:"
echo "  docker compose down"
