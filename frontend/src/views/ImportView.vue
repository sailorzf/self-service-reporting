<template>
  <div>
    <h3>数据导入</h3>
    <el-form label-width="100px">
      <el-form-item label="数据类型">
        <el-select v-model="dataTypeId" placeholder="选择数据类型">
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
      <el-table :data="previewRows" border>
        <el-table-column v-for="col in preview.columns" :key="col" :prop="col" :label="col" />
      </el-table>
      <p>共 {{ preview.row_count }} 行</p>
      <el-button type="primary" @click="confirmImport">确认导入</el-button>
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

onMounted(async () => { dataTypes.value = await api.getDataTypes() })

const previewRows = computed(() =>
  preview.value?.rows?.map(row => {
    const obj = {}
    preview.value.columns.forEach((c, i) => { obj[c] = row[i] })
    return obj
  }) || []
)

async function handleFile(uploadFile) {
  file.value = uploadFile.raw
  preview.value = await api.uploadPreview(file.value)
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
  try {
    const res = await fetch('/api/imports/confirm', { method: 'POST', body: formData })
    const result = await res.json()
    ElMessage.success(`导入成功，共 ${result.row_count} 行`)
    preview.value = null; period.value = ''; file.value = null
  } catch (e) {
    ElMessage.error('导入失败')
  }
}
</script>
