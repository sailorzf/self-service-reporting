<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <el-button @click="$router.push('/import')">返回列表</el-button>
        <h3 style="margin: 0;">导入详情</h3>
      </div>
      <span class="text-muted">共 {{ rowCount }} 条数据</span>
    </div>

    <el-descriptions :column="4" border style="margin-bottom: 16px;">
      <el-descriptions-item label="文件名">{{ record.file_name }}</el-descriptions-item>
      <el-descriptions-item label="数据表">{{ dataTypes.find(d => d.id === record.data_type_id)?.name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="月份">{{ record.period }}</el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="record.status === 'success' ? 'success' : 'danger'" size="small">
          {{ record.status === 'success' ? '成功' : '失败' }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="行数">{{ record.row_count }}</el-descriptions-item>
      <el-descriptions-item label="导入时间">{{ record.uploaded_at }}</el-descriptions-item>
      <el-descriptions-item label="操作人">{{ record.uploaded_by }}</el-descriptions-item>
    </el-descriptions>

    <h4>导入数据</h4>
    <el-table :data="tableRows" border size="small" v-loading="loading" max-height="500">
      <el-table-column v-for="h in headers" :key="h" :prop="h" :label="h" :width="150" show-overflow-tooltip />
    </el-table>
    <el-empty v-if="!loading && tableRows.length === 0" description="无数据" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const route = useRoute()
const record = ref({})
const dataTypes = ref([])
const headers = ref([])
const tableRows = ref([])
const rowCount = ref(0)
const loading = ref(false)

onMounted(async () => {
  try {
    loading.value = true
    const records = await api.getImports()
    const r = records.find(x => x.id === parseInt(route.params.id))
    if (!r) {
      ElMessage.error('记录不存在')
      return
    }
    record.value = r
    dataTypes.value = await api.getDataTypes()
    const data = await api.getImportData(r.id)
    headers.value = data.headers
    tableRows.value = data.rows.map(row => {
      const obj = {}
      data.headers.forEach((h, i) => { obj[h] = row[i] })
      return obj
    })
    rowCount.value = data.row_count
  } catch (e) {
    ElMessage.error('加载失败: ' + e.message)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.text-muted { color: #909399; font-size: 14px; }
</style>
