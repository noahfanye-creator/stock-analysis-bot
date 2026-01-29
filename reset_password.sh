#!/bin/bash

# SSH 密码重置脚本
# 使用方法: ./reset_password.sh <新密码>

SERVER_IP="154.17.3.182"
PRIVATE_KEY="/Users/fanye/Documents/ssh_rsa_keys/private_key/id_rsa.pem"

if [ -z "$1" ]; then
    echo "使用方法: $0 <新密码>"
    exit 1
fi

NEW_PASSWORD="$1"

echo "正在连接到服务器 $SERVER_IP..."
echo "正在重置 root 密码..."

# 使用 expect 或直接通过 SSH 执行 passwd 命令
ssh -i "$PRIVATE_KEY" -o StrictHostKeyChecking=no root@"$SERVER_IP" << EOF
echo -e "$NEW_PASSWORD\n$NEW_PASSWORD" | passwd root
EOF

if [ $? -eq 0 ]; then
    echo "密码重置成功！"
    echo "你现在可以使用以下命令登录："
    echo "ssh -i $PRIVATE_KEY root@$SERVER_IP"
    echo ""
    echo "然后输入新密码：$NEW_PASSWORD"
else
    echo "密码重置失败，请检查错误信息"
fi
