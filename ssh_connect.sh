#!/bin/bash

# SSH 连接脚本 - 用于重置密码
# 使用方法: ./ssh_connect.sh

SERVER_IP="154.17.3.182"
PRIVATE_KEY="/Users/fanye/Documents/ssh_rsa_keys/private_key/id_rsa.pem"

echo "正在连接到服务器 $SERVER_IP..."
echo ""
echo "连接成功后，请执行以下命令重置密码："
echo "  passwd root"
echo ""
echo "然后输入新密码两次。"
echo ""
echo "按 Enter 继续连接..."
read

ssh -i "$PRIVATE_KEY" -o StrictHostKeyChecking=no root@"$SERVER_IP"
