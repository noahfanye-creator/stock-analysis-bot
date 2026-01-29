#!/bin/bash

# 🚀 股票分析机器人 服务器一键部署脚本 (增强版 - 支持旧系统)
# 适用环境: Ubuntu / Debian (包括旧版本如 Debian 10)

set -e

PROJECT_NAME="stock-analysis-bot"
REPO_URL="https://github.com/noahfanye-creator/stock-analysis-bot.git"
INSTALL_DIR="$HOME/$PROJECT_NAME"
MAMBA_DIR="$HOME/micromamba"

echo "------------------------------------------------"
echo "🌟 开始部署股票分析机器人 (使用 Micromamba 管理环境)..."
echo "------------------------------------------------"

# 1. 安装必要的系统依赖
echo "📦 正在安装系统依赖 (Git, 中文字体, Curl)..."
sudo apt-get update
sudo apt-get install -y git fonts-wqy-zenhei curl bzip2

# 2. 安装 Micromamba (用于提供现代 Python 环境)
if [ ! -f "$HOME/bin/micromamba" ]; then
    echo "📥 正在下载并安装 Micromamba..."
    mkdir -p "$HOME/bin"
    curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C "$HOME/bin" --strip-components=1 bin/micromamba
fi

export PATH="$HOME/bin:$PATH"

# 3. 克隆或更新代码
if [ -d "$INSTALL_DIR" ]; then
    echo "📂 项目已存在，正在拉取最新代码..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo "🚚 正在克隆仓库..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 4. 创建 Python 3.11 环境
echo "🐍 正在创建 Python 3.11 虚拟环境..."
if [ -d "$INSTALL_DIR/venv" ]; then
    # 检查当前 venv 的 python 版本
    if [ -f "$INSTALL_DIR/venv/bin/python" ]; then
        VENV_VER=$("$INSTALL_DIR/venv/bin/python" --version 2>&1 | awk '{print $2}')
        if [[ ! "$VENV_VER" =~ ^3\.1 ]]; then
            echo "⚠️  检测到现有的 venv 版本 ($VENV_VER) 太旧，正在重置..."
            rm -rf "$INSTALL_DIR/venv"
        fi
    else
        rm -rf "$INSTALL_DIR/venv"
    fi
fi

if [ ! -d "$INSTALL_DIR/venv" ]; then
    $HOME/bin/micromamba create -y -p "$INSTALL_DIR/venv" -c conda-forge python=3.11
fi

# 5. 安装 Python 依赖
echo "⚙️  正在安装 Python 依赖库..."
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements-core.txt -r requirements-optional.txt
./venv/bin/python -m pip install pytz google-auth-oauthlib google-auth google-api-python-client python-dotenv

# 6. 初始化配置文件
if [ ! -f "config/config.yaml" ] && [ -f "config/config.example.yaml" ]; then
    echo "📝 正在初始化配置文件..."
    cp config/config.example.yaml config/config.yaml
fi

# 7. 设置环境变量文件 (.env)
if [ ! -f ".env" ]; then
    echo "🔐 正在创建 .env 模板..."
    cat > .env <<EOF
# Telegram 配置
TELEGRAM_BOT_TOKEN=8371667461:AAGXMmYflhwuVFt1tE5lIlOtgxXeoXi7Fhg
TELEGRAM_CHAT_ID=5920715689

# Google Drive OAuth 配置
GDRIVE_CLIENT_ID=
GDRIVE_CLIENT_SECRET=
GDRIVE_REFRESH_TOKEN=
GDRIVE_FOLDER_ID=1g_45mJ9b7UZ3UfC0SaAtjYEHOmYhm7pB
EOF
    echo "⚠️  已自动填入 Telegram 和 Folder ID，请手动编辑 .env 补全 GDRIVE_CLIENT_ID 等 OAuth 信息。"
fi

echo ""
echo "================================================"
echo "✅ 基础环境部署完成！"
echo "================================================"
echo "🎯 请按照以下步骤完成最后配置："
echo ""
echo "1. 进入目录: cd $INSTALL_DIR"
echo "2. 编辑变量: nano .env (补全 Google OAuth 的 Client ID, Secret 和 Refresh Token)"
echo "3. 运行测试: ./venv/bin/python github_stock_bot.py --mode manual --stocks '600460'"
echo "4. 开启定时任务: 执行 'crontab -e' 并添加以下行："
echo ""
echo "# 每天 15:05 自动运行分析"
echo "5 15 * * 1-5 cd $INSTALL_DIR && ./venv/bin/python github_stock_bot.py --mode manual"
echo "================================================"
