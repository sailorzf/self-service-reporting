# 自助报表系统设计文档

> 2026-04-29 | 版本: v1.0

## 1. 目标与背景

当前报表依赖人工分析Excel：业务和管理层提需求，运营人员手工制作，费时费力。
本系统通过 **Excel导入 + 拖拽式报表设计 + AI对话式分析**，让用户自助完成报表制作。

### 核心用户
- **业务人员**：查看报表、AI自然语言查询
- **管理层**：查看报表、AI分析趋势
- **运营人员**：数据导入、报表设计、类型管理

### 技术约束
- 数据量：当前几百行，后续几万行
- 查询响应：秒级
- 并发用户：不超过5人
- 权限：初始统一视图，后续按需扩展

---

## 2. 系统架构

```
┌──────────────────────────────────────────────────────┐
│                     浏览器端                          │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Excel导入 │  │ 拖拽报表 │  │ AI对话式分析(嵌入) │  │
│  │  & 管理   │  │  设计器  │  │ (NL → SQL)         │  │
│  └──────────┘  └──────────┘  └────────────────────┘  │
│                                                       │
│  ┌──────────────────────────────────────────────┐     │
│  │        Vue3 + Element Plus + ECharts         │     │
│  └──────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
                        ↕  REST API
┌──────────────────────────────────────────────────────┐
│                     后端层                            │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ 文件导入 │  │ 报表引擎 │  │ AI查询引擎         │  │
│  │ & 解析   │  │ (JSON→SQL│  │ (多轮对话,NL转SQL) │  │
│  └──────────┘  │  执行)   │  └────────────────────┘  │
│                └──────────┘                           │
│  ┌──────────────────────────────────────────────┐     │
│  │         Python FastAPI + SQLAlchemy          │     │
│  └──────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
                        ↕
┌──────────────────────────────────────────────────────┐
│                  MySQL 8.x                           │
└──────────────────────────────────────────────────────┘
```

### 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 组合式API |
| UI组件 | Element Plus | 表格、表单、上传、对话框 |
| 图表 | ECharts | 柱状图/折线图/饼图等 |
| 拖拽 | vue-draggable-plus | 字段拖拽分组 |
| Excel解析 | Python openpyxl / pandas | 后端解析 |
| 后端框架 | Python FastAPI | 异步，自带Swagger |
| ORM | SQLAlchemy | 动态表查询 |
| 数据库 | MySQL 8.x | 主数据存储 |
| AI引擎 | DashScope (Qwen) | 阿里百炼 token plan |

---

## 3. 数据模型

### 3.1 数据类型定义

```sql
data_types (
    id              INT PK AUTO_INCREMENT
    code            VARCHAR(50) UNIQUE   -- 类型标识: "operation", "forecast"
    name            VARCHAR(255)         -- 显示名称: "运营数据", "预估数据"
    table_name      VARCHAR(255)         -- 物理表名: "data_operation"
    columns_json    JSON                 -- 列定义: [{"name":"站点","type":"varchar"},...]
    created_at      DATETIME
)
```

### 3.2 动态业务数据表

按数据类型建固定表，每月导入追加数据，`period` 字段标识月份。
示例（运营数据表）：

```sql
data_operation (
    id              INT PK AUTO_INCREMENT
    period          VARCHAR(7)           -- 月份: "2024-01"
    source_file     VARCHAR(255)         -- 来源文件名
    uploaded_at     DATETIME
    uploaded_by     VARCHAR(50)
    -- 以下列为示例，实际由 columns_json 定义
    站点            VARCHAR(255),
    区域            VARCHAR(100),
    充电量          DECIMAL(12,2),
    充电时长        DECIMAL(10,2),
    金额            DECIMAL(12,2)
)
```

### 3.3 导入记录

```sql
import_records (
    id              INT PK AUTO_INCREMENT
    data_type_id    INT FK
    period          VARCHAR(7)
    file_name       VARCHAR(255)
    row_count       INT
    status          VARCHAR(20)          -- "success", "partial", "failed"
    error_log       TEXT
    uploaded_at     DATETIME
    uploaded_by     VARCHAR(50)
)
```

### 3.4 报表定义

```sql
reports (
    id              INT PK AUTO_INCREMENT
    name            VARCHAR(255)
    data_type_id    INT FK
    config_json     JSON
    shared_token    VARCHAR(64) NULL     -- NULL=不分享
    token_expires   DATETIME
    created_by      VARCHAR(50)
    created_at      DATETIME
    updated_at      DATETIME
)
```

config_json 结构：
```json
{
    "columns": ["时间", "区域", "充电量"],
    "aggregations": {"充电量": "sum"},
    "group_by": ["区域"],
    "filters": [{"field": "时间", "op": ">=", "value": "2024-01-01"}],
    "chart_type": "bar",
    "sort": {"field": "充电量", "order": "desc"},
    "limit": 100
}
```

### 3.5 AI会话与消息

```sql
ai_sessions (
    id              INT PK AUTO_INCREMENT
    session_id      VARCHAR(64) UNIQUE
    data_type_id    INT FK
    user            VARCHAR(50)
    created_at      DATETIME
    updated_at      DATETIME
)

ai_messages (
    id              INT PK AUTO_INCREMENT
    session_id      VARCHAR(64) FK
    role            VARCHAR(20)          -- "user", "assistant", "follow_up"
    content         TEXT
    sql_query       TEXT
    result_preview  JSON
    created_at      DATETIME
)
```

---

## 4. AI 对话引擎

### 4.1 交互模式

- **嵌入式面板** — AI对话面板嵌入在报表设计器右侧
- **Follow-up建议按钮** — AI回复底部展示3-4个建议按钮，点击即发送
- **多轮对话** — 继承筛选上下文，支持追问、环比、趋势分析

### 4.2 AI与拖拽联动

- AI查询结果可**一键转为报表** — 参数同步到拖拽设计器
- 拖拽报表可**一键AI分析** — 配置丢给AI做趋势分析、异常检测

### 4.3 LLM适配层

```
┌─────────────────────────────────────┐
│        AI Engine (上层逻辑)          │
└──────────────────┬──────────────────┘
         ┌─────────▼──────────┐
         │   LLM Adapter      │ ← 统一接口: generate(prompt) → response
         │   (LLMProvider)    │
         └─────────┬──────────┘
                   │
         ┌─────────▼──────────┐
         │  DashScope (Qwen)  │ ← 默认实现, OpenAI兼容
         └────────────────────┘
```

适配层要求：
- 统一 OpenAI 兼容的消息格式
- 支持流式输出
- 配置化模型名称和API密钥

### 4.4 Prompt 设计

```
System Prompt:
  你是数据分析助手。用户正在查询数据集 "{dataset_name}"。
  可用字段: {schema_info}
  当前对话上下文: {conversation_history}

  任务:
  1. 理解意图，提取: 时间范围、筛选条件、聚合指标、分组维度
  2. 信息不完整时提出追问（最多一个）
  3. 信息足够时生成MySQL查询
  4. 对结果做简要分析，推荐可视化方式

  安全限制:
  - 只生成SELECT语句
  - 不允许DELETE/UPDATE/INSERT/DROP
  - 最多返回1000行
```

### 4.5 安全限制

- **SQL白名单** — 只允许SELECT，独立校验层扫描禁关键词
- **字段白名单** — 只能引用数据类型中实际存在的字段
- **结果限制** — 自动追加LIMIT 1000
- **执行超时** — SQL执行超时5秒，超时终止

### 4.6 对话上下文维护

上下文栈内容：
- **数据集上下文** — 当前分析的数据类型
- **筛选上下文** — 已设定的时间、区域等筛选，后续追问继承
- **结果缓存** — 上次查询结果，追问可直接内存处理
- **澄清状态** — AI追问后用户回答，自动补全缺失参数

---

## 5. 功能模块

### 5.1 数据管理

- **数据导入** — 选择数据类型 → 上传Excel → 预览 → 确认导入
- **导入记录** — 列表展示已导入记录，含状态、行数、时间
- **数据类型管理** — 运营预定义数据类型及其字段结构

### 5.2 报表中心

- **报表列表** — 已保存报表，支持搜索/筛选
- **新建报表** — 拖拽设计器 + AI对话面板
  - 字段选择、聚合方式、分组维度、筛选条件、图表类型
  - AI自然语言查询 + follow-up建议
- **报表预览** — 实时预览 + 导出Excel
- **分享管理** — 生成分享链接（token + 过期时间）

### 5.3 分享

- 分享链接**公开可访问**，有token即可查看
- 支持设置过期时间

---

## 6. API 设计

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 导入 | POST | `/api/imports/upload` | 上传Excel，解析预览 |
| 导入 | POST | `/api/imports/confirm` | 确认导入数据库 |
| 导入 | GET | `/api/imports` | 导入记录列表 |
| 报表 | POST | `/api/reports` | 保存报表定义 |
| 报表 | GET | `/api/reports` | 报表列表 |
| 报表 | POST | `/api/reports/:id/execute` | 执行报表查询 |
| 报表 | GET | `/api/reports/:id/export` | 导出Excel |
| 报表 | POST | `/api/reports/:id/share` | 生成分享链接 |
| 分享 | GET | `/api/share/:token` | 查看分享报表 |
| AI | POST | `/api/ai/sessions` | 创建AI会话 |
| AI | POST | `/api/ai/sessions/:id/message` | 发送NL查询 |
| AI | POST | `/api/ai/sessions/:id/follow-up` | 执行follow-up |
| AI | GET | `/api/ai/sessions/:id` | 获取会话历史 |
| 类型 | CRUD | `/api/data-types` | 数据类型管理 |

---

## 7. 待确认项

- [ ] 前端页面设计 — 用户将用 Stitch 设计后深入沟通
- [ ] 具体数据类型及列定义 — 等拿到实际Excel表结构后细化
- [ ] 日期字段处理 — 原始数据中有，具体格式待确认
