# faninvest.com 域名配置指南（V2ray 服务器）

## ⚠️ 重要说明

你的服务器正在运行 V2ray 代理服务，配置新域名时需要特别注意：
- **443 端口**：V2ray (sing-box) 正在使用
- **10722 端口**：V2ray 备用端口
- **18403 端口**：Nginx 订阅服务

## 🎯 推荐方案：使用 Cloudflare 代理 + 非 443 端口

### 方案一：faninvest.com 使用 80 端口（推荐）

由于 443 端口被 V2ray 占用，我们可以：
1. faninvest.com 使用 80 端口（HTTP）
2. Cloudflare 自动提供 HTTPS（通过代理）
3. 不影响现有的 V2ray 服务

**优点：**
- ✅ 完全不影响 V2ray
- ✅ Cloudflare 免费 SSL
- ✅ 配置简单

### 方案二：Nginx SNI 分流（高级）

如果必须使用 443 端口，可以配置 Nginx 作为反向代理，根据域名分流：
- `frank.ooxxeee.cf` / `frank.ooxxeee.eu.org` → 转发到 V2ray
- `faninvest.com` → Web 服务

**注意：** 这需要修改 V2ray 配置，可能影响现有连接。

## 📋 配置步骤（方案一：推荐）

### 第一步：在 Cloudflare 配置 DNS

1. 访问：https://dash.cloudflare.com/efff6e6fc4e89f69cbe5770cdcde335c/faninvest.com
2. 点击 **DNS** → **记录**
3. 添加 A 记录：

| 类型 | 名称 | 内容 | 代理状态 | TTL |
|------|------|------|----------|-----|
| A | @ | 154.17.3.182 | 🟠 已代理（橙色云朵） | 自动 |
| A | www | 154.17.3.182 | 🟠 已代理（橙色云朵） | 自动 |

**重要：** 必须开启代理（橙色云朵），这样 Cloudflare 会处理 HTTPS。

### 第二步：配置 Cloudflare SSL

1. **SSL/TLS** → 加密模式：**完全（严格）**
2. **SSL/TLS** → **边缘证书** → 开启 **始终使用 HTTPS**
3. **SSL/TLS** → **源服务器** → 可以暂时不配置（因为使用 HTTP）

### 第三步：在服务器上配置 Nginx

运行部署脚本：

```bash
cd /Users/fanye/Documents/stock-analysis-bot
./deploy_v2ray_domain.sh
```

或者手动配置（见下方）。

## 🔧 Nginx 配置文件

### 基础配置（HTTP，Cloudflare 处理 HTTPS）

```nginx
# /etc/nginx/conf.d/faninvest.com.conf

server {
    listen 80;
    listen [::]:80;
    server_name faninvest.com www.faninvest.com;

    # 允许 Cloudflare IP 范围（可选，提高安全性）
    # 可以从 https://www.cloudflare.com/ips/ 获取最新 IP 列表
    # allow 173.245.48.0/20;
    # deny all;

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

### Python Web 应用配置

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name faninvest.com www.faninvest.com;

    access_log /var/log/nginx/faninvest.com.access.log;
    error_log /var/log/nginx/faninvest.com.error.log;

    # 反向代理到 Python 应用
    location / {
        proxy_pass http://127.0.0.1:5000;  # 修改为你的应用端口
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cloudflare 真实 IP
        set_real_ip_from 173.245.48.0/20;
        set_real_ip_from 103.21.244.0/22;
        set_real_ip_from 103.22.200.0/22;
        set_real_ip_from 103.31.4.0/22;
        set_real_ip_from 141.101.64.0/18;
        set_real_ip_from 108.162.192.0/18;
        set_real_ip_from 190.93.240.0/20;
        set_real_ip_from 188.114.96.0/20;
        set_real_ip_from 197.234.240.0/22;
        set_real_ip_from 198.41.128.0/17;
        set_real_ip_from 162.158.0.0/15;
        set_real_ip_from 104.16.0.0/13;
        set_real_ip_from 104.24.0.0/14;
        set_real_ip_from 172.64.0.0/13;
        set_real_ip_from 131.0.72.0/22;
        real_ip_header CF-Connecting-IP;
    }
}
```

## 🚀 快速部署

我已经创建了专门的部署脚本，运行：

```bash
./deploy_v2ray_domain.sh
```

## ✅ 验证配置

1. **检查 Nginx 配置**：
   ```bash
   ssh -i ~/ssh_rsa_keys/private_key/id_rsa.pem root@154.17.3.182 "nginx -t"
   ```

2. **重新加载 Nginx**：
   ```bash
   ssh -i ~/ssh_rsa_keys/private_key/id_rsa.pem root@154.17.3.182 "systemctl reload nginx"
   ```

3. **测试访问**：
   - 等待 DNS 传播（几分钟）
   - 访问 https://faninvest.com（Cloudflare 会自动提供 HTTPS）

## 🔒 安全建议

1. **限制访问来源**（可选）：
   如果只想通过 Cloudflare 访问，可以限制只允许 Cloudflare IP：
   ```nginx
   # 在 server 块中添加
   include /etc/nginx/cloudflare-ips.conf;
   allow 173.245.48.0/20;
   # ... 其他 Cloudflare IP 段
   deny all;
   ```

2. **防火墙规则**：
   确保 80 端口开放：
   ```bash
   ufw allow 80/tcp
   ```

## ❓ 常见问题

**Q: 会影响我的 V2ray 服务吗？**
A: 不会。新域名使用 80 端口，V2ray 继续使用 443 端口。

**Q: 可以使用 HTTPS 吗？**
A: 可以。Cloudflare 会自动提供 HTTPS（通过代理），无需在服务器上配置 SSL 证书。

**Q: 如果我想用 443 端口怎么办？**
A: 需要配置 Nginx SNI 分流，这会比较复杂，建议使用方案一。
