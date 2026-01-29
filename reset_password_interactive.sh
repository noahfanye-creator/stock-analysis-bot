#!/bin/bash

# 交互式密码重置脚本
# 使用方法: ./reset_password_interactive.sh

SERVER_IP="154.17.3.182"
PRIVATE_KEY="/Users/fanye/Documents/ssh_rsa_keys/private_key/id_rsa.pem"

echo "=========================================="
echo "服务器密码重置工具"
echo "=========================================="
echo ""
echo "服务器: $SERVER_IP"
echo ""

# 提示用户输入新密码
read -sp "请输入新密码: " NEW_PASSWORD
echo ""
read -sp "请再次输入新密码确认: " NEW_PASSWORD_CONFIRM
echo ""

if [ "$NEW_PASSWORD" != "$NEW_PASSWORD_CONFIRM" ]; then
    echo "❌ 两次输入的密码不一致，请重新运行脚本"
    exit 1
fi

if [ -z "$NEW_PASSWORD" ]; then
    echo "❌ 密码不能为空"
    exit 1
fi

echo ""
echo "正在连接到服务器并重置密码..."

# 使用 expect 或直接通过 SSH 执行
ssh -i "$PRIVATE_KEY" -o StrictHostKeyChecking=no root@"$SERVER_IP" << EOF
echo -e "$NEW_PASSWORD\n$NEW_PASSWORD" | passwd root
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 密码重置成功！"
    echo ""
    echo "现在你可以使用以下方式登录："
    echo "1. 使用密码: ssh root@$SERVER_IP"
    echo "2. 使用密钥: ssh -i $PRIVATE_KEY root@$SERVER_IP"
else
    echo ""
    echo "❌ 密码重置失败，请检查错误信息"
    exit 1
fi
