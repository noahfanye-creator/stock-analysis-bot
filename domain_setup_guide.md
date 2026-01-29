# faninvest.com 域名配置指南

## 📋 配置步骤

### 第一步：在 Cloudflare 配置 DNS 记录

1. 访问：https://dash.cloudflare.com/efff6e6fc4e89f69cbe5770cdcde335c/faninvest.com
2. 点击左侧菜单 **"DNS"** → **"记录"**
3. 添加以下 DNS 记录：

| 类型 | 名称 | 内容 | 代理状态 | TTL |
|------|------|------|----------|-----|
| A | @ | 154.17.3.182 | 🟠 已代理（橙色云朵） | 自动 |
| A | www | 154.17.3.182 | 🟠 已代理（橙色云朵） | 自动 |

**重要说明：**
- **@** 表示根域名 `faninvest.com`
- **www** 表示 `www.faninvest.com`
- 确保代理状态是 **橙色云朵**（已代理），这样 Cloudflare 会提供免费 SSL 和 CDN 加速

### 第二步：配置 Cloudflare SSL/TLS

1. 在 Cloudflare 控制台，点击左侧 **"SSL/TLS"**
2. 将加密模式设置为：**"完全（严格）"** 或 **"完全"**
3. 在 **"边缘证书"** 部分，确保 **"始终使用 HTTPS"** 已开启

### 第三步：在服务器上配置 Nginx

我已经为你创建了 Nginx 配置文件，执行以下命令部署：

```bash
# 连接到服务器
ssh -i /Users/fanye/Documents/ssh_rsa_keys/private_key/id_rsa.pem root@154.17.3.182

# 创建 Nginx 配置
nano /etc/nginx/conf.d/faninvest.com.conf
```

然后粘贴以下配置内容（见下方配置文件）。

### 第四步：测试并重启 Nginx

```bash
# 测试配置是否正确
nginx -t

# 如果测试通过，重新加载 Nginx
systemctl reload nginx
```

## 🔧 Nginx 配置文件

根据你的需求选择以下配置之一：

### 选项 1：静态网站配置

如果你要部署静态网站（HTML/CSS/JS）：

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name faninvest.com www.faninvest.com;

    # 重定向到 HTTPS（Cloudflare 会自动处理）
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name faninvest.com www.faninvest.com;

    # SSL 证书（Cloudflare 自动提供，或使用 Let's Encrypt）
    # 如果使用 Cloudflare 代理，可以暂时不配置 SSL 证书
    # ssl_certificate /etc/letsencrypt/live/faninvest.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/faninvest.com/privkey.pem;

    # 网站根目录
    root /var/www/faninvest.com;
    index index.html index.htm;

    # 日志
    access_log /var/log/nginx/faninvest.com.access.log;
    error_log /var/log/nginx/faninvest.com.error.log;

    location / {
        try_files $uri $uri/ =404;
    }

    # 静态文件缓存
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 选项 2：Python Web 应用（Flask/FastAPI）

如果你要部署股票分析系统的 Web 服务：

```nginx
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

    # 日志
    access_log /var/log/nginx/faninvest.com.access.log;
    error_log /var/log/nginx/faninvest.com.error.log;

    # 反向代理到 Python 应用（假设运行在 5000 端口）
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件直接服务
    location /static {
        alias /var/www/faninvest.com/static;
        expires 30d;
    }
}
```

### 选项 3：API 服务配置

如果你要部署 API 服务：

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name api.faninvest.com;

    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.faninvest.com;

    # 日志
    access_log /var/log/nginx/api.faninvest.com.access.log;
    error_log /var/log/nginx/api.faninvest.com.error.log;

    # API 反向代理
    location / {
        proxy_pass http://127.0.0.1:8000;  # 修改为你的 API 端口
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS 头（如果需要）
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Authorization, Content-Type";
    }
}
```

## 🚀 快速部署脚本

我已经创建了自动化部署脚本，你可以直接运行：

```bash
cd /Users/fanye/Documents/stock-analysis-bot
./deploy_domain.sh
```

## 📝 后续步骤

1. **创建网站目录**（如果使用静态网站）：
   ```bash
   mkdir -p /var/www/faninvest.com
   chown -R www-data:www-data /var/www/faninvest.com
   ```

2. **配置 SSL 证书**（可选，如果不用 Cloudflare 代理）：
   ```bash
   apt install certbot python3-certbot-nginx
   certbot --nginx -d faninvest.com -d www.faninvest.com
   ```

3. **测试访问**：
   - 等待 DNS 传播（通常几分钟到几小时）
   - 访问 https://faninvest.com 测试

## ❓ 需要帮助？

告诉我你想用这个域名做什么：
- 部署静态网站？
- 部署股票分析系统的 Web 界面？
- 部署 API 服务？
- 其他用途？

我可以根据你的需求定制配置！
