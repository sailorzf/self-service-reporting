<template>
  <div
    class="canvas-component"
    :class="{ selected }"
  >
    <!-- Header bar -->
    <div class="component-header comp-header-draggable" :style="{ backgroundColor: component.theme_color || '#409eff' }">
      <span class="component-name">{{ component.name }}</span>
      <span v-if="component.locked" class="lock-badge" title="已锁定">
        <el-icon><Lock /></el-icon>
      </span>
      <el-dropdown trigger="click" @command="(cmd) => $emit('action', cmd, component.id)">
        <span class="header-menu-btn" @click.stop>
          <el-icon><MoreFilled /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="copy">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-dropdown-item>
            <el-dropdown-item command="rename">
              <el-icon><Edit /></el-icon> 重命名
            </el-dropdown-item>
            <el-dropdown-item command="lock">
              <el-icon><Lock /></el-icon> {{ component.locked ? '解锁' : '锁定' }}
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

    <!-- Content area -->
    <div class="component-content">
      <!-- Text -->
      <div v-if="component.type === 'text'" class="text-content">
        {{ component.content }}
      </div>

      <!-- KPI -->
      <div v-else-if="component.type === 'kpi'" class="kpi-content">
        <div class="kpi-value">{{ kpiValue }}</div>
        <div class="kpi-label">{{ component.name }}</div>
      </div>

      <!-- Table -->
      <div v-else-if="component.type === 'table'" class="table-content">
        <el-table v-if="data && data.headers" :data="tableData" border stripe size="small" style="width: 100%;">
          <el-table-column
            v-for="header in data.headers"
            :key="header"
            :prop="header"
            :label="header"
          />
        </el-table>
        <el-empty v-else description="暂无数据" :image-size="60" />
      </div>

      <!-- Charts (bar / line / pie) -->
      <div v-else-if="['bar', 'line', 'pie'].includes(component.type)" class="chart-content">
        <div ref="chartRef" class="chart-container"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { MoreFilled, CopyDocument, Edit, Lock, Top, Bottom, Delete } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

defineEmits(['action'])

const props = defineProps({
  component: { type: Object, required: true },
  data: { type: Object, default: null },
  selected: { type: Boolean, default: false }
})

const chartRef = ref(null)
let chart = null

const typeLabel = computed(() => {
  const labels = {
    text: '文本',
    kpi: '数据卡片',
    table: '表格',
    bar: '柱状图',
    line: '折线图',
    pie: '饼图'
  }
  return labels[props.component.type] || props.component.type
})

const kpiValue = computed(() => {
  if (props.data && props.data.rows && props.data.rows.length > 0) {
    return props.data.rows[0][0]
  }
  return '--'
})

const tableData = computed(() => {
  if (!props.data || !props.data.headers) return []
  return props.data.rows.map(row => {
    const obj = {}
    props.data.headers.forEach((h, i) => { obj[h] = row[i] })
    return obj
  })
})

function renderChart() {
  if (!chart || !props.data || !props.data.headers || props.data.rows.length === 0) return

  const headers = props.data.headers
  const rows = props.data.rows
  const xAxisData = rows.map(r => r[0])
  const type = props.component.type
  const chartOpt = props.component.chart_options || {}

  if (type === 'pie') {
    const seriesData = rows.map(r => ({ name: String(r[0]), value: r[1] }))
    chart.setOption({
      title: { text: chartOpt.title || '', show: !!chartOpt.title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: seriesData
      }]
    }, true)
  } else {
    const series = headers.slice(1).map((h, i) => ({
      name: h,
      type: type === 'bar' ? 'bar' : 'line',
      data: rows.map(r => r[i + 1])
    }))

    chart.setOption({
      title: { text: chartOpt.title || '', show: !!chartOpt.title, left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { data: headers.slice(1), bottom: '0%' },
      xAxis: {
        type: 'category',
        data: xAxisData,
        name: chartOpt.xAxisName || '',
        nameLocation: 'middle',
        nameGap: 25
      },
      yAxis: {
        type: 'value',
        name: chartOpt.yAxisName || '',
        nameLocation: 'middle',
        nameGap: 30
      },
      series,
      grid: { left: '10%', right: '5%', bottom: chartOpt.xAxisName ? '15%' : '10%', top: chartOpt.title ? '20%' : '5%' }
    }, true)
  }
}

async function initChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
  await nextTick()
  renderChart()
}

// ResizeObserver for chart auto-resize
let resizeObserver = null

function initResizeObserver() {
  if (!chartRef.value || !chart) return
  resizeObserver = new ResizeObserver(() => {
    if (chart) chart.resize()
  })
  resizeObserver.observe(chartRef.value)
}

onMounted(async () => {
  if (['bar', 'line', 'pie'].includes(props.component.type)) {
    await initChart()
    initResizeObserver()
  }
})

onBeforeUnmount(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})

watch(() => props.data, () => {
  if (['bar', 'line', 'pie'].includes(props.component.type)) {
    renderChart()
  }
}, { deep: true })

// Re-render when chart_options change
watch(() => props.component?.chart_options, () => {
  if (['bar', 'line', 'pie'].includes(props.component.type)) {
    renderChart()
  }
}, { deep: true })
</script>

<style scoped>
.canvas-component {
  position: relative;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  transition: box-shadow 0.2s, border-color 0.2s;
  overflow: hidden;
  user-select: none;
  pointer-events: none;
}

.canvas-component:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.canvas-component.selected {
  border: 2px solid #409eff;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.4);
}

.component-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  color: #fff;
  font-size: 12px;
  cursor: grab;
  pointer-events: auto;
}

.component-name {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lock-badge {
  flex-shrink: 0;
  margin-left: 6px;
  opacity: 0.7;
  font-size: 12px;
  display: flex;
  align-items: center;
}

.header-menu-btn {
  flex-shrink: 0;
  margin-left: 6px;
  cursor: pointer;
  opacity: 0.75;
  font-size: 14px;
  color: #fff;
  display: flex;
  align-items: center;
  padding: 2px 4px;
  border-radius: 3px;
  transition: opacity 0.15s, background 0.15s;
}

.header-menu-btn:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.2);
}

.component-type-label {
  opacity: 0.85;
  font-size: 11px;
  flex-shrink: 0;
  margin-left: 8px;
}

.component-content {
  padding: 8px;
}

.text-content {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  color: #303133;
}

.kpi-content {
  text-align: center;
  padding: 12px 0;
}

.kpi-value {
  font-size: 36px;
  font-weight: 700;
  color: #303133;
}

.kpi-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.chart-container {
  width: 100%;
  height: 100%;
  min-height: 180px;
}
</style>
