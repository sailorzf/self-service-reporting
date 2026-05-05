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

## 7. Linux 服务器部署

### 7.1 环境准备

**Ubuntu / Debian：**

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip mysql-server nginx nodejs npm
```

**CentOS / RHEL：**

```bash
sudo yum install -y python39 python39-devel mysql-server nginx
# Node.js 18+
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
```

### 7.2 部署项目

```bash
# 克隆项目
git clone git@github.com:sailorzf/self-service-reporting.git
cd self-service-reporting

# 或在服务器上直接上传代码后
cd /opt/self-service-reporting
```

### 7.3 后端部署

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 创建 .env 配置文件
cat > .env << 'EOF'
database_url=mysql+pymysql://report_user:your_password@localhost:3306/report_db
dashscope_api_key=your-dashscope-api-key
dashscope_base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
dashscope_model=qwen3.6-plus
max_joins=3
sql_timeout=5
max_result_rows=1000
EOF
```

**配置 systemd 服务：**

```bash
sudo tee /etc/systemd/system/report-backend.service > /dev/null << 'EOF'
[Unit]
Description=Self-Service Report Backend
After=network.target mysql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/self-service-reporting/backend
Environment=PATH=/opt/self-service-reporting/backend/.venv/bin
ExecStart=/opt/self-service-reporting/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8100 --workers 4
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable report-backend
sudo systemctl start report-backend
```

### 7.4 前端构建

```bash
cd frontend

# 安装依赖
npm install

# 生产构建
npm run build
```

构建产物输出到 `frontend/dist/`。

### 7.5 Nginx 配置

```bash
sudo tee /etc/nginx/sites-available/report > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /opt/self-service-reporting/frontend/dist;
    index index.html;

    # SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2)$ {
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }

    # 反向代理到后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持（如需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/report /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 7.6 HTTPS（Let's Encrypt）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 7.7 Linux 服务管理脚本

在 `manage.sh` 中提供与 `manage.ps1` 等效的 Linux 管理功能：

```bash
cat > manage.sh << 'SCRIPT'
#!/usr/bin/env bash
set -e

BACKEND_PORT=8100
FRONTEND_PORT=3000
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

kill_port() {
    local pid=$(lsof -ti:$1 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "  Killing PID $pid on port $1"
        kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

start_backend() {
    echo "=== Starting backend (port $BACKEND_PORT) ==="
    cd "$BACKEND_DIR"
    source .venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > /tmp/report-backend.log 2>&1 &
    local pid=$!
    echo "  Backend PID: $pid"
    echo -n "  Waiting for backend..."
    for i in $(seq 1 40); do
        if curl -s http://127.0.0.1:$BACKEND_PORT/api/health | grep -q ok; then
            echo " OK"; return 0
        fi
        sleep 1
        echo -n "."
    done
    echo " TIMEOUT"; return 1
}

start_frontend() {
    echo "=== Starting frontend (port $FRONTEND_PORT) ==="
    cd "$FRONTEND_DIR"
    nohup npx vite --host 0.0.0.0 --port $FRONTEND_PORT > /tmp/report-frontend.log 2>&1 &
    local pid=$!
    echo "  Frontend PID: $pid"
    echo -n "  Waiting for frontend..."
    for i in $(seq 1 40); do
        if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
            echo " OK"; return 0
        fi
        sleep 1
        echo -n "."
    done
    echo " TIMEOUT"; return 1
}

stop_services() {
    echo "=== Stopping services ==="
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    echo "All services stopped."
}

case "${1:-help}" in
    start)          start_backend && start_frontend ;;
    stop)           stop_services ;;
    restart)        stop_services; sleep 2; start_backend && start_frontend ;;
    status)         lsof -i:$BACKEND_PORT 2>/dev/null && echo "  Backend: Running" || echo "  Backend: Stopped"
                    lsof -i:$FRONTEND_PORT 2>/dev/null && echo "  Frontend: Running" || echo "  Frontend: Stopped" ;;
    backend-start)  start_backend ;;
    frontend-start) start_frontend ;;
    *)              echo "Usage: ./manage.sh {start|stop|restart|status|backend-start|frontend-start}" ;;
esac
SCRIPT

chmod +x manage.sh
```

使用方式：

```bash
./manage.sh start           # 启动前后端
./manage.sh stop            # 停止前后端
./manage.sh restart         # 重启前后端
./manage.sh status          # 查看状态
```

### 7.8 日志查看

```bash
# 后端日志
tail -f /tmp/report-backend.log
# 或使用 journalctl（如果使用 systemd）
sudo journalctl -u report-backend -f

# 前端日志
tail -f /tmp/report-frontend.log

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 7.9 数据库备份

```bash
# 手动备份
mysqldump -u root -p report_db > /backup/report_db_$(date +%Y%m%d_%H%M%S).sql

# 定时备份（crontab）
echo "0 2 * * * mysqldump -u root -pyour_password report_db | gzip > /backup/report_db_\$(date +\%Y\%m\%d).sql.gz" | crontab -
```

## 8. 故障排查

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

**Windows（PowerShell）：**

```powershell
# 查看占用端口的进程
netstat -ano | findstr :8100   # 后端
netstat -ano | findstr :3000   # 前端

# 终止对应进程
taskkill /F /PID <PID>
```

**Linux：**

```bash
# 查看占用端口的进程
sudo lsof -i:8100    # 后端
sudo lsof -i:3000    # 前端

# 终止对应进程
sudo kill -9 <PID>
```
