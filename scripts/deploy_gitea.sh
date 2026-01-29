#!/bin/bash

# Gitea 部署脚本
# 在服务器上安装和配置 Gitea Git 服务

set -e

GITEA_VERSION="1.21.0"
GITEA_USER="git"
GITEA_HOME="/var/lib/gitea"
GITEA_BINARY="/usr/local/bin/gitea"
GITEA_WORK_DIR="/var/lib/gitea"
GITEA_CONFIG="/etc/gitea/app.ini"
DOMAIN="git.faninvest.com"

echo "=========================================="
echo "🚀 开始部署 Gitea"
echo "=========================================="
echo ""

# 1. 创建 git 用户
if ! id "$GITEA_USER" &>/dev/null; then
    echo "📦 创建 git 用户..."
    useradd -r -s /bin/bash -d "$GITEA_HOME" -m "$GITEA_USER"
    echo "✅ 用户创建成功"
else
    echo "✅ git 用户已存在"
fi

# 2. 创建必要的目录
echo "📁 创建目录结构..."
mkdir -p "$GITEA_HOME"
mkdir -p "$GITEA_HOME/.ssh"
mkdir -p "$GITEA_HOME/repositories"
mkdir -p "$GITEA_HOME/data"
mkdir -p "$GITEA_HOME/log"
mkdir -p /etc/gitea
chown -R "$GITEA_USER:$GITEA_USER" "$GITEA_HOME"
chmod 700 "$GITEA_HOME/.ssh"
echo "✅ 目录创建完成"

# 3. 下载 Gitea 二进制文件
echo "📥 下载 Gitea ${GITEA_VERSION}..."
if [ ! -f "$GITEA_BINARY" ]; then
    cd /tmp
    wget -q "https://dl.gitea.com/gitea/${GITEA_VERSION}/gitea-${GITEA_VERSION}-linux-amd64" -O gitea
    chmod +x gitea
    mv gitea "$GITEA_BINARY"
    chown "$GITEA_USER:$GITEA_USER" "$GITEA_BINARY"
    echo "✅ Gitea 下载完成"
else
    echo "✅ Gitea 已存在"
fi

# 4. 创建配置文件
echo "⚙️  创建配置文件..."
cat > "$GITEA_CONFIG" << EOF
APP_NAME = Gitea: Git with a cup of tea
RUN_USER = $GITEA_USER
RUN_MODE = prod

[server]
DOMAIN           = $DOMAIN
HTTP_PORT        = 3000
ROOT_URL         = https://$DOMAIN/
DISABLE_SSH      = false
SSH_PORT         = 2222
SSH_LISTEN_PORT  = 2222
START_SSH_SERVER = true

[database]
DB_TYPE  = sqlite3
PATH     = $GITEA_HOME/data/gitea.db

[repository]
ROOT = $GITEA_HOME/repositories

[log]
ROOT_PATH = $GITEA_HOME/log
MODE      = file
LEVEL     = Info

[security]
INSTALL_LOCK = true
SECRET_KEY   = $(openssl rand -hex 32)

[service]
DISABLE_REGISTRATION = false
ENABLE_CAPTCHA       = true

[paths]
APP_DATA_PATH = $GITEA_HOME/data
EOF

chown "$GITEA_USER:$GITEA_USER" "$GITEA_CONFIG"
chmod 600 "$GITEA_CONFIG"
echo "✅ 配置文件创建完成"

# 5. 创建 systemd 服务
echo "🔧 创建 systemd 服务..."
cat > /etc/systemd/system/gitea.service << EOF
[Unit]
Description=Gitea (Git with a cup of tea)
After=network.target

[Service]
Type=simple
User=$GITEA_USER
Group=$GITEA_USER
WorkingDirectory=$GITEA_WORK_DIR
ExecStart=$GITEA_BINARY web --config $GITEA_CONFIG
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "✅ systemd 服务创建完成"

# 6. 启动 Gitea（首次运行需要初始化）
echo "🚀 启动 Gitea 服务..."
if ! systemctl is-active --quiet gitea; then
    systemctl enable gitea
    systemctl start gitea
    echo "✅ Gitea 服务已启动"
else
    systemctl restart gitea
    echo "✅ Gitea 服务已重启"
fi

# 等待服务启动
sleep 3

# 检查服务状态
if systemctl is-active --quiet gitea; then
    echo ""
    echo "=========================================="
    echo "✅ Gitea 部署完成！"
    echo "=========================================="
    echo ""
    echo "📋 访问信息："
    echo "   URL: https://$DOMAIN"
    echo "   SSH 端口: 2222"
    echo ""
    echo "📝 下一步："
    echo "   1. 访问 https://$DOMAIN 完成初始设置"
    echo "   2. 创建管理员账户"
    echo "   3. 配置 Nginx 反向代理（如果尚未配置）"
    echo ""
else
    echo "❌ Gitea 服务启动失败，请检查日志："
    echo "   journalctl -u gitea -n 50"
    exit 1
fi
