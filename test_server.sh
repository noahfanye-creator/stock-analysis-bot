#!/bin/bash

# 🧪 服务器测试脚本
# 用途: 快速测试股票分析机器人在服务器上的运行情况

set -e

echo "=========================================="
echo "🧪 股票分析机器人 - 服务器测试"
echo "=========================================="
echo ""

# 检查是否在服务器上
if [ ! -d "/root/stock-analysis-bot" ] && [ ! -d "$HOME/stock-analysis-bot" ]; then
    echo "❌ 错误: 未找到项目目录"
    echo "请先运行部署脚本: bash deploy_server.sh"
    exit 1
fi

# 确定项目目录
if [ -d "/root/stock-analysis-bot" ]; then
    PROJECT_DIR="/root/stock-analysis-bot"
else
    PROJECT_DIR="$HOME/stock-analysis-bot"
fi

cd "$PROJECT_DIR"

echo "📂 项目目录: $PROJECT_DIR"
echo ""

# 1. 检查 Python 环境
echo "1️⃣  检查 Python 环境..."
PYTHON_VER=$("./venv/bin/python" --version 2>&1)
echo "   $PYTHON_VER"
if [[ ! "$PYTHON_VER" =~ "Python 3.1" ]]; then
    echo "   ⚠️  警告: Python 版本可能不兼容"
fi
echo ""

# 2. 检查 .env 文件
echo "2️⃣  检查环境变量配置..."
if [ ! -f ".env" ]; then
    echo "   ❌ .env 文件不存在"
    echo "   请运行: nano .env 创建配置文件"
    exit 1
fi

# 检查关键变量
source .env 2>/dev/null || true
MISSING_VARS=()

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    MISSING_VARS+=("TELEGRAM_BOT_TOKEN")
fi
if [ -z "$TELEGRAM_CHAT_ID" ]; then
    MISSING_VARS+=("TELEGRAM_CHAT_ID")
fi
if [ -z "$GDRIVE_CLIENT_ID" ]; then
    MISSING_VARS+=("GDRIVE_CLIENT_ID")
fi
if [ -z "$GDRIVE_CLIENT_SECRET" ]; then
    MISSING_VARS+=("GDRIVE_CLIENT_SECRET")
fi
if [ -z "$GDRIVE_REFRESH_TOKEN" ]; then
    MISSING_VARS+=("GDRIVE_REFRESH_TOKEN")
fi
if [ -z "$GDRIVE_FOLDER_ID" ]; then
    MISSING_VARS+=("GDRIVE_FOLDER_ID")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "   ⚠️  以下环境变量未配置:"
    for var in "${MISSING_VARS[@]}"; do
        echo "      - $var"
    done
    echo ""
    echo "   请编辑 .env 文件补全配置:"
    echo "   nano .env"
    echo ""
    read -p "   是否继续测试？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "   ✅ 环境变量配置完整"
fi
echo ""

# 3. 检查依赖
echo "3️⃣  检查 Python 依赖..."
if ! "./venv/bin/python" -c "import pandas, numpy, matplotlib" 2>/dev/null; then
    echo "   ⚠️  部分依赖缺失，正在安装..."
    ./venv/bin/python -m pip install -q -r requirements-core.txt -r requirements-optional.txt
    echo "   ✅ 依赖安装完成"
else
    echo "   ✅ 核心依赖已安装"
fi
echo ""

# 4. 运行测试
echo "4️⃣  开始运行测试..."
echo "   测试股票: 600460 (士兰微)"
echo ""

# 运行测试（使用 600460 作为测试股票）
./venv/bin/python github_stock_bot.py --mode manual --stocks '600460'

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ 测试完成！"
    echo ""
    echo "📊 查看生成的报告:"
    echo "   ls -lh reports/reports_*/"
    echo ""
    echo "📤 检查 Google Drive 上传:"
    echo "   访问你的 Google Drive 文件夹确认"
    echo ""
    echo "📱 检查 Telegram 通知:"
    echo "   查看你的 Telegram 是否收到消息"
else
    echo "❌ 测试失败 (退出码: $TEST_EXIT_CODE)"
    echo ""
    echo "请检查上面的错误信息，常见问题："
    echo "  - 网络连接问题"
    echo "  - Google OAuth 配置错误"
    echo "  - 依赖缺失"
fi
echo "=========================================="
