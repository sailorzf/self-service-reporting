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
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button size="small" @click="editReport(row.id)">编辑</el-button>
          <el-button size="small" @click="executeReport(row.id)">执行</el-button>
          <el-button size="small" @click="shareReport(row.id)">分享</el-button>
          <el-dropdown @command="(cmd) => exportReport(row.id, cmd)">
            <el-button size="small">导出<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="excel">Excel</el-dropdown-item>
                <el-dropdown-item command="html">HTML</el-dropdown-item>
                <el-dropdown-item command="pdf">PDF</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
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
import { ArrowDown } from '@element-plus/icons-vue'
import { api } from '../api'
import ReportPreview from '../components/ReportPreview.vue'

const router = useRouter()
const reports = ref([])
const result = ref(null)
const currentChartType = ref('table')

onMounted(async () => {
  try {
    reports.value = await api.getReports()
  } catch (e) {
    ElMessage.error('报表列表加载失败: ' + e.message)
    reports.value = []
  }
})

function isLegacy(row) {
  const cfg = row.config_json
  return cfg && !cfg.canvas
}

function editReport(id) {
  router.push(`/reports/${id}`)
}

async function executeReport(id) {
  try {
    result.value = await api.executeReport(id)
    currentChartType.value = 'table'
  } catch (e) {
    ElMessage.warning('画布报表请使用保存后在画布中查看，或使用导出功能')
  }
}

function exportReport(id, format = 'excel') {
  const url = `/api/reports/${id}/export`
  if (format === 'excel') {
    window.open(url, '_blank')
  } else if (format === 'html') {
    window.open(`${url}/html`, '_blank')
  } else if (format === 'pdf') {
    window.open(`${url}/html`, '_blank')
  }
}

async function shareReport(id) {
  const res = await api.shareReport(id)
  const fullUrl = `${window.location.origin}${res.share_url}`
  try {
    await navigator.clipboard.writeText(fullUrl)
    ElMessage.success('分享链接已复制到剪贴板')
  } catch {
    ElMessage.success(`分享链接: ${fullUrl}`)
  }
}
</script>
