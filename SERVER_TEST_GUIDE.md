# 🧪 服务器测试指南

## 📋 快速测试步骤

### 1. 连接到服务器

```bash
ssh root@154.17.3.182
# 或者使用密钥
ssh -i /Users/fanye/Documents/ssh_rsa_keys/private_key/id_rsa.pem root@154.17.3.182
```

### 2. 进入项目目录

```bash
cd ~/stock-analysis-bot
```

### 3. 检查环境配置

#### 3.1 检查 Python 环境
```bash
./venv/bin/python --version
# 应该显示: Python 3.11.x
```

#### 3.2 检查 .env 文件
```bash
cat .env
# 确认以下变量都已填写：
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHAT_ID
# - GDRIVE_CLIENT_ID
# - GDRIVE_CLIENT_SECRET
# - GDRIVE_REFRESH_TOKEN
# - GDRIVE_FOLDER_ID
```

如果 `.env` 文件中的 Google OAuth 信息为空，需要编辑：
```bash
nano .env
# 填入 GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN
# 按 Ctrl+O 保存，Ctrl+X 退出
```

### 4. 运行测试

#### 4.1 单只股票测试（推荐，快速）
```bash
./venv/bin/python github_stock_bot.py --mode manual --stocks '600460'
```

#### 4.2 多只股票测试
```bash
./venv/bin/python github_stock_bot.py --mode manual --stocks '600460,00700'
```

#### 4.3 使用配置文件中的股票列表
```bash
./venv/bin/python github_stock_bot.py --mode manual
```

### 5. 查看测试结果

#### 5.1 查看终端输出
测试运行时会显示：
- ✅ 数据获取进度
- 📊 报告生成状态
- 📤 Google Drive 上传结果
- 📦 ZIP 压缩包创建

#### 5.2 查看生成的报告
```bash
ls -lh reports/reports_*/
# 查看最新的报告目录
ls -lh reports/reports_*/ | tail -1
```

#### 5.3 查看日志（如果有错误）
```bash
# 查看最近的报告目录
cd reports/reports_*
ls -la *.pdf
```

### 6. 验证 Google Drive 上传

1. 打开你的 Google Drive
2. 进入配置的文件夹（ID: `1g_45mJ9b7UZ3UfC0SaAtjYEHOmYhm7pB`）
3. 检查是否有新上传的 PDF 文件

### 7. 验证 Telegram 通知

检查你的 Telegram 是否收到：
- 📊 分析开始通知
- 📄 报告生成完成通知（带 PDF 文件）

---

## 🔍 常见问题排查

### 问题 1: `ModuleNotFoundError`
**原因**: 依赖未安装完整  
**解决**:
```bash
cd ~/stock-analysis-bot
./venv/bin/python -m pip install -r requirements-core.txt -r requirements-optional.txt
```

### 问题 2: `缺少 Google Drive OAuth 配置`
**原因**: `.env` 文件中 OAuth 信息未填写  
**解决**: 编辑 `.env` 文件，填入 `GDRIVE_CLIENT_ID`, `GDRIVE_CLIENT_SECRET`, `GDRIVE_REFRESH_TOKEN`

### 问题 3: `无法访问 Google Drive 文件夹`
**原因**: 
- `GDRIVE_FOLDER_ID` 错误
- Refresh Token 过期或权限不足

**解决**:
1. 确认文件夹 ID 正确（从 Google Drive URL 中提取）
2. 如果 Refresh Token 过期，重新运行 `auth_tool.py` 获取新的 token

### 问题 4: 网络连接问题
**原因**: 服务器无法访问数据源  
**解决**:
```bash
# 测试网络连接
ping -c 3 sina.com.cn
ping -c 3 eastmoney.com
```

### 问题 5: 中文字体问题
**原因**: 字体未正确安装  
**解决**:
```bash
sudo apt-get install -y fonts-wqy-zenhei
fc-cache -fv
```

---

## 📝 测试检查清单

- [ ] SSH 连接成功
- [ ] Python 3.11 环境正常
- [ ] `.env` 文件配置完整
- [ ] 单只股票测试运行成功
- [ ] PDF 报告生成成功
- [ ] Google Drive 上传成功
- [ ] Telegram 通知收到
- [ ] 报告文件命名格式正确（`股票名称_股票代码_时间戳.pdf`）

---

## 🚀 测试完成后

如果所有测试都通过，可以设置定时任务：

```bash
crontab -e
```

添加以下行（每天 11:35 和 15:05 运行）：
```
35 11 * * 1-5 cd /root/stock-analysis-bot && ./venv/bin/python github_stock_bot.py --mode manual
5 15 * * 1-5 cd /root/stock-analysis-bot && ./venv/bin/python github_stock_bot.py --mode manual
```

保存并退出（`:wq` 在 vim 中，或 `Ctrl+O` + `Ctrl+X` 在 nano 中）
