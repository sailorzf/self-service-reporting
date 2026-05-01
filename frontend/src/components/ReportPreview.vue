<template>
  <div>
    <div v-if="data && data.headers" style="margin-bottom: 16px;">
      <ChartRenderer v-if="data.chart_data && props.chartType !== 'table'" :chart-data="data.chart_data" :chart-type="props.chartType" />
      <TableRenderer :data="data" />
    </div>
    <el-empty v-else description="暂无数据" />
  </div>
</template>

<script setup>
import TableRenderer from './TableRenderer.vue'
import ChartRenderer from './ChartRenderer.vue'
const props = defineProps({
  data: { type: Object, default: null },
  chartType: { type: String, default: 'table' }
})
</script>
