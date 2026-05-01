<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h3>数据表管理</h3>
      <el-button type="primary" @click="showCreate = true">新建数据表</el-button>
    </div>

    <el-table :data="tables" border>
      <el-table-column prop="code" label="标识" width="150" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="table_name" label="物理表名" width="200" />
      <el-table-column label="字段" width="300">
        <template #default="{ row }">
          <el-tag v-for="col in row.columns_json" :key="col.name" size="small" style="margin: 2px;">
            {{ col.name }}({{ col.type }})
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click="deleteTable(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="新建数据表" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="标识">
          <el-input v-model="form.code" placeholder="如: operation" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如: 运营数据" />
        </el-form-item>
        <el-form-item label="物理表名">
          <el-input v-model="form.table_name" placeholder="如: data_operation" />
        </el-form-item>
        <el-form-item label="字段定义">
          <div style="margin-bottom: 8px;">
            <el-button size="small" @click="addColumn">+ 添加字段</el-button>
          </div>
          <el-table :data="form.columns_json" border size="small">
            <el-table-column label="字段名" width="200">
              <template #default="{ row: col }">
                <el-input v-model="col.name" size="small" placeholder="字段名" />
              </template>
            </el-table-column>
            <el-table-column label="类型" width="150">
              <template #default="{ row: col }">
                <el-select v-model="col.type" size="small">
                  <el-option label="varchar" value="varchar" />
                  <el-option label="decimal" value="decimal" />
                  <el-option label="int" value="int" />
                  <el-option label="datetime" value="datetime" />
                  <el-option label="text" value="text" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{$index}">
                <el-button size="small" type="danger" @click="removeColumn($index)">×</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createTable">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const tables = ref([])
const showCreate = ref(false)
const form = ref({
  code: '',
  name: '',
  table_name: '',
  columns_json: []
})

onMounted(async () => { await loadTables() })

async function loadTables() {
  tables.value = await api.getDataTypes()
}

function addColumn() {
  form.value.columns_json.push({ name: '', type: 'varchar' })
}

function removeColumn(idx) {
  form.value.columns_json.splice(idx, 1)
}

async function createTable() {
  if (!form.value.code || !form.value.name || !form.value.table_name || !form.value.columns_json.length) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    await api.createDataType({
      code: form.value.code,
      name: form.value.name,
      table_name: form.value.table_name,
      columns_json: form.value.columns_json
    })
    ElMessage.success('数据表创建成功')
    showCreate.value = false
    form.value = { code: '', name: '', table_name: '', columns_json: [] }
    await loadTables()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function deleteTable(id) {
  try {
    await ElMessageBox.confirm('删除后无法恢复，确认删除？', '警告', { type: 'warning' })
    await api.deleteDataType(id)
    ElMessage.success('已删除')
    await loadTables()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.message)
  }
}
</script>
