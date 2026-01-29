#!/bin/bash

# 报告查看器部署脚本
# 在服务器上部署 Flask 报告查看器服务

set -e

PROJECT_DIR="/root/stock-analysis-bot"
SERVICE_NAME="stock-report-viewer"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
DOMAIN="reports.faninvest.com"

echo "=========================================="
echo "🚀 开始部署报告查看器"
echo "=========================================="
echo ""

# 1. 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 项目目录不存在: $PROJECT_DIR"
    echo "请先运行 deploy_server.sh 部署项目"
    exit 1
fi

cd "$PROJECT_DIR"

# 2. 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行 deploy_server.sh"
    exit 1
fi

# 3. 安装 Flask（如果未安装）
echo "📦 检查 Flask 依赖..."
if ! ./venv/bin/python -c "import flask" 2>/dev/null; then
    echo "正在安装 Flask..."
    ./venv/bin/python -m pip install -q Flask
    echo "✅ Flask 安装完成"
else
    echo "✅ Flask 已安装"
fi

# 4. 创建 systemd 服务
echo "🔧 创建 systemd 服务..."
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Stock Analysis Report Viewer
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/web/report_viewer.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
echo "✅ systemd 服务创建完成"

# 5. 启动服务
echo "🚀 启动报告查看器服务..."
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    echo "✅ 服务已启动"
else
    systemctl restart "$SERVICE_NAME"
    echo "✅ 服务已重启"
fi

# 等待服务启动
sleep 2

# 检查服务状态
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "=========================================="
    echo "✅ 报告查看器部署完成！"
    echo "=========================================="
    echo ""
    echo "📋 访问信息："
    echo "   URL: https://$DOMAIN"
    echo "   本地: http://127.0.0.1:5000"
    echo ""
    echo "📝 下一步："
    echo "   1. 配置 Nginx 反向代理（如果尚未配置）"
    echo "   2. 访问 https://$DOMAIN 查看报告"
    echo ""
    echo "🔍 查看日志："
    echo "   journalctl -u $SERVICE_NAME -f"
    echo ""
else
    echo "❌ 服务启动失败，请检查日志："
    echo "   journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi
