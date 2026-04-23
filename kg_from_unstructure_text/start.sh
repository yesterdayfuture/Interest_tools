#!/bin/bash

# 电商客服图谱系统启动脚本

echo "🚀 启动电商客服图谱系统..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -q -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "⚠️ 警告: 未找到.env文件，使用默认配置"
    cp .env.example .env
fi

# 创建必要目录
mkdir -p data uploads

# 启动服务
echo "✅ 启动服务..."
echo "📚 API文档: http://localhost:8000/docs"
echo "🔍 健康检查: http://localhost:8000/health"
echo ""

python3 main.py