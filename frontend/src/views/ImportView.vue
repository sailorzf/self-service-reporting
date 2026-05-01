<template>
  <div>
    <h3>数据导入</h3>
    <el-form label-width="100px">
      <el-form-item label="数据表">
        <el-select v-model="dataTypeId" placeholder="选择数据表" @change="onDataTypeChange">
          <el-option v-for="dt in dataTypes" :key="dt.id" :label="dt.name" :value="dt.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="月份">
        <el-input v-model="period" placeholder="如: 2024-01" />
      </el-form-item>
      <el-form-item label="上传文件">
        <el-upload action="" :auto-upload="false" :on-change="handleFile" accept=".xlsx,.xls">
          <el-button>选择Excel文件</el-button>
        </el-upload>
      </el-form-item>
    </el-form>

    <div v-if="preview" style="margin-top: 16px;">
      <h4>预览 (前10行)</h4>
      <el-table :data="previewRows" border size="small">
        <el-table-column v-for="col in preview.excel_columns" :key="col" :prop="col" :label="col" width="120" />
      </el-table>
      <p>共 {{ preview.row_count }} 行</p>

      <h4 style="margin-top: 20px;">列映射</h4>
      <el-table :data="mappings" border size="small">
        <el-table-column label="Excel列名" width="180">
          <template #default="{ row }">
            {{ row.excel_column || '—' }}
          </template>
        </el-table-column>
        <el-table-column label="映射到字段" width="220">
          <template #default="{ row }">
            <el-select v-if="row.excel_column" v-model="row.db_column" size="small" clearable>
              <el-option label="不导入" :value="null" />
              <el-option v-for="col in dbColumns" :key="col.name" :label="col.name" :value="col.name" />
            </el-select>
            <span v-else class="text-muted">{{ row.db_column }}（未匹配）</span>
          </template>
        </el-table-column>
        <el-table-column label="匹配方式" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.match_type === 'exact'" type="success" size="small">精确</el-tag>
            <el-tag v-else-if="row.match_type === 'fuzzy'" type="warning" size="small">模糊</el-tag>
            <el-tag v-else-if="row.match_type === 'unmatched'" type="info" size="small">未匹配</el-tag>
            <el-tag v-else type="danger" size="small">手动</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-button type="primary" @click="confirmImport" style="margin-top: 16px;">确认导入</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const dataTypes = ref([])
const dataTypeId = ref(null)
const period = ref('')
const file = ref(null)
const preview = ref(null)
const mappings = ref([])

onMounted(async () => { dataTypes.value = await api.getDataTypes() })

const dbColumns = computed(() => {
  const dt = dataTypes.value.find(d => d.id === dataTypeId.value)
  return dt ? dt.columns_json : []
})

const previewRows = computed(() =>
  preview.value?.rows?.map(row => {
    const obj = {}
    preview.value.excel_columns.forEach((c, i) => { obj[c] = row[i] })
    return obj
  }) || []
)

function onDataTypeChange() {
  preview.value = null
  mappings.value = []
}

async function handleFile(uploadFile) {
  file.value = uploadFile.raw
  if (!dataTypeId.value) {
    ElMessage.warning('请先选择数据表')
    return
  }
  const res = await api.uploadPreview(file.value, dataTypeId.value)
  preview.value = res
  mappings.value = res.mappings || []
}

async function confirmImport() {
  if (!dataTypeId.value || !period.value || !file.value) {
    ElMessage.warning('请填写完整信息')
    return
  }
  const formData = new FormData()
  formData.append('file', file.value)
  formData.append('data_type_id', dataTypeId.value)
  formData.append('period', period.value)
  formData.append('file_name', file.value.name)
  formData.append('column_mappings', JSON.stringify(mappings.value))
  try {
    const res = await fetch('/api/imports/confirm', { method: 'POST', body: formData })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '导入失败')
    }
    const result = await res.json()
    ElMessage.success(`导入成功，共 ${result.row_count} 行`)
    preview.value = null; mappings.value = []; period.value = ''; file.value = null
  } catch (e) {
    ElMessage.error(e.message || '导入失败')
  }
}
</script>

<style scoped>
.text-muted { color: #909399; font-size: 12px; }
</style>
