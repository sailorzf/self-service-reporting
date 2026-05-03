# Report Designer Canvas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将报表设计器从表单式重构为拖拽画布式，支持 6 种组件自由布局，每个组件独立 SQL 查询，AI 对话自动填入 SQL

**Architecture:** 三栏布局（左=组件库 220px, 中=画布 flex, 右=设置+AI 320px）。每个组件包含独立 SQL，通过 raw_sql 端点独立查询。画布用 `interact.js` 实现拖拽+缩放。旧报表配置自动迁移为单组件格式。

**Tech Stack:** Vue3, Element Plus, ECharts, interact.js, FastAPI, SQLAlchemy

**Dependencies:** 需要安装 `interact.js` — `npm install interactjs`

---

### Task 1: 安装 interactjs 依赖

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装 interactjs**

Run in `frontend/`:
```bash
npm install interactjs
```

- [ ] **Step 2: 验证安装**

```bash
node -e "console.log(require('interactjs/package.json').version)"
```
Expected: prints version number

---

### Task 2: 后端 - 报表配置 Schema 更新

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: 定义 CanvasComponent 和 CanvasConfig schema**

```python
class CanvasComponent(BaseModel):
    id: str
    type: str  # "text" | "kpi" | "table" | "bar" | "line" | "pie"
    name: str = ""
    x: int = 16
    y: int = 16
    width: int = 260
    height: int = 180
    data_type_id: Optional[int] = None
    sql: str = ""
    chart_type: str = "table"
    theme_color: str = "#409eff"
    content: str = ""  # for text component

class CanvasConfig(BaseModel):
    width: int = 1200
    height: int = 800

class ReportConfigCanvas(BaseModel):
    canvas: Optional[CanvasConfig] = CanvasConfig()
    components: list[CanvasComponent] = []
```

Place these after existing `ReportConfig` class. The existing `ReportConfig` (with columns/aggregations) stays for backward compatibility.

- [ ] **Step 2: Verify the file still parses**

```bash
cd backend && python -c "from app.schemas import ReportConfigCanvas, CanvasComponent; print('OK')"
```
Expected: `OK`

---

### Task 3: 后端 - raw_sql 执行端点

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/api/reports.py`

- [ ] **Step 1: Update QueryExecute schema**

```python
class QueryExecute(BaseModel):
    data_type_id: Optional[int] = None
    config: Optional[ReportConfig] = None
    override_filters: list[FilterSpec] = []
    raw_sql: Optional[str] = None
```

- [ ] **Step 2: Add raw_sql execution logic to execute_query**

In `execute_query` function, add at the top:

```python
@router.post("/execute", response_model=QueryResult)
def execute_query(query: QueryExecute, db: Session = Depends(get_db)):
    # Raw SQL mode
    if query.raw_sql:
        from app.security import validate_sql
        from app.config import settings
        from sqlalchemy import text
        sql = query.raw_sql.strip().rstrip(';')
        validate_sql(sql)
        if "LIMIT" not in sql.upper():
            sql = f"{sql} LIMIT {settings.max_result_rows}"
        result = db.execute(text(sql))
        rows = result.fetchall()
        headers = list(result.keys())
        formatted_rows = [list(r) for r in rows]
        return {
            "headers": headers,
            "rows": formatted_rows,
            "chart_data": DataFormatter.to_chart(headers, formatted_rows, "table"),
        }
    if not query.config:
        raise HTTPException(400, "需要指定config或raw_sql")
    # ... rest of existing code unchanged
```

- [ ] **Step 3: Verify the file parses**

```bash
cd backend && python -c "from app.api.reports import router; print('OK')"
```
Expected: `OK`

---

### Task 4: 前端 API - 新增组件级 SQL 执行

**Files:**
- Modify: `frontend/src/api/index.js`

- [ ] **Step 1: Add executeComponentSql method**

```javascript
  // 组件级 SQL 执行（raw_sql 模式）
  executeComponentSql: (rawSql) => request('/reports/execute', {
    method: 'POST',
    body: JSON.stringify({ raw_sql: rawSql }),
  }),
```

Add this after the existing `executeQuery` method.

- [ ] **Step 2: Verify the API module loads**

```bash
cd frontend && node -e "import('./src/api/index.js').then(m => console.log(Object.keys(m.api)))"
```
Expected: lists all API method names including `executeComponentSql`

---

### Task 5: 创建 CanvasComponent 组件（单个组件渲染器）

**Files:**
- Create: `frontend/src/components/CanvasComponent.vue`

- [ ] **Step 1: Create the component file**

This component renders a single canvas component based on its type and data. It wraps the component content (table, chart, KPI, text) and provides the resize handle and header bar.

```vue
<template>
  <div
    class="canvas-component"
    :class="{ selected: selected }"
    :style="{ width: comp.width + 'px', height: comp.height + 'px' }"
    @mousedown.stop="onSelect"
  >
    <!-- Header bar -->
    <div class="comp-header" @mousedown.stop="onSelect">
      <span class="comp-type-label">{{ typeLabel }}</span>
      <span class="comp-actions">
        <el-icon class="delete-btn" @click.stop="$emit('delete')"><Delete /></el-icon>
      </span>
    </div>
    <!-- Content area -->
    <div class="comp-content">
      <!-- Text component -->
      <div v-if="comp.type === 'text'" class="text-content">{{ comp.content || '双击编辑文本' }}</div>
      <!-- KPI component -->
      <div v-else-if="comp.type === 'kpi'" class="kpi-content">
        <div class="kpi-name">{{ comp.name }}</div>
        <div class="kpi-value">{{ kpiValue }}</div>
      </div>
      <!-- Table component -->
      <div v-else-if="comp.type === 'table'" class="table-content">
        <TableRenderer v-if="compData" :data="compData" />
        <div v-else class="comp-placeholder">点击「执行」预览数据</div>
      </div>
      <!-- Chart components -->
      <div v-else-if="['bar', 'line', 'pie'].includes(comp.type)" class="chart-content">
        <ChartRenderer v-if="compData" :chart-data="compData.chart_data" :chart-type="comp.type" />
        <div v-else class="comp-placeholder">点击「执行」预览图表</div>
      </div>
    </div>
    <!-- Resize handle -->
    <div class="resize-handle" @mousedown.stop></div>
  </div>
</template>

<script setup>
import { computed, defineProps, defineEmits } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import TableRenderer from './TableRenderer.vue'
import ChartRenderer from './ChartRenderer.vue'

const props = defineProps({
  comp: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  compData: { type: Object, default: null }
})
const emit = defineEmits(['select', 'delete'])

const typeLabel = computed(() => {
  const labels = { text: '文本', kpi: '数据卡片', table: '表格', bar: '柱状图', line: '折线图', pie: '饼图' }
  return labels[props.comp.type] || props.comp.type
})

const kpiValue = computed(() => {
  if (props.compData?.rows?.length > 0) {
    const val = props.compData.rows[0][0]
    return typeof val === 'number' ? val.toLocaleString() : val
  }
  return '—'
})

function onSelect() {
  emit('select', props.comp.id)
}
</script>

<style scoped>
.canvas-component {
  position: absolute;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  overflow: hidden;
  user-select: none;
}
.canvas-component.selected {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.3);
  z-index: 10;
}
.comp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 8px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
  cursor: move;
}
.comp-type-label {
  font-size: 10px;
  color: #909399;
}
.comp-actions .delete-btn {
  font-size: 14px;
  color: #909399;
  cursor: pointer;
}
.comp-actions .delete-btn:hover { color: #f56c6c; }
.comp-content {
  padding: 8px;
  height: calc(100% - 28px);
  overflow: auto;
}
.comp-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
  font-size: 12px;
}
.text-content { font-size: 13px; color: #303133; line-height: 1.6; }
.kpi-content { display: flex; flex-direction: column; justify-content: center; height: 100%; }
.kpi-name { font-size: 11px; color: #909399; margin-bottom: 4px; }
.kpi-value { font-size: 22px; font-weight: 700; color: #303133; }
.table-content { font-size: 12px; }
.chart-content { width: 100%; height: 100%; }
.resize-handle {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 12px;
  height: 12px;
  cursor: se-resize;
}
</style>
```

- [ ] **Step 2: Verify the component parses**

```bash
cd frontend && node -e "const fs = require('fs'); const content = fs.readFileSync('src/components/CanvasComponent.vue','utf8'); console.log('OK, lines:', content.split('\n').length)"
```
Expected: `OK, lines: <number>`

---

### Task 6: 重写 ReportDesigner.vue — 三栏布局 + 画布

**Files:**
- Modify: `frontend/src/views/ReportDesigner.vue`
- Modify: `frontend/src/components/AIPanel.vue` (AI 对话内联到 ReportDesigner，此文件可保留为空或后续删除)

This is the largest task. It rewrites the entire ReportDesigner with:
1. Three-panel layout (left 220px, center flex, right 320px)
2. Left panel: component library with drag support
3. Center: canvas with interact.js drag+resize
4. Right panel: component settings (top) + AI chat (bottom)

- [ ] **Step 1: Write the template**

```vue
<template>
  <div class="designer">
    <!-- Top bar -->
    <div class="top-bar">
      <el-button @click="router.push('/reports')" size="small" link>
        <el-icon><ArrowLeft /></el-icon> 返回列表
      </el-button>
      <span class="page-title">{{ editingReportId ? '编辑: ' + reportName : '新建报表' }}</span>
      <div class="top-actions">
        <el-button type="primary" size="small" @click="saveReport" :loading="saving">保存报表</el-button>
      </div>
    </div>

    <div class="main-layout">
      <!-- LEFT: Component Library -->
      <div class="left-panel">
        <div class="panel-header">组件库</div>
        <div class="panel-body">
          <div class="type-selector">
            <div class="section-label">基础组件</div>
            <div class="component-grid">
              <div
                v-for="ct in baseComponentTypes" :key="ct.type"
                class="comp-card"
                draggable="true"
                @dragstart="onDragStart(ct.type)"
                @dblclick="addComponent(ct.type)"
              >
                <div class="comp-card-icon">{{ ct.icon }}</div>
                <span class="comp-card-label">{{ ct.label }}</span>
              </div>
            </div>
          </div>
          <div class="type-selector">
            <div class="section-label">图表组件</div>
            <div class="component-grid">
              <div
                v-for="ct in chartComponentTypes" :key="ct.type"
                class="comp-card"
                draggable="true"
                @dragstart="onDragStart(ct.type)"
                @dblclick="addComponent(ct.type)"
              >
                <div class="comp-card-icon">{{ ct.icon }}</div>
                <span class="comp-card-label">{{ ct.label }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- CENTER: Canvas -->
      <div class="center-panel">
        <div class="canvas-wrapper" ref="canvasWrapper">
          <div
            class="canvas"
            ref="canvasEl"
            :style="{ width: canvasWidth + 'px', height: canvasHeight + 'px' }"
            @dragover.prevent="onDragOver"
            @drop="onDrop"
            @click.self="deselectAll"
          >
            <!-- Empty state -->
            <div v-if="components.length === 0" class="canvas-empty">
              <el-icon :size="48" color="#c0c4cc"><DocumentAdd /></el-icon>
              <p>从左侧拖拽组件到此处</p>
            </div>
            <!-- Components -->
            <div
              v-for="comp in components" :key="comp.id"
              :ref="el => setCompRef(comp.id, el)"
            >
              <CanvasComponent
                :comp="comp"
                :selected="selectedId === comp.id"
                :comp-data="compResults[comp.id]"
                @select="selectedId = comp.id"
                @delete="deleteComponent(comp.id)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: Settings + AI -->
      <div class="right-panel">
        <div class="right-content">
          <!-- Component Settings -->
          <div class="settings-section">
            <div class="settings-header">
              <span v-if="selectedComp">
                <span class="comp-badge">{{ selectedCompTypeLabel }}</span>
                组件设置
              </span>
              <span v-else class="no-selection">请先选择组件</span>
            </div>
            <div v-if="selectedComp" class="settings-body">
              <!-- Component name -->
              <div class="setting-item">
                <div class="setting-label">组件名称</div>
                <el-input v-model="selectedComp.name" size="small" placeholder="如: 本月销量" />
              </div>

              <!-- Text component: content only -->
              <template v-if="selectedComp.type === 'text'">
                <div class="setting-item">
                  <div class="setting-label">文本内容</div>
                  <el-input v-model="selectedComp.content" type="textarea" :rows="4" size="small" />
                </div>
              </template>

              <!-- Data components: data source + SQL -->
              <template v-else>
                <div class="setting-item">
                  <div class="setting-label">数据源</div>
                  <el-select v-model="selectedComp.data_type_id" size="small" placeholder="选择数据表" clearable style="width: 100%;">
                    <el-option v-for="dt in dataTypes" :key="dt.id" :label="dt.name" :value="dt.id" />
                  </el-select>
                </div>
                <div class="setting-item">
                  <div class="setting-label">SQL</div>
                  <div class="sql-area">
                    <el-input v-model="selectedComp.sql" type="textarea" :rows="5" size="small" placeholder="输入 SQL 或由 AI 生成..." spellcheck="false" />
                    <div class="sql-actions">
                      <el-button size="small" @click="executeCurrentComponent" :loading="executing" :disabled="!selectedComp.sql">执行</el-button>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- AI Chat -->
          <div class="ai-section">
            <div class="ai-header">AI 助手</div>
            <div class="ai-messages" ref="aiMessagesEl">
              <div v-if="!aiMessages.length" class="ai-hint">
                <el-icon :size="32" color="#c0c4cc"><ChatDotRound /></el-icon>
                <p>描述你的需求，AI 帮你生成 SQL</p>
              </div>
              <div v-for="(msg, i) in aiMessages" :key="i" :class="['ai-msg', msg.role]">
                <div class="ai-msg-bubble">{{ msg.content }}</div>
                <div v-if="msg.sql" class="ai-msg-sql">
                  <pre>{{ truncateSQL(msg.sql) }}</pre>
                </div>
              </div>
              <div v-if="aiFollowUps.length" class="ai-followups">
                <el-button v-for="(fu, i) in aiFollowUps" :key="i" size="small" text @click="sendFollowUp(fu)">{{ fu }}</el-button>
              </div>
            </div>
            <div class="ai-input-area">
              <el-input v-model="aiInput" placeholder="继续对话..." size="small" @keyup.enter="sendAiMessage" :disabled="aiLoading" />
              <el-button type="primary" size="small" @click="sendAiMessage" :loading="aiLoading">发送</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Write the script**

```vue
<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, DocumentAdd, ChatDotRound, Delete } from '@element-plus/icons-vue'
import { api } from '../api'
import CanvasComponent from '../components/CanvasComponent.vue'

const route = useRoute()
const router = useRouter()

// Data
const dataTypes = ref([])
const editingReportId = ref(null)
const reportName = ref('')
const saving = ref(false)

// Canvas
const canvasWidth = ref(1200)
const canvasHeight = ref(800)
const canvasWrapper = ref(null)
const canvasEl = ref(null)
const compRefs = ref({})
const compInteractInstances = ref({})

// Components
const components = ref([])
const selectedId = ref(null)
const compResults = ref({})
const executing = ref(false)

// Component types
const baseComponentTypes = [
  { type: 'text', icon: 'T', label: '文本' },
  { type: 'kpi', icon: '▤', label: '数据卡片' },
  { type: 'table', icon: '☷', label: '表格' },
]
const chartComponentTypes = [
  { type: 'bar', icon: '▃', label: '柱状图' },
  { type: 'line', icon: '⤢', label: '折线图' },
  { type: 'pie', icon: '◐', label: '饼图' },
]

// AI
const aiSessionId = ref(null)
const aiMessages = ref([])
const aiFollowUps = ref([])
const aiInput = ref('')
const aiLoading = ref(false)
const aiMessagesEl = ref(null)

// Drag state
const dragType = ref(null)

// Computed
const selectedComp = computed(() => components.value.find(c => c.id === selectedId.value))
const selectedCompTypeLabel = computed(() => {
  if (!selectedComp.value) return ''
  const all = [...baseComponentTypes, ...chartComponentTypes]
  return all.find(t => t.type === selectedComp.value.type)?.label || ''
})

// Helper: generate unique ID
function genId() {
  return 'comp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6)
}

// Add component to canvas
function addComponent(type) {
  const newComp = {
    id: genId(),
    type,
    name: '',
    x: 16 + Math.floor(Math.random() * 100),
    y: 16 + Math.floor(Math.random() * 100),
    width: type === 'text' ? 200 : type === 'kpi' ? 180 : 260,
    height: type === 'text' ? 100 : type === 'kpi' ? 80 : 180,
    data_type_id: null,
    sql: '',
    chart_type: ['bar', 'line', 'pie'].includes(type) ? type : 'table',
    theme_color: '#409eff',
    content: '',
  }
  components.value.push(newComp)
  selectedId.value = newComp.id
  nextTick(() => initInteract(newComp.id))
}

// Drag handlers
function onDragStart(type) {
  dragType.value = type
}

function onDragOver(e) {
  e.preventDefault()
}

function onDrop(e) {
  e.preventDefault()
  if (!dragType.value) return
  const rect = canvasEl.value.getBoundingClientRect()
  const x = Math.max(0, e.clientX - rect.left + canvasEl.value.parentElement.scrollLeft - 130)
  const y = Math.max(0, e.clientY - rect.top + canvasEl.value.parentElement.scrollTop - 15)
  const type = dragType.value
  dragType.value = null
  const newComp = {
    id: genId(),
    type,
    name: '',
    x: Math.round(x),
    y: Math.round(y),
    width: type === 'text' ? 200 : type === 'kpi' ? 180 : 260,
    height: type === 'text' ? 100 : type === 'kpi' ? 80 : 180,
    data_type_id: null,
    sql: '',
    chart_type: ['bar', 'line', 'pie'].includes(type) ? type : 'table',
    theme_color: '#409eff',
    content: '',
  }
  components.value.push(newComp)
  selectedId.value = newComp.id
  nextTick(() => initInteract(newComp.id))
}

// Initialize interact.js on a component element
function initInteract(compId) {
  const interact = (await import('interactjs')).default
  const el = compRefs.value[compId]
  if (!el) return
  const comp = components.value.find(c => c.id === compId)
  if (!comp) return

  const elRef = el.querySelector('.canvas-component')
  if (!elRef) return

  // Destroy existing instance
  if (compInteractInstances.value[compId]) {
    compInteractInstances.value[compId].unset()
  }

  const instance = interact(elRef)
    .draggable({
      listeners: {
        move(event) {
          comp.x += event.dx
          comp.y += event.dy
          event.target.style.transform = `translate(${comp.x}px, ${comp.y}px)`
        }
      }
    })
    .resizable({
      edges: { left: false, right: '.resize-handle', bottom: '.resize-handle', top: false },
      listeners: {
        move(event) {
          comp.width = Math.max(150, event.rect.width)
          comp.height = Math.max(80, event.rect.height)
          event.target.style.width = comp.width + 'px'
          event.target.style.height = comp.height + 'px'
        }
      }
    })

  compInteractInstances.value[compId] = instance

  // Set initial position via transform
  elRef.style.transform = `translate(${comp.x}px, ${comp.y}px)`
}

// We need to await import inside a function, so let's restructure
// Actually, let's use a different approach - import at top level
</script>
```

Wait, I need to restructure - can't use `await` inside `initInteract` with the current setup. Let me fix:

```vue
<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, DocumentAdd, ChatDotRound, Delete } from '@element-plus/icons-vue'
import interact from 'interactjs'
import { api } from '../api'
import CanvasComponent from '../components/CanvasComponent.vue'

const route = useRoute()
const router = useRouter()

// Data
const dataTypes = ref([])
const editingReportId = ref(null)
const reportName = ref('')
const saving = ref(false)

// Canvas
const canvasWidth = ref(1200)
const canvasHeight = ref(800)
const canvasWrapper = ref(null)
const canvasEl = ref(null)
const compRefs = ref({})

// Components
const components = ref([])
const selectedId = ref(null)
const compResults = ref({})
const executing = ref(false)

// Component types
const baseComponentTypes = [
  { type: 'text', icon: 'T', label: '文本' },
  { type: 'kpi', icon: '▤', label: '数据卡片' },
  { type: 'table', icon: '☷', label: '表格' },
]
const chartComponentTypes = [
  { type: 'bar', icon: '▃', label: '柱状图' },
  { type: 'line', icon: '⤢', label: '折线图' },
  { type: 'pie', icon: '◐', label: '饼图' },
]

// AI
const aiSessionId = ref(null)
const aiMessages = ref([])
const aiFollowUps = ref([])
const aiInput = ref('')
const aiLoading = ref(false)
const aiMessagesEl = ref(null)

// Drag
const dragType = ref(null)

// Computed
const selectedComp = computed(() => components.value.find(c => c.id === selectedId.value))
const selectedCompTypeLabel = computed(() => {
  if (!selectedComp.value) return ''
  const all = [...baseComponentTypes, ...chartComponentTypes]
  return all.find(t => t.type === selectedComp.value.type)?.label || ''
})

function genId() {
  return 'comp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6)
}

function addComponent(type) {
  const newComp = {
    id: genId(), type, name: '',
    x: 16 + Math.floor(Math.random() * 100),
    y: 16 + Math.floor(Math.random() * 100),
    width: type === 'text' ? 200 : type === 'kpi' ? 180 : 260,
    height: type === 'text' ? 100 : type === 'kpi' ? 80 : 180,
    data_type_id: null, sql: '',
    chart_type: ['bar', 'line', 'pie'].includes(type) ? type : 'table',
    theme_color: '#409eff', content: '',
  }
  components.value.push(newComp)
  selectedId.value = newComp.id
  nextTick(() => initInteract(newComp.id))
}

function onDragStart(type) { dragType.value = type }
function onDragOver(e) { e.preventDefault() }

function onDrop(e) {
  e.preventDefault()
  if (!dragType.value) return
  const rect = canvasEl.value.getBoundingClientRect()
  const x = Math.max(0, e.clientX - rect.left + canvasEl.value.parentElement.scrollLeft - 130)
  const y = Math.max(0, e.clientY - rect.top + canvasEl.value.parentElement.scrollTop - 15)
  const type = dragType.value
  dragType.value = null
  const newComp = {
    id: genId(), type, name: '',
    x: Math.round(x), y: Math.round(y),
    width: type === 'text' ? 200 : type === 'kpi' ? 180 : 260,
    height: type === 'text' ? 100 : type === 'kpi' ? 80 : 180,
    data_type_id: null, sql: '',
    chart_type: ['bar', 'line', 'pie'].includes(type) ? type : 'table',
    theme_color: '#409eff', content: '',
  }
  components.value.push(newComp)
  selectedId.value = newComp.id
  nextTick(() => initInteract(newComp.id))
}

function setCompRef(id, el) {
  if (el) compRefs.value[id] = el
}

function initInteract(compId) {
  const el = compRefs.value[compId]
  if (!el) return
  const comp = components.value.find(c => c.id === compId)
  if (!comp) return
  const elRef = el.querySelector('.canvas-component')
  if (!elRef) return

  const instance = interact(elRef)
    .draggable({
      listeners: {
        move(event) {
          comp.x += event.dx
          comp.y += event.dy
          elRef.style.transform = `translate(${comp.x}px, ${comp.y}px)`
        }
      }
    })
    .resizable({
      edges: { left: false, right: '.resize-handle', bottom: '.resize-handle', top: false },
      listeners: {
        move(event) {
          comp.width = Math.max(150, event.rect.width)
          comp.height = Math.max(80, event.rect.height)
          elRef.style.width = comp.width + 'px'
          elRef.style.height = comp.height + 'px'
        }
      }
    })
}

function deleteComponent(id) {
  const idx = components.value.findIndex(c => c.id === id)
  if (idx === -1) return
  components.value.splice(idx, 1)
  if (selectedId.value === id) selectedId.value = null
  delete compResults.value[id]
}

function deselectAll() { selectedId.value = null }

// Execute current component SQL
async function executeCurrentComponent() {
  const comp = selectedComp.value
  if (!comp || !comp.sql) return
  executing.value = true
  try {
    const result = await api.executeComponentSql(comp.sql)
    compResults.value[comp.id] = result
    ElMessage.success('查询成功')
  } catch (e) {
    const msg = e.message || (typeof e === 'object' ? JSON.stringify(e) : String(e))
    ElMessage.error('SQL 执行失败: ' + msg)
  } finally {
    executing.value = false
  }
}

// AI
async function initAISession() {
  try {
    const res = await api.createAISession({})
    aiSessionId.value = res.session_id
  } catch (e) {
    ElMessage.error('AI 会话创建失败: ' + (e.message || e))
  }
}

async function sendAiMessage() {
  const text = aiInput.value.trim()
  if (!text || !aiSessionId.value) return
  aiLoading.value = true
  aiMessages.value.push({ role: 'user', content: text })
  scrollToAiBottom()
  try {
    const res = await api.sendAIMessage(aiSessionId.value, text)
    aiMessages.value.push({ role: 'assistant', content: res.text, sql: res.sql_query })
    aiFollowUps.value = res.follow_ups || []
    // Auto-fill SQL into selected component
    if (res.sql_query && selectedComp.value) {
      selectedComp.value.sql = res.sql_query
    }
    scrollToAiBottom()
  } catch (e) {
    aiMessages.value.push({ role: 'assistant', content: '错误: ' + (e.message || String(e)) })
  } finally {
    aiLoading.value = false
    aiInput.value = ''
  }
}

function sendFollowUp(text) { aiInput.value = text; sendAiMessage() }

function scrollToAiBottom() {
  nextTick(() => {
    if (aiMessagesEl.value) {
      aiMessagesEl.value.scrollTop = aiMessagesEl.value.scrollHeight
    }
  })
}

function truncateSQL(sql) {
  if (!sql) return ''
  const lines = sql.split('\n').filter(Boolean)
  if (lines.length <= 2) return sql
  return lines.slice(0, 2).join('\n') + '\n...'
}

// Save report
async function saveReport() {
  const name = reportName.value || prompt('报表名称:')
  if (!name) return
  saving.value = true
  const configJson = {
    canvas: { width: canvasWidth.value, height: canvasHeight.value },
    components: components.value.map(c => ({
      id: c.id, type: c.type, name: c.name,
      x: c.x, y: c.y, width: c.width, height: c.height,
      data_type_id: c.data_type_id, sql: c.sql,
      chart_type: c.chart_type, theme_color: c.theme_color,
      content: c.content,
    }))
  }
  const reportData = {
    name,
    data_type_id: components.value[0]?.data_type_id || 0,
    config_json: configJson
  }
  try {
    if (editingReportId.value) {
      await api.updateReport(editingReportId.value, reportData)
      ElMessage.success('报表已更新')
    } else {
      await api.createReport(reportData)
      ElMessage.success('报表已保存')
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.message || String(e)))
  } finally {
    saving.value = false
  }
}

// Delete key handler
function handleKeyDown(e) {
  if (e.key === 'Delete' && selectedId.value) {
    deleteComponent(selectedId.value)
  }
}

onMounted(async () => {
  dataTypes.value = await api.getDataTypes()
  await initAISession()
  document.addEventListener('keydown', handleKeyDown)

  // Load existing report
  if (route.params.id) {
    editingReportId.value = parseInt(route.params.id)
    const reports = await api.getReports()
    const report = reports.find(r => r.id === editingReportId.value)
    if (report) {
      reportName.value = report.name
      const cfg = report.config_json
      // Check if it's new canvas format
      if (cfg.components && Array.isArray(cfg.components)) {
        components.value = cfg.components.map(c => ({
          ...c,
          x: c.x || 16, y: c.y || 16,
          width: c.width || 260, height: c.height || 180,
        }))
      } else {
        // Old format: convert to single table component
        components.value = [{
          id: genId(), type: 'table', name: report.name,
          x: 16, y: 16, width: 600, height: 300,
          data_type_id: report.data_type_id,
          sql: '', // old format doesn't store raw SQL
          chart_type: cfg.chart_type || 'table',
          theme_color: '#409eff', content: '',
          _legacy_config: cfg, // store for reference
        }]
      }
    } else {
      ElMessage.error('报表不存在')
      router.replace('/reports')
    }
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>
```

- [ ] **Step 3: Write the styles**

```vue
<style scoped>
.designer { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }

/* Top bar */
.top-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 6px 16px; border-bottom: 1px solid #e4e7ed;
  background: #fff; flex-shrink: 0;
}
.page-title { font-weight: 600; font-size: 14px; flex: 1; }
.top-actions { display: flex; gap: 8px; }

/* Main layout */
.main-layout { display: flex; flex: 1; overflow: hidden; }

/* Left panel */
.left-panel {
  width: 220px; flex-shrink: 0; border-right: 1px solid #e4e7ed;
  background: #fafafa; display: flex; flex-direction: column;
}
.panel-header {
  padding: 10px 14px; font-weight: 600; font-size: 13px;
  border-bottom: 1px solid #e4e7ed; color: #303133;
}
.panel-body { flex: 1; overflow-y: auto; padding: 12px; }
.section-label {
  font-size: 11px; color: #909399; margin-bottom: 8px; padding-left: 2px;
}
.component-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px;
}
.comp-card {
  background: #fff; border: 1px solid #dcdfe6; border-radius: 6px;
  padding: 14px 8px; text-align: center; cursor: grab;
  transition: all 0.15s;
}
.comp-card:hover { border-color: #409eff; box-shadow: 0 2px 6px rgba(64,158,255,0.15); }
.comp-card:active { cursor: grabbing; }
.comp-card-icon { font-size: 22px; color: #606266; margin-bottom: 4px; }
.comp-card-label { font-size: 11px; color: #606266; }

/* Center panel */
.center-panel { flex: 1; overflow: auto; background: #f0f2f5; min-width: 0; }
.canvas-wrapper { padding: 20px; min-height: 100%; }
.canvas {
  position: relative; background: #fff; border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  min-height: 100%;
}
.canvas-empty {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 8px; padding: 80px; color: #c0c4cc;
}
.canvas-empty p { font-size: 13px; margin: 0; }

/* Right panel */
.right-panel {
  width: 320px; flex-shrink: 0; border-left: 1px solid #e4e7ed;
  background: #fff; display: flex; flex-direction: column;
}
.right-content { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

/* Settings section */
.settings-section {
  border-bottom: 1px solid #ebeef5; flex-shrink: 0;
}
.settings-header {
  padding: 10px 14px; font-size: 12px; font-weight: 600; color: #303133;
}
.comp-badge {
  display: inline-block; background: #409eff; color: #fff;
  padding: 1px 6px; border-radius: 2px; font-size: 10px; margin-right: 6px;
}
.no-selection { color: #c0c4cc; font-weight: 400; }
.settings-body { padding: 0 14px 14px; }
.setting-item { margin-bottom: 10px; }
.setting-label {
  font-size: 11px; color: #909399; margin-bottom: 4px;
}
.sql-area { position: relative; }
.sql-actions { margin-top: 4px; display: flex; justify-content: flex-end; }

/* AI section */
.ai-section { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.ai-header {
  padding: 10px 14px; font-size: 12px; font-weight: 600; color: #303133;
  border-bottom: 1px solid #ebeef5;
}
.ai-messages { flex: 1; overflow-y: auto; padding: 10px 14px; }
.ai-hint {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 8px; padding: 40px 10px; color: #c0c4cc; text-align: center;
}
.ai-hint p { font-size: 12px; margin: 0; }
.ai-msg { margin-bottom: 8px; }
.ai-msg.user { text-align: right; }
.ai-msg-bubble {
  display: inline-block; padding: 6px 12px; border-radius: 12px;
  font-size: 12px; max-width: 90%; line-height: 1.5;
}
.ai-msg.user .ai-msg-bubble { background: #409eff; color: #fff; }
.ai-msg.assistant .ai-msg-bubble { background: #f0f2f5; color: #303133; }
.ai-msg-sql pre {
  background: #1e1e1e; color: #d4d4d4; padding: 6px 10px;
  border-radius: 4px; font-size: 11px; margin: 4px 0;
  overflow-x: auto; white-space: pre-wrap; word-break: break-all;
}
.ai-followups { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }
.ai-input-area {
  display: flex; gap: 6px; padding: 8px 14px;
  border-top: 1px solid #ebeef5;
}
.ai-input-area .el-input { flex: 1; }
</style>
```

- [ ] **Step 4: Full file verification**

Write the complete file with all three sections combined, then verify:
```bash
cd frontend && node -e "const fs=require('fs'); const c=fs.readFileSync('src/views/ReportDesigner.vue','utf8'); console.log('OK, lines:', c.split('\n').length)"
```
Expected: `OK, lines: <number>` (should be 400+)

- [ ] **Step 5: Vite compilation check**

```bash
cd frontend && npx vite build --mode development 2>&1 | head -20
```
Expected: no errors related to ReportDesigner.vue

---

### Task 7: 删除 AIPanel.vue（已整合到 ReportDesigner）

**Files:**
- Delete: `frontend/src/components/AIPanel.vue`

- [ ] **Step 1: Remove the file**

```bash
rm frontend/src/components/AIPanel.vue
```

- [ ] **Step 2: Verify no remaining references**

```bash
cd frontend && grep -r "AIPanel" src/ || echo "No references found (expected)"
```
Expected: `No references found`

---

### Task 8: 旧报表列表标记 "经典模式"

**Files:**
- Modify: `frontend/src/views/ReportListView.vue`

- [ ] **Step 1: Add "经典模式" badge for old-format reports**

Read the current ReportListView.vue first, then add a detection function:

```javascript
function isLegacyReport(report) {
  const cfg = report.config_json
  return !cfg.components || !Array.isArray(cfg.components)
}
```

In the report list template, add a tag:
```vue
<el-tag v-if="isLegacyReport(report)" type="warning" size="small" style="margin-left: 8px;">经典模式</el-tag>
```

- [ ] **Step 2: Verify**

```bash
cd frontend && node -e "const fs=require('fs'); const c=fs.readFileSync('src/views/ReportListView.vue','utf8'); console.log('OK')"
```

---

### Task 9: 后端 - AI session 无需预选择表

**Files:**
- Modify: `backend/app/schemas.py` (already done in previous session, verify)
- Modify: `backend/app/api/ai.py` (already done, verify)
- Modify: `backend/app/ai_engine.py` (already done, verify)

- [ ] **Step 1: Verify all three files have the changes**

Check that `AISessionCreate.data_type_id` is `Optional[int] = None` in schemas.py.

Run:
```bash
cd backend && python -c "from app.schemas import AISessionCreate; print(AISessionCreate.model_fields['data_type_id'])"
```
Expected: shows `annotation=int | None required=False default=None`

- [ ] **Step 2: Test empty session creation**

```bash
curl -s -X POST http://127.0.0.1:8100/api/ai/sessions -H "Content-Type: application/json" -d '{}'
```
Expected: `{"session_id": "..."}`

---

### Task 10: 端到端验证

- [ ] **Step 1: Start both services**

```powershell
cd E:\AI-Project\charging-self-report
.\manage.ps1 restart
```

- [ ] **Step 2: Open report designer in browser**

Navigate to `http://localhost:3000/reports/new`

- [ ] **Step 3: Verify all features**

1. Left panel shows 6 component cards (文本, 数据卡片, 表格, 柱状图, 折线图, 饼图)
2. Double-click a component → it appears on canvas
3. Drag a component from left panel to canvas → it appears at drop position
4. Click a component on canvas → right panel shows component settings
5. Type SQL → click 执行 → component renders data
6. Type in AI chat → AI responds with SQL → SQL auto-fills into component settings
7. Drag component to reposition → position updates
8. Resize component via bottom-right corner → size updates
9. Press Delete key → selected component removed
10. Save report → config_json contains canvas + components structure

- [ ] **Step 4: Test old report loading**

Navigate to an existing report → verify it loads as a single table component

---

### Task 11: Commit

- [ ] **Step 1: Review all changes**

```bash
cd E:\AI-Project\charging-self-report
git diff --stat
```

Expected files changed:
- `frontend/src/views/ReportDesigner.vue` (rewritten)
- `frontend/src/components/AIPanel.vue` (deleted)
- `frontend/src/components/CanvasComponent.vue` (new)
- `frontend/src/api/index.js` (added executeComponentSql)
- `backend/app/schemas.py` (added CanvasComponent, CanvasConfig, ReportConfigCanvas, raw_sql)
- `backend/app/api/reports.py` (raw_sql execution)
- `frontend/package.json` (interactjs added)
- `frontend/src/views/ReportListView.vue` (legacy badge)

- [ ] **Step 2: Commit**

```bash
cd E:\AI-Project\charging-self-report
git add frontend/src/views/ReportDesigner.vue frontend/src/components/CanvasComponent.vue frontend/src/api/index.js frontend/src/views/ReportListView.vue backend/app/schemas.py backend/app/api/reports.py frontend/package.json package-lock.json
git rm frontend/src/components/AIPanel.vue
git commit -m "feat: redesign report designer as drag-and-drop canvas with component library, per-component SQL, and integrated AI chat

- Three-panel layout: component library (left), free canvas (center), settings + AI (right)
- 6 component types: text, KPI card, table, bar chart, line chart, pie chart
- Free drag and resize via interact.js
- Each component has independent SQL query with raw_sql endpoint
- AI chat auto-fills generated SQL into selected component
- Legacy reports auto-migrate to single-component canvas format
- Removed standalone AIPanel component

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```
