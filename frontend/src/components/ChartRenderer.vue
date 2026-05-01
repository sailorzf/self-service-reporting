<template>
  <div ref="chartRef" style="width: 100%; height: 400px;"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  chartData: { type: Object, required: true },
  chartType: { type: String, default: 'bar' }
})

const chartRef = ref(null)
let chart = null

onMounted(() => { chart = echarts.init(chartRef.value); renderChart() })
watch(() => props.chartData, renderChart, { deep: true })

function renderChart() {
  if (!chart || !props.chartData) return
  const option = {
    title: { text: '报表结果' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: props.chartData.categories || [] },
    yAxis: { type: 'value' },
    series: props.chartData.series?.map(s => ({ ...s, type: props.chartType === 'bar' ? 'bar' : props.chartType === 'line' ? 'line' : 'pie' })) || []
  }
  chart.setOption(option, true)
}
</script>
