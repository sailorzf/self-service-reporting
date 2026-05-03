<template>
  <div class="designer">
    <!-- Toolbar -->
    <div class="designer-toolbar">
      <div class="toolbar-left">
        <el-button @click="goBack">返回</el-button>
        <span v-if="loadedReportName" class="toolbar-report-name">{{ loadedReportName }}</span>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="saveReport" :loading="loading">保存</el-button>
        <el-dropdown v-if="reportId" @command="handleExport" trigger="click">
          <el-button>导出<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="excel">Excel</el-dropdown-item>
              <el-dropdown-item command="html">HTML</el-dropdown-item>
              <el-dropdown-item command="pdf">PDF</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button v-if="reportId" @click="shareCurrentReport">分享</el-button>
      </div>
    </div>

    <!-- Main body: Left Panel, Canvas, Right Panel -->
    <div class="designer-body">
      <!-- Left Panel: Component Library -->
      <div class="panel-left">
      <h3 class="panel-title">组件库</h3>
      <div class="component-grid">
        <div
          v-for="item in componentTypes"
          :key="item.type"
          class="component-card"
          draggable="true"
          @dragstart="onDragStart(item.type, $event)"
        >
          <span class="comp-icon">{{ item.icon }}</span>
          <span class="comp-name">{{ item.name }}</span>
        </div>
      </div>
    </div>

    <!-- Center: Canvas Area -->
    <div
      class="panel-canvas"
      @drop="onDrop"
      @dragover.prevent
      @dragenter.prevent
      @click="onCanvasClick"
    >
      <div
        ref="canvasArea"
        class="canvas-area"
        :class="{ 'has-components': components.length > 0 }"
      >
        <!-- Empty state -->
        <div v-if="components.length === 0" class="canvas-empty">
          <p>拖拽组件到此处</p>
        </div>

        <!-- Placed components -->
        <div
          v-for="(comp, index) in components"
          :key="comp.id"
          :ref="el => componentRefs[comp.id] = el"
          class="canvas-item"
          :class="{ selected: comp.id === selectedId, locked: comp.locked }"
          :style="{
            transform: `translate(${comp.x}px, ${comp.y}px)`,
            width: comp.width + 'px',
            height: comp.height + 'px',
            zIndex: comp.zIndex || index + 1
          }"
          @click.stop="selectComponent(comp.id)"
          @contextmenu.prevent="showContextMenu(comp.id, $event)"
        >
          <CanvasComponent
            :component="comp"
            :data="componentData[comp.id]"
            :selected="comp.id === selectedId"
          />
          <!-- Resize handle -->
          <div v-if="comp.id === selectedId" class="resize-handle"></div>
          <!-- Action button (appears on select) -->
          <div v-if="comp.id === selectedId && !comp.locked" class="comp-action-btn">
            <el-dropdown trigger="click" @command="(cmd) => handleCompAction(cmd, comp.id)">
              <el-button size="small" circle @click.stop>
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy">
                    <el-icon><CopyDocument /></el-icon> 复制
                  </el-dropdown-item>
                  <el-dropdown-item command="rename">
                    <el-icon><Edit /></el-icon> 重命名
                  </el-dropdown-item>
                  <el-dropdown-item command="lock">
                    <el-icon><Lock /></el-icon> 锁定
                  </el-dropdown-item>
                  <el-dropdown-item command="bringFront">
                    <el-icon><Top /></el-icon> 置于顶层
                  </el-dropdown-item>
                  <el-dropdown-item command="sendBack">
                    <el-icon><Bottom /></el-icon> 置于底层
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <el-icon><Delete /></el-icon> 删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <!-- Lock indicator -->
          <div v-if="comp.locked" class="comp-lock-indicator">
            <el-icon><Lock /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Panel: Settings + AI Chat -->
    <div class="panel-right">
      <!-- Component Settings -->
      <div class="settings-section">
        <h3 class="panel-title">组件设置</h3>
        <template v-if="selectedComponent">
          <div class="setting-item">
            <label>名称</label>
            <el-input v-model="selectedComponent.name" placeholder="组件名称" size="small" />
          </div>

          <!-- Non-text components -->
          <template v-if="selectedComponent.type !== 'text'">
            <div class="setting-item">
              <label>数据源</label>
              <el-select
                v-model="selectedComponent.data_type_id"
                placeholder="选择数据表"
                size="small"
                style="width: 100%;"
              >
                <el-option
                  v-for="dt in dataTypes"
                  :key="dt.id"
                  :label="dt.name"
                  :value="dt.id"
                />
              </el-select>
            </div>

            <div class="setting-item">
              <label>SQL</label>
              <div class="sql-editor-wrapper">
                <el-input
                  v-if="sqlExpanded"
                  v-model="selectedComponent.sql"
                  type="textarea"
                  :rows="6"
                  placeholder="输入SQL查询语句"
                  class="sql-textarea"
                />
                <div v-else class="sql-collapsed">
                  {{ selectedComponent.sql || '未设置SQL' }}
                </div>
                <div class="sql-actions">
                  <el-button size="small" @click="sqlExpanded = !sqlExpanded">
                    {{ sqlExpanded ? '收起' : '编辑' }}
                  </el-button>
                  <el-button size="small" type="primary" @click="executeComponentSql" :loading="loading">
                    执行
                  </el-button>
                </div>
              </div>
            </div>
          </template>

          <!-- Text component -->
          <template v-else>
            <div class="setting-item">
              <label>内容</label>
              <el-input
                v-model="selectedComponent.content"
                type="textarea"
                :rows="6"
                placeholder="输入文本内容"
              />
            </div>
          </template>
        </template>
        <p v-else class="no-selection">选择画布上的组件以编辑其设置</p>
      </div>

      <!-- AI Chat -->
      <div class="chat-section">
        <h3 class="panel-title">AI 分析</h3>
        <div class="chat-messages" ref="chatMessagesRef">
          <div
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            class="chat-message"
            :class="msg.role"
          >
            <div class="chat-bubble">
              <p>{{ msg.content }}</p>
              <pre v-if="msg.sql_query" class="sql-block">{{ msg.sql_query }}</pre>
              <div v-if="msg.used_tables && msg.used_tables.length" class="used-tables">
                使用表: {{ msg.used_tables.join(', ') }}
              </div>
            </div>
            <!-- Follow-up suggestions -->
            <div v-if="msg.follow_ups && msg.follow_ups.length" class="follow-ups">
              <el-tag
                v-for="(s, i) in msg.follow_ups"
                :key="i"
                size="small"
                class="follow-up-tag"
                @click="sendFollowUp(s)"
              >
                {{ s }}
              </el-tag>
            </div>
          </div>
          <div v-if="chatLoading" class="chat-message ai">
            <div class="chat-bubble"><p>分析中...</p></div>
          </div>
        </div>
        <div class="chat-input-area">
          <el-input
            v-model="chatInput"
            placeholder="输入问题..."
            size="small"
            @keydown.enter="sendChatMessage"
          />
          <el-button type="primary" size="small" @click="sendChatMessage" :loading="chatLoading">
            发送
          </el-button>
        </div>
      </div>
    </div>
    <!-- end designer-body -->
  </div>
  <!-- end designer -->
</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, MoreFilled, CopyDocument, Edit, Lock, Top, Bottom, Delete } from '@element-plus/icons-vue'
import { api } from '../api'
import CanvasComponent from '../components/CanvasComponent.vue'
import interact from 'interactjs'

const route = useRoute()
const router = useRouter()

// State
const components = ref([])
const selectedId = ref(null)
const dataTypes = ref([])
const componentData = ref({})
const aiSessionId = ref(null)
const chatMessages = ref([])
const chatInput = ref('')
const chatLoading = ref(false)
const loading = ref(false)
const sqlExpanded = ref(false)
const reportId = ref(route.params.id ? Number(route.params.id) : null)
const loadedReportName = ref('')
const canvasWidth = ref(1200)
const canvasHeight = ref(800)
const loadedComponents = ref(false)

// Watch for route changes to load different reports
watch(() => route.params.id, async (newId) => {
  if (newId) {
    reportId.value = Number(newId)
    // Reset state before loading new report
    components.value = []
    selectedId.value = null
    componentData.value = {}
    loadedComponents.value = true
    await loadDataTypes()
    await loadReport(reportId.value)
    nextTick(() => initAllInteract())
  } else {
    reportId.value = null
    loadedReportName.value = ''
    components.value = []
    selectedId.value = null
  }
}, { immediate: false })

// Refs
const canvasArea = ref(null)
const chatMessagesRef = ref(null)
const componentRefs = {}

// Component types for left panel
const componentTypes = [
  { type: 'text', icon: 'T', name: '文本' },
  { type: 'kpi', icon: '▤', name: '数据卡片' },
  { type: 'table', icon: '☷', name: '表格' },
  { type: 'bar', icon: '▃', name: '柱状图' },
  { type: 'line', icon: '⤢', name: '折线图' },
  { type: 'pie', icon: '◐', name: '饼图' },
]

// Computed
const selectedComponent = computed(() => {
  return components.value.find(c => c.id === selectedId.value) || null
})

// Helpers
function typeLabel(type) {
  const labels = { text: '文本', kpi: '数据卡片', table: '表格', bar: '柱状图', line: '折线图', pie: '饼图' }
  return labels[type] || type
}

function genId() {
  return 'comp_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
}

function defaultDimensions(type) {
  const defaults = {
    text: { width: 240, height: 120 },
    kpi: { width: 200, height: 120 },
    table: { width: 480, height: 260 },
    bar: { width: 400, height: 260 },
    line: { width: 400, height: 260 },
    pie: { width: 320, height: 260 }
  }
  return defaults[type] || { width: 260, height: 180 }
}

// Drag from left panel
function onDragStart(type, event) {
  event.dataTransfer.setData('componentType', type)
  event.dataTransfer.effectAllowed = 'copy'
}

function onDrop(event) {
  event.preventDefault()
  const type = event.dataTransfer.getData('componentType')
  if (!type) return

  const rect = canvasArea.value.getBoundingClientRect()
  const x = event.clientX - rect.left + canvasArea.value.scrollLeft
  const y = event.clientY - rect.top + canvasArea.value.scrollTop

  const dims = defaultDimensions(type)
  const comp = {
    id: genId(),
    type,
    name: typeLabel(type),
    x: Math.max(0, x - dims.width / 2),
    y: Math.max(0, y - dims.height / 2),
    width: dims.width,
    height: dims.height,
    data_type_id: null,
    sql: '',
    chart_type: type,
    theme_color: '#409eff',
    content: ''
  }
  components.value.push(comp)
  selectedId.value = comp.id
  initInteractForComponent(comp)
}

// Selection
function selectComponent(id) {
  selectedId.value = id
}

function onCanvasClick() {
  selectedId.value = null
}

// Component actions
function handleCompAction(cmd, compId) {
  const comp = components.value.find(c => c.id === compId)
  if (!comp) return
  switch (cmd) {
    case 'copy':
      duplicateComponent(compId)
      break
    case 'rename':
      renameComponent(compId)
      break
    case 'lock':
      comp.locked = !comp.locked
      break
    case 'bringFront':
      comp.zIndex = Math.max(...components.value.map(c => c.zIndex || 1)) + 1
      break
    case 'sendBack':
      comp.zIndex = Math.min(...components.value.map(c => c.zIndex || 1)) - 1
      break
    case 'delete':
      deleteComponent(compId)
      break
  }
}

function duplicateComponent(compId) {
  const orig = components.value.find(c => c.id === compId)
  if (!orig) return
  const dup = {
    ...JSON.parse(JSON.stringify(orig)),
    id: genId(),
    name: orig.name + ' (副本)',
    x: orig.x + 20,
    y: orig.y + 20,
    locked: false
  }
  components.value.push(dup)
  selectedId.value = dup.id
  // Copy data preview if exists
  if (componentData.value[compId]) {
    componentData.value[dup.id] = componentData.value[compId]
  }
  nextTick(() => initInteractForComponent(dup))
  ElMessage.success('组件已复制')
}

function renameComponent(compId) {
  const comp = components.value.find(c => c.id === compId)
  if (!comp) return
  const name = prompt('组件名称:', comp.name)
  if (name && name.trim()) {
    comp.name = name.trim()
  }
}

function deleteComponent(compId) {
  components.value = components.value.filter(c => c.id !== compId)
  delete componentData.value[compId]
  if (selectedId.value === compId) selectedId.value = null
}

function showContextMenu(compId, event) {
  selectComponent(compId)
  // Right-click selects, user can use action button or Delete key
}

// Delete key
function handleKeydown(e) {
  if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId.value) {
    // Don't delete if user is typing in an input
    const tag = e.target.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA') return
    components.value = components.value.filter(c => c.id !== selectedId.value)
    delete componentData.value[selectedId.value]
    selectedId.value = null
  }
}

// Execute component SQL
async function executeComponentSql() {
  const comp = selectedComponent.value
  if (!comp || !comp.sql.trim()) {
    ElMessage.warning('请输入SQL语句')
    return
  }
  loading.value = true
  try {
    const result = await api.executeComponentSql({ raw_sql: comp.sql })
    componentData.value[comp.id] = {
      headers: result.headers,
      rows: result.rows
    }
    ElMessage.success('查询完成')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

// Save report
async function saveReport() {
  const config = {
    canvas: { width: 1200, height: 800 },
    components: components.value
  }
  const data = {
    name: loadedReportName.value || '未命名报表',
    data_type_id: null,
    config_json: config
  }

  loading.value = true
  try {
    if (reportId.value) {
      await api.updateReport(reportId.value, data)
      ElMessage.success('报表已更新')
    } else {
      const name = prompt('报表名称:')
      if (!name) return
      data.name = name
      const res = await api.createReport(data)
      ElMessage.success('报表已保存')
      router.replace(`/reports/${res.id}`)
      reportId.value = res.id
      loadedReportName.value = res.name
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/reports')
}

function handleExport(format) {
  if (!reportId.value) {
    ElMessage.warning('请先保存报表')
    return
  }
  const url = `/api/reports/${reportId.value}/export`
  if (format === 'excel') {
    window.open(url, '_blank')
  } else if (format === 'html') {
    window.open(`${url}/html`, '_blank')
  } else if (format === 'pdf') {
    window.open(`${url}/html`, '_blank')
  }
}

async function shareCurrentReport() {
  const res = await api.shareReport(reportId.value)
  const fullUrl = `${window.location.origin}${res.share_url}`
  try {
    await navigator.clipboard.writeText(fullUrl)
    ElMessage.success('分享链接已复制到剪贴板')
  } catch {
    ElMessage.success(`分享链接: ${fullUrl}`)
  }
}

// AI Chat
async function sendChatMessage() {
  console.log('[chat] sendChatMessage called, input:', chatInput.value, 'sessionId:', aiSessionId.value)
  const content = chatInput.value?.trim()
  if (!content) { ElMessage.warning('请输入内容'); return }
  if (!aiSessionId.value) { ElMessage.error('AI会话未初始化，请刷新页面重试'); return }

  console.log('[chat] Sending message:', content)
  chatMessages.value.push({ role: 'user', content })
  chatInput.value = ''
  chatLoading.value = true
  try {
    const res = await api.sendAIMessage(aiSessionId.value, content)
    console.log('[chat] Response:', res)
    const aiMsg = {
      role: 'ai',
      content: res.text || '',
      sql_query: res.sql_query || null,
      follow_ups: res.follow_ups || [],
      used_tables: res.used_tables || []
    }
    chatMessages.value.push(aiMsg)

    // Auto-fill and execute SQL for selected component
    if (res.sql_query && selectedComponent.value) {
      selectedComponent.value.sql = res.sql_query
      sqlExpanded.value = true
      // Auto-execute to update chart preview
      try {
        const result = await api.executeComponentSql({ raw_sql: res.sql_query })
        componentData.value[selectedComponent.value.id] = {
          headers: result.headers,
          rows: result.rows
        }
        ElMessage.success('查询已执行，图表已更新')
      } catch (e) {
        ElMessage.warning('SQL执行失败: ' + e.message)
      }
    }
  } catch (e) {
    console.error('[chat] Error:', e)
    ElMessage.error(e.message)
  } finally {
    chatLoading.value = false
  }
}

function sendFollowUp(suggestion) {
  chatInput.value = suggestion
  sendChatMessage()
}

// Load data types
async function loadDataTypes() {
  dataTypes.value = await api.getDataTypes()
}

// Load existing report
async function loadReport(id) {
  const reports = await api.getReports()
  const report = reports.find(r => r.id === id)
  if (!report) {
    ElMessage.error('报表不存在')
    return
  }
  loadedReportName.value = report.name
  const config = report.config_json
  if (config && config.components) {
    // Canvas format: { canvas: {...}, components: [...] }
    components.value = config.components
    if (config.canvas) {
      canvasWidth.value = config.canvas.width || 1200
      canvasHeight.value = config.canvas.height || 800
    }
  } else if (config && config.columns) {
    // Migrate old format to single table component
    const comp = {
      id: genId(),
      type: config.chart_type === 'table' ? 'table' : (config.chart_type || 'bar'),
      name: report.name,
      x: 50,
      y: 50,
      width: 480,
      height: 260,
      data_type_id: report.data_type_id,
      sql: '',
      chart_type: config.chart_type || 'bar',
      theme_color: '#409eff',
      content: ''
    }
    components.value = [comp]
  }
  if (components.value.length > 0) {
    selectedId.value = components.value[0].id
  }

  // Auto-execute SQL for all components that have a query
  await executeAllComponentsSql()
}

async function executeAllComponentsSql() {
  for (const comp of components.value) {
    const sql = comp.sql?.trim()
    if (!sql) continue
    try {
      const result = await api.executeComponentSql({ raw_sql: sql })
      componentData.value[comp.id] = {
        headers: result.headers,
        rows: result.rows
      }
    } catch (e) {
      // Silent fail on load - component will show empty
      console.warn(`[ReportDesigner] SQL execution failed for ${comp.name}:`, e.message)
    }
  }
}

// Init AI session
async function initAISession() {
  try {
    const res = await api.createAISession({})
    if (res && res.session_id) {
      aiSessionId.value = res.session_id
    } else {
      throw new Error('返回响应无效')
    }
  } catch (e) {
    // Fallback: try with a data_type_id
    try {
      const res2 = await api.createAISession({ data_type_id: dataTypes.value[0]?.id })
      aiSessionId.value = res2.session_id
    } catch (e2) {
      ElMessage.error('AI会话创建失败: ' + e2.message)
    }
  }
}

// interact.js setup
function initInteractForComponent(comp) {
  nextTick(() => {
    const el = componentRefs[comp.id]
    if (!el) return

    const interactInstance = interact(el)

    // Draggable
    interactInstance.draggable({
      enabled: () => !comp.locked,
      inertia: true,
      modifiers: [
        interact.modifiers.restrictRect({
          restriction: 'parent',
          endOnly: false
        })
      ],
      listeners: {
        start() {
          selectComponent(comp.id)
        },
        move(event) {
          comp.x = (comp.x || 0) + event.dx
          comp.y = (comp.y || 0) + event.dy
          comp.x = Math.max(0, comp.x)
          comp.y = Math.max(0, comp.y)
        }
      }
    })

    // Resizable
    interactInstance.resizable({
      enabled: () => !comp.locked,
      edges: { bottom: '.resize-handle', right: '.resize-handle' },
      modifiers: [
        interact.modifiers.restrictSize({
          min: { width: 150, height: 80 }
        })
      ],
      listeners: {
        move(event) {
          comp.width = Math.max(150, event.rect.width)
          comp.height = Math.max(80, event.rect.height)
        }
      }
    })
  })
}

// Initialize interact for all components
function initAllInteract() {
  components.value.forEach(comp => {
    initInteractForComponent(comp)
  })
}

onMounted(async () => {
  await loadDataTypes()
  await initAISession()

  if (reportId.value) {
    await loadReport(reportId.value)
  }

  window.addEventListener('keydown', handleKeydown)
  nextTick(() => initAllInteract())
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  // Clean up interact instances
  components.value.forEach(comp => {
    const el = componentRefs[comp.id]
    if (el) {
      interact(el).unset()
    }
  })
})

// Watch for new components being added
watch(components, (newVal, oldVal) => {
  if (newVal.length > oldVal?.length) {
    const added = newVal.find(c => !oldVal?.find(o => o.id === c.id))
    if (added) {
      nextTick(() => initInteractForComponent(added))
    }
  }
}, { deep: false })

// Auto-scroll chat
watch(chatMessages, () => {
  nextTick(() => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    }
  })
}, { deep: true })
</script>

<style scoped>
.designer {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Toolbar */
.designer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  min-height: 48px;
}
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 8px; }
.toolbar-report-name { font-size: 14px; font-weight: bold; color: #333; padding: 0 12px; }

/* Main content below toolbar */
.designer-body {
  display: flex;
  flex-direction: row;
  flex: 1;
  overflow: hidden;
}

.panel-left {
  width: 220px;
  min-width: 220px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  padding: 16px 12px;
  overflow-y: auto;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.component-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.component-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;
  user-select: none;
}

.component-card:hover {
  background: #ecf5ff;
  border-color: #409eff;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.2);
}

.component-card:active {
  cursor: grabbing;
}

.comp-icon {
  font-size: 22px;
  color: #409eff;
}

.comp-name {
  font-size: 12px;
  color: #606266;
}

/* Center Canvas */
.panel-canvas {
  flex: 1;
  overflow: auto;
  background: #f5f7fa;
  position: relative;
}

.canvas-area {
  min-width: 1200px;
  min-height: 800px;
  position: relative;
  border: 2px dashed #dcdfe6;
  margin: 16px;
  border-radius: 8px;
  background: #fff;
}

.canvas-area.has-components {
  border-style: solid;
}

.canvas-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #c0c4cc;
  font-size: 18px;
  pointer-events: none;
}

/* Canvas Items */
.canvas-item {
  position: absolute;
  z-index: 1;
  pointer-events: auto;
  cursor: grab;
}

.canvas-item.selected {
  z-index: 10;
  cursor: grabbing;
}

.resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 14px;
  height: 14px;
  cursor: nwse-resize;
  z-index: 20;
}

.resize-handle::after {
  content: '';
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 8px;
  height: 8px;
  border-right: 2px solid #409eff;
  border-bottom: 2px solid #409eff;
}

/* Action button on selected component */
.comp-action-btn {
  position: absolute;
  top: -14px;
  right: -14px;
  z-index: 30;
}

.comp-action-btn :deep(.el-button) {
  background: #fff;
  border-color: #409eff;
  color: #409eff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  width: 28px;
  height: 28px;
  min-height: 28px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Lock indicator */
.comp-lock-indicator {
  position: absolute;
  top: -14px;
  right: -14px;
  z-index: 30;
  background: #909399;
  color: #fff;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
}

/* Locked component visual hint */
.canvas-item.locked {
  cursor: default;
  opacity: 0.85;
}

.canvas-item.locked .canvas-component {
  border-color: #909399 !important;
}

/* Right Panel */
.panel-right {
  width: 320px;
  min-width: 320px;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #e4e7ed;
  background: #fff;
  overflow: hidden;
}

.settings-section {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
  border-bottom: 1px solid #e4e7ed;
}

.no-selection {
  color: #c0c4cc;
  font-size: 13px;
  text-align: center;
  margin-top: 20px;
}

.setting-item {
  margin-bottom: 14px;
}

.setting-item label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 4px;
}

/* SQL Editor */
.sql-editor-wrapper {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.sql-textarea :deep(textarea) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  border: none;
  padding: 8px;
  line-height: 1.5;
}

.sql-collapsed {
  padding: 6px 8px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-height: 24px;
  line-height: 1.4;
}

.sql-actions {
  display: flex;
  gap: 4px;
  padding: 4px 6px;
  background: #f5f7fa;
  border-top: 1px solid #e4e7ed;
}

/* AI Chat */
.chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-section .panel-title {
  padding: 16px 12px 8px;
  margin: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
}

.chat-message {
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
}

.chat-message.user {
  align-items: flex-end;
}

.chat-message.ai {
  align-items: flex-start;
}

.chat-bubble {
  max-width: 90%;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.chat-message.user .chat-bubble {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 2px;
}

.chat-message.ai .chat-bubble {
  background: #f0f2f5;
  color: #303133;
  border-bottom-left-radius: 2px;
}

.chat-bubble p {
  margin: 0;
}

.sql-block {
  margin: 6px 0 0 0;
  padding: 6px 8px;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-x: auto;
  max-height: 120px;
}

.used-tables {
  margin-top: 4px;
  font-size: 11px;
  color: #909399;
}

.follow-ups {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.follow-up-tag {
  cursor: pointer;
}

.chat-input-area {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
}
</style>
