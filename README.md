# 🤖 多用户隔离 AI 知识库助手

一个基于 FastAPI + Vue3 + FastGPT 的 MVP 原型系统，支持多用户隔离、专属知识库和智能对话功能。

## ✨ 核心特性

- **👥 多用户隔离**：每个注册用户拥有独立的 FastGPT 知识库
- **📁 文件上传**：支持 PDF、DOCX、TXT、MD 格式文档
- **💬 智能对话**：基于用户知识库的流式对话响应
- **🔐 安全认证**：HTTP Basic Auth + 密码加密存储
- **🚀 快速部署**：单文件后端 + 单文件前端

## 🏗️ 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端 | Python 3.10+ / FastAPI / SQLite |
| 前端 | Vue 3 (CDN) / TailwindCSS / Marked.js |
| AI 集成 | FastGPT API |
| 部署 | Uvicorn (ASGI Server) |

## 📁 项目结构

```
/home/engine/project
├── main.py              # FastAPI 后端服务
├── index.html           # Vue3 前端单页应用
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量示例
├── .gitignore          # Git 忽略配置
└── knowledge_base.db   # SQLite 数据库（启动后自动生成）
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆或进入项目目录
cd /home/engine/project

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 Windows: .\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
nano .env
```

**配置项说明：**

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `FASTGPT_ADMIN_KEY` | 管理员 Key（创建知识库、上传文件） | `fastgpt-gcFmV...` |
| `FASTGPT_CHAT_APP_KEY` | 聊天 App Key（对话功能） | `fastgpt-m06FYV...` |
| `FASTGPT_BASE_URL` | FastGPT 服务地址 | `https://fastgpt.aiown.top` |

### 3. 启动服务

```bash
# 开发模式启动（热重载）
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问应用

打开浏览器访问：**http://localhost:8000**

## 📡 API 接口文档

启动服务后访问：**http://localhost:8000/docs**

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 (HTTP Basic) |
| GET | `/api/user/info` | 获取当前用户信息 |

### 功能接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/upload` | 文件上传 | ✅ |
| POST | `/api/chat` | 流式对话 | ✅ |

### 请求示例

#### 用户注册

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "123456"}'
```

#### 用户登录

```bash
curl -u "testuser:123456" http://localhost:8000/api/auth/login
```

#### 文件上传

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -u "testuser:123456" \
  -F "file=@document.pdf"
```

#### 流式对话

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -u "testuser:123456" \
  -H "Content-Type: application/json" \
  -d '{"message": "请介绍一下文档内容"}' \
  --stream
```

## 🔧 部署指南

### 生产环境部署

#### 1. 使用 Gunicorn

```bash
# 安装 gunicorn
pip install gunicorn

# 启动服务（4个工作进程）
gunicorn main:app -w 4 -b 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker
```

#### 2. 使用 Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /home/engine/project

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 构建和运行
docker build -t fastgpt-kb-assistant .
docker run -p 8000:8000 -e FASTGPT_ADMIN_KEY="your-key" -e FASTGPT_CHAT_APP_KEY="your-key" fastgpt-kb-assistant
```

#### 3. 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 安全加固建议

1. **修改默认密钥**
   ```bash
   # 生成强随机密钥
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **限制 CORS**
   ```python
   # 在 main.py 中修改
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-domain.com"],  # 限制为你的域名
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **使用更强的密码哈希**
   ```python
   # 推荐使用 bcrypt
   pip install bcrypt
   import bcrypt
   password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
   ```

4. **启用 HTTPS**

## 🛠️ 维护指南

### 数据库管理

```bash
# 查看数据库文件
ls -la knowledge_base.db

# 备份数据库
cp knowledge_base.db backup_$(date +%Y%m%d).db

# 查看用户数量
sqlite3 knowledge_base.db "SELECT COUNT(*) FROM users;"

# 查看所有用户
sqlite3 knowledge_base.db "SELECT id, username, created_at FROM users;"
```

### 日志查看

```bash
# 实时查看日志
tail -f app.log

# 查看错误日志
grep "ERROR" app.log
```

### 监控检查

```bash
# 检查服务状态
curl http://localhost:8000/

# 检查 API 健康
curl http://localhost:8000/docs
```

### 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 注册失败 | FastGPT API Key 无效 | 检查 `.env` 配置 |
| 上传失败 | 文件类型不支持 | 确认文件格式为 PDF/DOCX/TXT/MD |
| 对话无响应 | 知识库为空 | 先上传文档到知识库 |
| 登录失败 | 密码错误或用户不存在 | 检查凭据或重新注册 |
| 流式响应中断 | 网络超时 | 检查网络连接 |

### 更新升级

```bash
# 1. 备份数据
cp knowledge_base.db backup.db

# 2. 更新代码
git pull origin main

# 3. 更新依赖
pip install -r requirements.txt

# 4. 重启服务
pkill -f uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 &
```

## 📊 FastGPT API 参考

### 创建知识库

```bash
curl -X POST "https://fastgpt.aiown.top/api/core/dataset/create" \
  -H "Authorization: Bearer {ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"name": "username_KB", "type": "dataset", "parentId": null}'
```

### 上传文件

```bash
curl -X POST "https://fastgpt.aiown.top/api/core/dataset/collection/create/localFile" \
  -H "Authorization: Bearer {ADMIN_KEY}" \
  -F "file=@document.pdf" \
  -F 'data={"datasetId": "xxx", "trainingType": "chunk", "chunkSize": 512}'
```

### 流式对话

```bash
curl -X POST "https://fastgpt.aiown.top/api/v1/chat/completions" \
  -H "Authorization: Bearer {CHAT_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "chatId": "session_id",
    "stream": true,
    "variables": {
      "fastdataUid": "dataset_id"
    },
    "messages": [{"role": "user", "content": "hello"}]
  }'
```

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2024-12-27 | 初始版本发布 |

## ⚠️ 注意事项

1. **MVP 级别**：本项目为 MVP 原型，生产环境使用需加强安全措施
2. **API 限制**：请确保 FastGPT 账户有足够的 API 调用配额
3. **数据备份**：定期备份 `knowledge_base.db` 数据库文件
4. **密码安全**：当前使用简单 SHA256 哈希，生产环境建议使用 bcrypt

## 📄 许可证

本项目仅供学习和研究使用。

---

**Made with ❤️**
