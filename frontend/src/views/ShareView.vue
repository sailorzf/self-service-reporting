<template>
  <div class="shared-report">
    <div v-if="loading" class="loading">加载中...</div>
    <el-alert v-else-if="error" :title="error" type="error" show-icon />
    <template v-else-if="config">
      <div class="report-header">
        <h2>{{ reportName }}</h2>
        <span class="meta">报表分享</span>
      </div>
      <div class="canvas-container" :style="{ width: canvasWidth + 'px', height: canvasHeight + 'px' }">
        <div
          v-for="comp in components"
          :key="comp.id"
          class="comp"
          :style="{ left: comp.x + 'px', top: comp.y + 'px', width: comp.width + 'px', height: comp.height + 'px' }"
        >
          <div class="comp-header" :style="{ color: comp.theme_color }">{{ comp.name || comp.type }}</div>

          <div v-if="comp.type === 'text'" class="comp-text">{{ comp.content }}</div>

          <div v-else-if="comp.type === 'kpi'" class="comp-kpi">
            <div class="kpi-value">{{ getKpiValue(comp) }}</div>
            <div class="kpi-label">{{ comp.name }}</div>
          </div>

          <div v-else-if="comp.type === 'table'" class="comp-table">
            <el-table :data="getTableData(comp)" border stripe size="small" style="width: 100%;" max-height="100%">
              <el-table-column v-for="h in getHeaders(comp)" :key="h" :prop="safeProp(h)" :label="h" />
            </el-table>
          </div>

          <div v-else class="chart-container" :ref="el => setChartRef(comp.id, el)"></div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import * as echarts from 'echarts'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const config = ref(null)
const reportName = ref('')
const componentData = ref({})
const chartRefs = {}
const chartInstances = []

onMounted(async () => {
  try {
    const data = await api.viewShare(route.params.token)
    config.value = data.config
    reportName.value = data.report_name
    componentData.value = data.component_data
    const canvas = data.config.canvas || {}
    canvasWidth.value = canvas.width || 1200
    canvasHeight.value = canvas.height || 800
    await nextTick()
    initCharts()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})

const canvasWidth = ref(1200)
const canvasHeight = ref(800)

function setChartRef(id, el) {
  if (el) chartRefs[id] = el
}

function getHeaders(comp) {
  const d = componentData.value[comp.id]
  return d ? d.headers : []
}

function safeProp(h) {
  return String(h).replace(/[.\[\]]/g, '_')
}

function getTableData(comp) {
  const d = componentData.value[comp.id]
  if (!d || !d.rows) return []
  return d.rows.map(row => {
    const obj = {}
    d.headers.forEach((h, i) => { obj[safeProp(h)] = row[i] })
    return obj
  })
}

function getKpiValue(comp) {
  const d = componentData.value[comp.id]
  if (d && d.rows && d.rows.length > 0) return d.rows[0][0]
  return '-'
}

function initCharts() {
  if (!config.value) return
  const comps = config.value.components || []
  comps.forEach(comp => {
    if (!['bar', 'line', 'pie'].includes(comp.type)) return
    const el = chartRefs[comp.id]
    if (!el) return
    const d = componentData.value[comp.id]
    if (!d || !d.chart_data) return
    const chart = echarts.init(el)
    chartInstances.push(chart)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: d.chart_data.categories || [] },
      yAxis: { type: 'value' },
      series: d.chart_data.series || [],
      grid: { left: '10%', right: '5%', bottom: '10%', top: '10%' }
    })
  })
}
</script>

<style scoped>
.shared-report { padding: 20px; background: #f5f7fa; min-height: 100vh; }
.loading { text-align: center; padding: 60px; font-size: 16px; color: #999; }
.report-header { text-align: center; margin-bottom: 20px; }
.report-header h2 { font-size: 20px; color: #333; }
.report-header .meta { font-size: 12px; color: #999; }
.canvas-container { position: relative; margin: 0 auto; background: #fff; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
.comp { position: absolute; border: 1px solid #e4e7ed; border-radius: 4px; padding: 12px; overflow: hidden; }
.comp-header { font-size: 14px; font-weight: bold; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #eee; }
.comp-text { font-size: 13px; line-height: 1.6; white-space: pre-wrap; }
.comp-kpi { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; }
.comp-kpi .kpi-value { font-size: 32px; font-weight: bold; color: #333; }
.comp-kpi .kpi-label { font-size: 12px; color: #999; margin-top: 4px; }
.comp-table { height: calc(100% - 28px); overflow: auto; }
.chart-container { width: 100%; height: calc(100% - 28px); }
</style>
