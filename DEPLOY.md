# 部署指南 (Deployment Guide)

## 环境要求

- Python 3.12+
- Node.js 18+
- MySQL 5.7+
- Windows PowerShell (用于 manage.ps1 脚本) 或手动启动

## 1. 数据库准备

### 1.1 创建数据库

```sql
CREATE DATABASE report_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 1.2 创建数据库用户

```sql
CREATE USER 'report_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON report_db.* TO 'report_user'@'localhost';
-- 如果需要跨库查询，授予对应数据库的 SELECT 权限
GRANT SELECT ON other_db.* TO 'report_user'@'localhost';
FLUSH PRIVILEGES;
```

### 1.3 自动建表

启动后端时，SQLAlchemy 会根据 `backend/app/models.py` 中的模型定义自动创建以下表：

| 表名 | 说明 |
|------|------|
| `data_types` | 数据表注册信息 |
| `reports` | 报表配置 |
| `import_records` | Excel 导入记录 |
| `ai_sessions` | AI 对话会话 |
| `ai_messages` | AI 对话消息 |

## 2. 后端部署

### 2.1 安装依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2.2 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```env
database_url=mysql+pymysql://report_user:your_password@localhost:3306/report_db
dashscope_api_key=your-dashscope-api-key
dashscope_base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
dashscope_model=qwen3.6-plus
max_joins=3
sql_timeout=5
max_result_rows=1000
```

| 变量 | 说明 |
|------|------|
| `database_url` | MySQL 连接字符串，格式 `mysql+pymysql://user:pass@host:port/dbname` |
| `dashscope_api_key` | 阿里云 DashScope API 密钥（用于 AI 查询） |
| `dashscope_base_url` | DashScope API 地址 |
| `dashscope_model` | AI 模型名称 |
| `max_joins` | 最大 JOIN 数量限制 |
| `sql_timeout` | SQL 查询超时时间（秒） |
| `max_result_rows` | 查询结果最大行数 |

### 2.3 启动后端

```powershell
# 使用管理脚本（推荐）
.\manage.ps1 backend-start

# 或直接启动
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

后端默认运行在 `http://localhost:8100`。

### 2.4 API 文档

启动后可访问 `http://localhost:8100/docs` 查看 Swagger 自动生成的 API 文档。

## 3. 前端部署

### 3.1 安装依赖

```bash
cd frontend
npm install
```

### 3.2 开发模式

```powershell
# 使用管理脚本（推荐）
.\manage.ps1 frontend-start

# 或直接启动
cd frontend
npx vite --host 0.0.0.0 --port 3000
```

前端默认运行在 `http://localhost:3000`，开发模式下会自动代理 API 请求到后端。

### 3.3 生产构建

```bash
cd frontend
npm run build
```

构建产物输出到 `frontend/dist/` 目录。

### 3.4 生产部署

将 `frontend/dist/` 部署到任意静态文件服务器（Nginx、Caddy、Apache 等），并配置将 `/api/*` 请求反向代理到后端：

**Nginx 示例：**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/frontend/dist;
    index index.html;

    # 前端 SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 反向代理到后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 4. 服务管理

项目提供了 `manage.ps1` PowerShell 脚本统一管理前后端服务：

```powershell
.\manage.ps1 start            # 启动前后端
.\manage.ps1 stop             # 停止前后端
.\manage.ps1 restart          # 重启前后端
.\manage.ps1 status           # 查看运行状态
.\manage.ps1 backend-start    # 仅启动后端 (port 8100)
.\manage.ps1 backend-stop     # 仅停止后端
.\manage.ps1 frontend-start   # 仅启动前端 (port 3000)
.\manage.ps1 frontend-stop    # 仅停止前端
```

脚本会自动清理残留进程，确保端口不被占用。

## 5. 生产环境建议

### 5.1 后端

- 使用 `gunicorn` 或 `uvicorn --workers N` 启动多进程
- 关闭 `--reload` 热重载
- 使用环境变量或密钥管理服务管理 `.env` 文件
- 配置 SQL 查询超时和行数限制，防止慢查询

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8100
```

### 5.2 前端

- 使用 `npm run build` 构建生产版本
- 通过 CDN 或 Nginx 提供静态文件服务
- 启用 gzip/brotli 压缩
- 配置 HTTPS

### 5.3 数据库

- 定期备份 `report_db` 数据库
- 对 `ai_sessions` 和 `ai_messages` 表做定期清理，避免无限增长
- 为 `data_types.code`、`reports.shared_token` 等字段确保索引

## 6. 故障排查

### 后端无法连接数据库

- 检查 `.env` 中 `database_url` 的连接信息是否正确
- 确认 MySQL 服务正在运行
- 确认数据库用户有对应数据库的权限

### 前端无法访问后端 API

- 确认后端运行在 `http://localhost:8100`
- 检查 CORS 配置（`backend/app/main.py` 中的 `allow_origins`）
- 检查浏览器开发者工具 Network 面板的报错信息

### AI 查询不工作

- 检查 `.env` 中 `dashscope_api_key` 是否正确配置
- 检查网络是否能访问 `dashscope.aliyuncs.com`
- 查看后端日志中的具体错误信息

### 端口被占用

`manage.ps1` 脚本会自动清理占用端口的进程。如果手动启动时遇到端口占用：

```powershell
# 查看占用端口的进程
netstat -ano | findstr :8100   # 后端
netstat -ano | findstr :3000   # 前端

# 终止对应进程
taskkill /F /PID <PID>
```
