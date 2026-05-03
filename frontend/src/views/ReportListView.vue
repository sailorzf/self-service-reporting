<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h3>报表中心</h3>
      <router-link to="/reports/new"><el-button type="primary">新建报表</el-button></router-link>
    </div>
    <el-table :data="reports" border>
      <el-table-column prop="name" label="报表名称">
        <template #default="{ row }">
          <span>{{ row.name }}</span>
          <el-tag v-if="isLegacy(row)" size="small" type="info" style="margin-left: 8px;">经典模式</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" />
      <el-table-column label="操作" width="250">
        <template #default="{ row }">
          <el-button size="small" @click="editReport(row.id)">编辑</el-button>
          <el-button size="small" @click="executeReport(row.id)">执行</el-button>
          <el-button size="small" @click="shareReport(row.id)">分享</el-button>
          <el-button size="small" @click="exportReport(row.id)">导出</el-button>
        </template>
      </el-table-column>
    </el-table>
    <ReportPreview :data="result" :chart-type="currentChartType" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import ReportPreview from '../components/ReportPreview.vue'

const router = useRouter()
const reports = ref([])
const result = ref(null)
const currentChartType = ref('table')

onMounted(async () => { reports.value = await api.getReports() })

function isLegacy(row) {
  const cfg = row.config_json
  return cfg && !cfg.canvas
}

function editReport(id) {
  router.push(`/reports/${id}`)
}

async function executeReport(id) {
  result.value = await api.executeReport(id)
  currentChartType.value = 'table'
}
async function shareReport(id) { const res = await api.shareReport(id); ElMessage.success(`分享链接: ${res.share_url}`) }
async function exportReport(id) { window.open(`/api/reports/${id}/export`) }
</script>
