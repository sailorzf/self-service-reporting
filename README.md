# 自助报表系统 (Self-Service Reporting System)

一个基于 Vue 3 + FastAPI 的自助报表系统，支持数据表管理、Excel 导入、可视化报表设计、AI 辅助查询和报表分享。

## 功能特性

- **数据表管理** — 注册数据库表映射，支持跨数据库查询（`database_name.table_name`）
- **Excel 数据导入** — 上传 Excel 文件，自动匹配列并导入到对应的数据表
- **可视化报表设计器** — 拖拽式画布，支持表格/柱状图/折线图/饼图/指标卡等组件，自由拖拽 + 松手吸附网格
- **AI 辅助查询** — 自然语言转 SQL，基于 DashScope（Qwen 模型）的对话式数据查询
- **报表分享** — 生成带过期时间的分享链接，他人可通过链接查看报表
- **报表导出** — 支持导出为 Excel 和 HTML 格式

## 技术栈

### 前端
| 技术 | 版本 |
|------|------|
| Vue 3 | ^3.4.0 |
| Element Plus | ^2.7.0 |
| ECharts | ^5.5.0 |
| interact.js | ^1.10.27 |
| Vue Router | ^4.3.0 |
| Vite | ^5.4.0 |

### 后端
| 技术 | 版本 |
|------|------|
| FastAPI | latest |
| SQLAlchemy | latest |
| PyMySQL | latest |
| Pandas / openpyxl | latest |
| OpenAI SDK (DashScope) | latest |
| uvicorn | latest |

### 数据库
- MySQL

## 目录结构

```
charging-self-report/
├── manage.ps1              # 服务管理脚本 (PowerShell)
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI 入口，路由注册
│   │   ├── config.py       # 配置管理 (环境变量)
│   │   ├── database.py     # 数据库连接
│   │   ├── models.py       # ORM 模型定义
│   │   ├── schemas.py      # Pydantic 请求/响应模型
│   │   ├── report_engine.py # 报表查询引擎
│   │   ├── export_html.py  # HTML 导出
│   │   └── api/
│   │       ├── data_types.py  # 数据表 CRUD
│   │       ├── imports.py     # Excel 导入
│   │       ├── reports.py     # 报表 CRUD/执行/导出
│   │       ├── ai.py          # AI 对话
│   │       └── share.py       # 报表分享
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── DataTableManage.vue  # 数据表管理
│   │   │   ├── ImportView.vue       # 数据导入列表
│   │   │   ├── ImportForm.vue       # 数据导入表单
│   │   │   ├── ImportDetailView.vue # 导入详情
│   │   │   ├── ReportListView.vue   # 报表列表
│   │   │   ├── ReportDesigner.vue   # 报表设计器 (画布)
│   │   │   └── ShareView.vue        # 分享页面
│   │   └── router/index.js  # 路由配置
│   └── package.json
└── .gitignore
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- MySQL 5.7+

### 1. 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```env
database_url=mysql+pymysql://user:password@localhost:3306/report_db
dashscope_api_key=your-dashscope-api-key
dashscope_base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
dashscope_model=qwen3.6-plus
max_joins=3
sql_timeout=5
max_result_rows=1000
```

### 2. 启动服务

```powershell
# 一键启动前后端
.\manage.ps1 start

# 或分别启动
.\manage.ps1 backend-start   # 后端 http://localhost:8100
.\manage.ps1 frontend-start  # 前端 http://localhost:3000

# 查看状态
.\manage.ps1 status

# 重启
.\manage.ps1 restart

# 停止
.\manage.ps1 stop
```

### 3. 手动启动

```bash
# 后端
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload

# 前端
cd frontend
npm install
npx vite --host 0.0.0.0 --port 3000
```

## API 端点

### 数据表 `/api/data-types`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/data-types/` | 获取所有数据表 |
| POST | `/api/data-types/` | 注册数据表 |
| PUT | `/api/data-types/{id}` | 更新数据表 |
| DELETE | `/api/data-types/{id}` | 删除数据表 |

### 数据导入 `/api/imports`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/imports/` | 获取导入记录 |
| POST | `/api/imports/` | 上传 Excel 导入 |
| GET | `/api/imports/{id}` | 获取导入详情 |

### 报表 `/api/reports`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/reports/` | 获取所有报表 |
| POST | `/api/reports/` | 创建报表 |
| PUT | `/api/reports/{id}` | 更新报表 |
| POST | `/api/reports/execute` | 执行查询（支持 raw_sql） |
| POST | `/api/reports/{id}/execute` | 执行指定报表 |
| POST | `/api/reports/{id}/share` | 生成分享链接 |
| GET | `/api/reports/{id}/export` | 导出为 Excel |
| GET | `/api/reports/{id}/export/html` | 导出为 HTML |

### AI `/api/ai`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/chat` | AI 对话（自然语言转 SQL） |

### 分享 `/api/share`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/share/{token}` | 通过分享 token 查看报表 |

### 健康检查
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 服务健康检查 |

## 前端路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | 重定向 | 默认跳转到 `/reports` |
| `/tables` | DataTableManage | 数据表管理 |
| `/import` | ImportView | 导入记录列表 |
| `/import/new` | ImportForm | 新建导入 |
| `/import/:id` | ImportDetailView | 导入详情 |
| `/reports` | ReportListView | 报表列表 |
| `/reports/new` | ReportDesigner | 新建报表 |
| `/reports/:id` | ReportDesigner | 编辑报表 |
| `/share/:token` | ShareView | 分享页面 |

## 数据库模型

### DataType (数据表)
注册物理数据库表的映射，支持 `database_name` 跨库查询。

### Report (报表)
存储报表配置（`config_json`），包含画布布局、组件配置和 SQL 查询。支持分享 token 和过期时间。

### ImportRecord (导入记录)
记录每次 Excel 导入的元数据：文件名、行数、批次 ID、状态。

### AISession / AIMessage (AI 对话)
存储 AI 对话会话和消息，包含自然语言、生成的 SQL 和结果预览。

## 报表设计器

报表设计器是基于 interact.js 的拖拽式画布，支持以下组件：

- **表格** — 数据表格展示
- **柱状图** — ECharts 柱状图
- **折线图** — ECharts 折线图
- **饼图** — ECharts 饼图
- **指标卡** — 单值指标展示

### 拖拽交互

- 按住组件标题栏自由拖拽，不限制移动范围
- 松手后自动吸附到 20px 网格
- 重叠检测：拖动中显示红色边框，松手时弹回原位置
- 四边 + 四角共 8 个拉伸手柄，支持全方向缩放
- 缩放时同样自由拖动，松手吸附网格
