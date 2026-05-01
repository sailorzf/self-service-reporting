<template>
  <div class="designer">
    <el-row :gutter="16" style="height: calc(100vh - 100px);">
      <el-col :span="5">
        <el-card>
          <template #header>字段面板</template>
          <el-select v-model="dataTypeId" placeholder="选择数据类型" style="margin-bottom: 12px;">
            <el-option v-for="dt in dataTypes" :key="dt.id" :label="dt.name" :value="dt.id" />
          </el-select>
          <el-checkbox-group v-model="selectedColumns">
            <el-checkbox v-for="col in availableColumns" :key="col" :value="col">{{ col }}</el-checkbox>
          </el-checkbox-group>
          <el-divider />
          <el-form size="small">
            <el-form-item label="聚合">
              <el-select v-model="aggregation" placeholder="选择聚合函数">
                <el-option label="SUM" value="sum" /><el-option label="AVG" value="avg" />
                <el-option label="COUNT" value="count" /><el-option label="MAX" value="max" />
                <el-option label="MIN" value="min" />
              </el-select>
            </el-form-item>
            <el-form-item label="图表类型">
              <el-select v-model="chartType">
                <el-option label="表格" value="table" /><el-option label="柱状图" value="bar" />
                <el-option label="折线图" value="line" /><el-option label="饼图" value="pie" />
              </el-select>
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="runQuery" :loading="loading" style="width: 100%;">查询</el-button>
          <el-button @click="saveReport" style="width: 100%; margin-top: 8px;">保存报表</el-button>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card style="height: 100%;">
          <template #header>预览</template>
          <ReportPreview :data="result" :chart-type="chartType" />
        </el-card>
      </el-col>
      <el-col :span="7">
        <el-card style="height: 100%;">
          <AIPanel v-if="aiSessionId" :session-id="aiSessionId" @query-complete="onAIQueryComplete" />
          <div v-else><el-button @click="initAISession" type="primary">开启AI分析</el-button></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import AIPanel from '../components/AIPanel.vue'
import ReportPreview from '../components/ReportPreview.vue'

const dataTypes = ref([])
const dataTypeId = ref(null)
const selectedColumns = ref([])
const aggregation = ref('')
const chartType = ref('table')
const result = ref(null)
const loading = ref(false)
const aiSessionId = ref(null)

const availableColumns = computed(() => {
  const dt = dataTypes.value.find(d => d.id === dataTypeId.value)
  return dt ? dt.columns_json.map(c => c.name) : []
})

onMounted(async () => { dataTypes.value = await api.getDataTypes() })

async function runQuery() {
  if (!dataTypeId.value || selectedColumns.value.length === 0) { ElMessage.warning('请选择数据类型和字段'); return }
  loading.value = true
  const config = {
    columns: selectedColumns.value,
    aggregations: aggregation.value && selectedColumns.value[0] ? { [selectedColumns.value[0]]: aggregation.value } : {},
    group_by: selectedColumns.value.filter(c => c !== selectedColumns.value[0]),
    filters: [],
    chart_type: chartType.value,
    limit: 100
  }
  try {
    result.value = await api.executeQuery({ data_type_id: dataTypeId.value, config })
  } catch (e) { ElMessage.error(e.message) }
  finally { loading.value = false }
}

async function initAISession() {
  if (!dataTypeId.value) { ElMessage.warning('请先选择数据类型'); return }
  const res = await api.createAISession({ data_type_id: dataTypeId.value })
  aiSessionId.value = res.session_id
}

function onAIQueryComplete(res) { if (res.result_preview) { result.value = res.result_preview } }

async function saveReport() {
  const name = prompt('报表名称:')
  if (!name) return
  await api.createReport({
    name, data_type_id: dataTypeId.value,
    config_json: {
      columns: selectedColumns.value,
      aggregations: aggregation.value && selectedColumns.value[0] ? { [selectedColumns.value[0]]: aggregation.value } : {},
      group_by: [], filters: [], chart_type: chartType.value, limit: 100
    }
  })
  ElMessage.success('报表已保存')
}
</script>

<style scoped>.designer { padding: 16px; }</style>
