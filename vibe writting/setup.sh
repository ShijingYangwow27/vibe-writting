#!/bin/bash
# Vibe Writing 一键安装脚本

set -e

echo "🚀 Vibe Writing 安装脚本"
echo "========================"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装：https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js，请先安装：https://nodejs.org/"
    exit 1
fi
NODE_VERSION=$(node --version)
echo "✅ Node.js $NODE_VERSION"

# 安装后端依赖
echo ""
echo "📦 安装后端依赖..."
cd backend
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
cd ..

# 安装前端依赖
echo ""
echo "📦 安装前端依赖..."
cd frontend
npm install
cd ..

# 创建数据目录
mkdir -p backend/data

echo ""
echo "✅ 安装完成！"
echo ""
echo "启动方式："
echo "  ./start.sh"
echo ""
echo "或手动启动："
echo "  终端 1: cd backend && python3 -m uvicorn app.main:app --reload --port 8000"
echo "  终端 2: cd frontend && npm run dev"
echo ""
echo "访问 http://localhost:5173 开始使用"
echo "首次使用请在「设置」页面配置 AI 模型 API Key"
