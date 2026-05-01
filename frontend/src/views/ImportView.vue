<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h3 style="margin: 0;">导入记录</h3>
      <el-button type="primary" @click="$router.push('/import/new')">新增数据导入</el-button>
    </div>

    <el-table :data="records" border v-loading="loading">
      <el-table-column prop="file_name" label="文件名" />
      <el-table-column label="数据表" width="150">
        <template #default="{ row }">
          {{ dataTypes.find(d => d.id === row.data_type_id)?.name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="period" label="月份" width="100" />
      <el-table-column prop="row_count" label="行数" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
            {{ row.status === 'success' ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="uploaded_at" label="导入时间" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button v-if="row.status === 'failed'" size="small" type="danger" @click="showError(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && records.length === 0" description="暂无导入记录" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const records = ref([])
const dataTypes = ref([])
const loading = ref(false)

onMounted(async () => { await loadRecords() })

async function loadRecords() {
  loading.value = true
  try {
    records.value = await api.getImports()
    dataTypes.value = await api.getDataTypes()
  } catch (e) {
    ElMessage.error('加载失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function showError(row) {
  await ElMessageBox.alert(row.error_log || '无错误日志', '导入失败详情')
}
</script>
