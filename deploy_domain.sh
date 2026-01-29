#!/bin/bash

# faninvest.com 域名部署脚本
# 自动配置 Nginx 和创建必要的目录

SERVER_IP="154.17.3.182"
PRIVATE_KEY="/Users/fanye/Documents/ssh_rsa_keys/private_key/id_rsa.pem"
DOMAIN="faninvest.com"

echo "=========================================="
echo "faninvest.com 域名部署脚本"
echo "=========================================="
echo ""

# 检查参数
read -p "请选择配置类型：
1) 静态网站
2) Python Web 应用（Flask/FastAPI）
3) API 服务
请输入数字 (1-3): " config_type

case $config_type in
    1)
        CONFIG_TYPE="static"
        echo "✓ 已选择：静态网站配置"
        ;;
    2)
        CONFIG_TYPE="python"
        echo "✓ 已选择：Python Web 应用配置"
        ;;
    3)
        CONFIG_TYPE="api"
        echo "✓ 已选择：API 服务配置"
        ;;
    *)
        echo "❌ 无效选择，退出"
        exit 1
        ;;
esac

echo ""
echo "正在连接到服务器 $SERVER_IP..."
echo ""

# 创建临时配置文件
TEMP_CONFIG=$(mktemp)

if [ "$CONFIG_TYPE" == "static" ]; then
    cat > "$TEMP_CONFIG" << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name faninvest.com www.faninvest.com;

    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name faninvest.com www.faninvest.com;

    root /var/www/faninvest.com;
    index index.html index.htm;

    access_log /var/log/nginx/faninvest.com.access.log;
    error_log /var/log/nginx/faninvest.com.error.log;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

elif [ "$CONFIG_TYPE" == "python" ]; then
    read -p "请输入 Python 应用端口 (默认: 5000): " app_port
    app_port=${app_port:-5000}
    
    cat > "$TEMP_CONFIG" << EOF
server {
    listen 80;
    listen [::]:80;
    server_name faninvest.com www.faninvest.com;

    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name faninvest.com www.faninvest.com;

    access_log /var/log/nginx/faninvest.com.access.log;
    error_log /var/log/nginx/faninvest.com.error.log;

    location / {
        proxy_pass http://127.0.0.1:$app_port;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static {
        alias /var/www/faninvest.com/static;
        expires 30d;
    }
}
EOF

elif [ "$CONFIG_TYPE" == "api" ]; then
    read -p "请输入 API 服务端口 (默认: 8000): " api_port
    api_port=${api_port:-8000}
    
    cat > "$TEMP_CONFIG" << EOF
server {
    listen 80;
    listen [::]:80;
    server_name faninvest.com www.faninvest.com;

    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name faninvest.com www.faninvest.com;

    access_log /var/log/nginx/faninvest.com.access.log;
    error_log /var/log/nginx/faninvest.com.error.log;

    location / {
        proxy_pass http://127.0.0.1:$api_port;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Authorization, Content-Type";
    }
}
EOF
fi

# 上传配置文件到服务器
echo ""
echo "正在上传 Nginx 配置..."
scp -i "$PRIVATE_KEY" -o StrictHostKeyChecking=no "$TEMP_CONFIG" root@"$SERVER_IP":/etc/nginx/conf.d/faninvest.com.conf

# 在服务器上执行配置
echo ""
echo "正在配置服务器..."
ssh -i "$PRIVATE_KEY" -o StrictHostKeyChecking=no root@"$SERVER_IP" << 'ENDSSH'
    # 创建网站目录（如果是静态网站）
    if [ -f /etc/nginx/conf.d/faninvest.com.conf ] && grep -q "root /var/www/faninvest.com" /etc/nginx/conf.d/faninvest.com.conf; then
        mkdir -p /var/www/faninvest.com
        chown -R www-data:www-data /var/www/faninvest.com
        
        # 创建默认首页
        if [ ! -f /var/www/faninvest.com/index.html ]; then
            cat > /var/www/faninvest.com/index.html << 'EOFHTML'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>faninvest.com</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        h1 { font-size: 3rem; margin: 0; }
        p { font-size: 1.2rem; opacity: 0.9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 faninvest.com</h1>
        <p>网站配置成功！</p>
        <p style="font-size: 0.9rem; opacity: 0.7;">Nginx 已成功配置</p>
    </div>
</body>
</html>
EOFHTML
            chown www-data:www-data /var/www/faninvest.com/index.html
        fi
    fi
    
    # 测试 Nginx 配置
    echo "测试 Nginx 配置..."
    if nginx -t; then
        echo "✓ Nginx 配置测试通过"
        systemctl reload nginx
        echo "✓ Nginx 已重新加载"
    else
        echo "❌ Nginx 配置有错误，请检查"
        exit 1
    fi
ENDSSH

# 清理临时文件
rm "$TEMP_CONFIG"

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "📋 下一步操作："
echo ""
echo "1. 在 Cloudflare 配置 DNS 记录："
echo "   - 类型: A"
echo "   - 名称: @ 和 www"
echo "   - 内容: 154.17.3.182"
echo "   - 代理状态: 🟠 已代理（橙色云朵）"
echo ""
echo "2. 在 Cloudflare 启用 SSL/TLS："
echo "   - 加密模式: 完全（严格）"
echo "   - 始终使用 HTTPS: 开启"
echo ""
echo "3. 等待 DNS 传播（通常几分钟）"
echo ""
echo "4. 访问测试："
echo "   https://faninvest.com"
echo ""
echo "💡 提示：如果使用静态网站配置，网站文件位于："
echo "   /var/www/faninvest.com"
echo ""
