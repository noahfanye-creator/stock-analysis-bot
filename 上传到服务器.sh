#!/bin/bash

# 从本机上传 stock-analysis-bot 代码到服务器
# 用法：在本机执行 bash 上传到服务器.sh

set -e

# ========== 请按你的环境修改这两项 ==========
SERVER_IP="154.17.3.182"
PRIVATE_KEY="/Users/fanye/Documents/ssh_rsa_keys/private_key/id_rsa.pem"
# ==========================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "📤 上传代码到服务器 $SERVER_IP"
echo "=========================================="
echo "本地目录: $PROJECT_DIR"
echo ""

if [ ! -f "$PRIVATE_KEY" ]; then
    echo "❌ 找不到私钥文件: $PRIVATE_KEY"
    echo "请修改脚本里的 PRIVATE_KEY 为你的私钥路径"
    exit 1
fi

# 使用 rsync 上传（排除 .git、reports 里的报告、__pycache__、.env 等）
rsync -avz --progress \
  -e "ssh -i $PRIVATE_KEY -o StrictHostKeyChecking=no" \
  --exclude='.git' \
  --exclude='reports/reports_*' \
  --exclude='reports/*.pdf' \
  --exclude='reports/*.zip' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  "$PROJECT_DIR/" root@"$SERVER_IP":~/stock-analysis-bot/

echo ""
echo "=========================================="
echo "✅ 上传完成"
echo "=========================================="
echo ""
echo "下一步：登录服务器并运行"
echo "  ssh -i $PRIVATE_KEY root@$SERVER_IP"
echo "  cd ~/stock-analysis-bot"
echo "  ./venv/bin/python github_stock_bot.py --mode manual --stocks '688630'"
echo ""
