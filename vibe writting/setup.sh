#!/bin/bash
# ============================================================
# Vibe Writing 一键安装脚本
# AI 驱动的长篇小说创作平台
# ============================================================

set -e

echo "🚀 Vibe Writing 安装脚本"
echo "========================"
echo ""

# ------------------------------------------------------------
# 第 1 步：检查 Python3 是否已安装
# 后端使用 Python 编写，需要 Python 3.9+
# ------------------------------------------------------------
echo "📋 第 1 步：检查 Python3 环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装：https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION 已就绪"
echo ""

# ------------------------------------------------------------
# 第 2 步：检查 Node.js 是否已安装
# 前端使用 React + Vite 构建，需要 Node.js 18+
# ------------------------------------------------------------
echo "📋 第 2 步：检查 Node.js 环境..."
if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js，请先安装：https://nodejs.org/"
    exit 1
fi
NODE_VERSION=$(node --version)
echo "✅ Node.js $NODE_VERSION 已就绪"
echo ""

# ------------------------------------------------------------
# 第 3 步：安装后端 Python 依赖
# 包含 FastAPI、SQLAlchemy、Anthropic SDK 等
# 使用清华镜像加速下载
# ------------------------------------------------------------
echo "📋 第 3 步：安装后端依赖..."
echo "   → FastAPI (Web 框架)"
echo "   → SQLAlchemy (数据库 ORM)"
echo "   → Anthropic SDK (AI 模型接口)"
echo "   → 其他依赖..."
cd backend
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
cd ..
echo "✅ 后端依赖安装完成"
echo ""

# ------------------------------------------------------------
# 第 4 步：安装前端 Node 依赖
# 包含 React、Vite、TailwindCSS、Tiptap 编辑器等
# ------------------------------------------------------------
echo "📋 第 4 步：安装前端依赖..."
echo "   → React + Vite (构建框架)"
echo "   → TailwindCSS (样式框架)"
echo "   → Tiptap (富文本编辑器)"
echo "   → Zustand (状态管理)"
cd frontend
npm install
cd ..
echo "✅ 前端依赖安装完成"
echo ""

# ------------------------------------------------------------
# 第 5 步：创建数据存储目录
# SQLite 数据库和模型配置文件存放在此
# ------------------------------------------------------------
echo "📋 第 5 步：创建数据目录..."
mkdir -p backend/data
echo "✅ 数据目录已创建: backend/data/"
echo ""

# ------------------------------------------------------------
# 安装完成，输出启动说明
# ------------------------------------------------------------
echo "════════════════════════════════════════"
echo "✅ Vibe Writing 安装完成！"
echo "════════════════════════════════════════"
echo ""
echo "📌 启动方式："
echo "   ./start.sh"
echo ""
echo "📌 或手动启动："
echo "   终端 1: cd backend && python3 -m uvicorn app.main:app --reload --port 8000"
echo "   终端 2: cd frontend && npm run dev"
echo ""
echo "📌 访问地址："
echo "   前端界面: http://localhost:5173"
echo "   后端 API: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo ""
echo "📌 首次使用："
echo "   1. 打开 http://localhost:5173"
echo "   2. 进入「设置」页面"
echo "   3. 配置 AI 模型 API Key（支持 OpenAI / DeepSeek / 智谱 / Moonshot / Ollama 等）"
echo "   4. 创建项目，开始创作"
