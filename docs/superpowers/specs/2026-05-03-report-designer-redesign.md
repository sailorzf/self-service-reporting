# 报表编辑器重构设计

**日期**: 2026-05-03
**目标**: 将报表设计器从"表单式"重构为"拖拽画布式"，提升可视化报表的灵活性

---

## 1. 总体架构

三栏布局，垂直撑满整个视口（`100vh`）：

| 左栏 (220px) | 中栏 (自适应) | 右栏 (320px) |
|---|---|---|
| 组件库 | 自由画布 | 组件设置 + AI 对话 |

### 1.1 组件数据结构

每个画布上的组件包含以下字段：

```typescript
interface CanvasComponent {
  id: string            // 唯一标识
  type: string          // "text" | "kpi" | "table" | "bar" | "line" | "pie"
  name: string          // 用户自定义标题（如"本月销量"）
  x: number             // 画布中的水平位置 (px)
  y: number             // 画布中的垂直位置 (px)
  width: number         // 组件宽度 (px)
  height: number        // 组件高度 (px)
  // 数据配置
  data_type_id: number | null    // 数据源（数据表 ID）
  sql: string                    // 查询 SQL（AI 生成或手写）
  // 展示配置
  chart_type: string             // 仅图表组件使用："bar" | "line" | "pie"
  theme_color: string            // 主题色
}
```

报表配置 JSON 结构：

```json
{
  "canvas": {
    "width": 1200,
    "height": 800
  },
  "components": [CanvasComponent, ...]
}
```

### 1.2 数据流

每个组件独立 SQL、独立查询：

```
组件 SQL → 后端 /api/reports/execute (raw_sql 模式) → 渲染到组件
```

---

## 2. 左栏：组件库

纯组件列表，不含数据源选择。

### 2.1 组件类型

| 类型 | 标识 | 说明 |
|---|---|---|
| 文本 | `text` | 纯文本展示，不绑定数据源 |
| 数据卡片 | `kpi` | 显示单个 KPI 数值（SQL 首行首列） |
| 表格 | `table` | 以表格展示查询结果 |
| 柱状图 | `bar` | 第一列=X 轴，其余=数据系列 |
| 折线图 | `line` | 同上 |
| 饼图 | `pie` | 同上 |

### 2.2 交互

- 拖拽组件卡片到中栏画布，释放时创建新组件实例
- 也可点击组件卡片，在画布中心位置创建

---

## 3. 中栏：自由画布

### 3.1 功能

- **所见即所得**：画布上直接渲染组件内容，无需独立预览区
- **自由拖拽**：鼠标按住组件拖动，改变组件位置
- **自由缩放**：鼠标拖拽组件右下角控制点，改变组件大小
- **选中高亮**：点击组件选中，显示蓝色边框 + 控制点
- **删除组件**：选中后按 Delete 键或右键菜单删除
- **画布滚动**：画布内容超出视口时可滚动

### 3.2 技术选型

使用 `vue-draggable-resizable` 或 `interact.js` 实现拖拽+缩放。
优先选 `interact.js`（更轻量、不绑定 Vue 版本）。

### 3.3 空状态

画布无组件时显示提示文案"拖拽组件到此处"。

---

## 4. 右栏：组件设置 + AI 对话

### 4.1 上半部分：组件设置

选中画布上的组件后显示，未选中时显示"请先选择组件"。

**字段**：
- **组件名称**：`el-input`，用户自定义标题
- **数据源**：`el-select`，选择数据表（`data_type_id`）
- **SQL**：`el-input type="textarea"`，内联编辑，支持：
  - 手动编写 SQL
  - AI 自动填入（下方 AI 生成后自动写入）
  - 「编辑」按钮展开/收起（默认收起显示摘要）
  - 「执行」按钮 = 执行 SQL 并渲染到画布组件

**文本组件特殊处理**：文本组件没有 SQL 和数据源，只显示内容编辑框。

### 4.2 下半部分：AI 对话

- **聊天记录**：用户消息（右对齐蓝色气泡）+ AI 消息（左对齐灰色气泡）
- **AI 回复包含 SQL 时**：在消息中显示 SQL 摘要（一行代码），自动写入上方 SQL 框
- **后续建议**：AI 返回的 `follow_ups` 显示为可点击标签
- **输入框**：底部输入 + 发送按钮

**AI 会话管理**：
- 进入报表设计页面时自动创建 AI 会话（无需指定数据表）
- AI 收到所有数据表的 schema，根据用户查询意图自动选择涉及的表

---

## 5. 后端变更

### 5.1 报表配置 JSON 结构调整

`Report.config_json` 从旧的 `columns/aggregations/group_by` 结构改为：

```json
{
  "canvas": { "width": 1200, "height": 800 },
  "components": [
    {
      "id": "comp_1",
      "type": "bar",
      "name": "本月销量",
      "x": 16, "y": 16, "width": 260, "height": 180,
      "data_type_id": 1,
      "sql": "SELECT station_name, SUM(charge_num) FROM data_test_data GROUP BY station_name",
      "chart_type": "bar",
      "theme_color": "#409eff"
    }
  ]
}
```

### 5.2 `execute_query` 端点增强

`QueryExecute` schema 增加 `raw_sql` 字段：

```python
class QueryExecute(BaseModel):
    data_type_id: Optional[int] = None
    config: Optional[ReportConfig] = None
    raw_sql: Optional[str] = None  # 新增：裸 SQL 执行
```

当 `raw_sql` 存在时，跳过 SQLBuilder，直接执行原始 SQL 并返回结果。

### 5.3 AI 会话无需预选择表

`AISessionCreate.data_type_id` 改为可选。不指定时 AI 加载所有表 schema，根据用户意图自动选择。

---

## 6. 前端文件变更

| 文件 | 操作 | 说明 |
|---|---|---|
| `ReportDesigner.vue` | **重写** | 三栏布局、自由画布、组件管理 |
| `AIPanel.vue` | **删除** | AI 对话已整合到 ReportDesigner 右栏 |
| `ReportPreview.vue` | **保留** | 组件内部使用其渲染逻辑 |
| `api/index.js` | **修改** | 新增组件级 SQL 执行调用 |
| `report_engine.py` | **新增** | `execute_raw_sql` 方法 |
| `schemas.py` | **修改** | `QueryExecute` 增加 `raw_sql` |
| `api/reports.py` | **修改** | `execute_query` 支持 `raw_sql` |
| `api/ai.py` | **修改** | `data_type_id` 可选 |
| `ai_engine.py` | **修改** | prompt 增加 `used_tables` 输出 |

---

## 7. 旧报表兼容

旧报表的 `config_json` 使用 `columns/aggregations/group_by` 格式。迁移策略：

- 旧报表加载时自动转换：将配置包装为一个表格组件
- 编辑后保存时自动升级为新的 canvas 格式
- `ReportListView.vue` 显示旧报表标记为"经典模式"

---

## 8. 风险与边界

- **画布缩放**：初始版本不做画布缩放（zoom），只支持滚动
- **组件对齐**：初始版本不做自动对齐/吸附功能
- **多表 JOIN**：组件 SQL 可写多表 JOIN，AI 也可生成多表 SQL
- **SQL 安全**：复用已有的 `validate_sql` 机制，只允许 SELECT
