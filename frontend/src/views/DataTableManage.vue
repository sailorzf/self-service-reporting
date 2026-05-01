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
            {{ col.name }}({{ col.type }}{{ formatLength(col) }})
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

    <el-dialog v-model="showCreate" title="新建数据表" width="700px">
      <el-tabs v-model="createMode">
        <el-tab-pane label="手动创建" name="manual">
          <el-form :model="form" label-width="100px" style="margin-top: 12px;">
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
                <el-table-column label="字段名" width="160">
                  <template #default="{ row: col }">
                    <el-input v-model="col.name" size="small" placeholder="字段名" />
                  </template>
                </el-table-column>
                <el-table-column label="类型" width="120">
                  <template #default="{ row: col }">
                    <el-select v-model="col.type" size="small" @change="onTypeChange(col)">
                      <el-option label="varchar" value="varchar" />
                      <el-option label="decimal" value="decimal" />
                      <el-option label="int" value="int" />
                      <el-option label="datetime" value="datetime" />
                      <el-option label="text" value="text" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="长度" width="90">
                  <template #default="{ row: col }">
                    <el-input-number v-if="col.type === 'varchar'" v-model="col.length" :min="1" :max="65535" size="small" controls-position="right" />
                    <span v-else class="text-muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="精度" width="80">
                  <template #default="{ row: col }">
                    <el-input-number v-if="col.type === 'decimal'" v-model="col.precision" :min="1" :max="65" size="small" controls-position="right" />
                    <span v-else class="text-muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="小数位" width="80">
                  <template #default="{ row: col }">
                    <el-input-number v-if="col.type === 'decimal'" v-model="col.scale" :min="0" :max="30" size="small" controls-position="right" />
                    <span v-else class="text-muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="可空" width="60">
                  <template #default="{ row: col }">
                    <el-checkbox v-model="col.nullable" />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="60">
                  <template #default="{$index}">
                    <el-button size="small" type="danger" @click="removeColumn($index)">×</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="从Excel导入" name="excel">
          <div style="margin-top: 12px;">
            <el-upload action="" :auto-upload="false" :on-change="handleExcelUpload" accept=".xlsx,.xls" drag>
              <div style="padding: 20px;">
                <p>拖拽文件到此处，或点击选择Excel文件</p>
                <p class="text-muted">系统将自动解析表头和数据类型，生成表结构</p>
              </div>
            </el-upload>
            <div v-if="inferredColumns.length > 0" style="margin-top: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span>推断的表结构（共 {{ inferredColumns.length }} 个字段）</span>
                <el-button size="small" type="primary" @click="useInferred">使用此结构</el-button>
              </div>
              <el-table :data="inferredColumns" border size="small">
                <el-table-column label="Excel列名" width="150">
                  <template #default="{ row }">{{ row.original_name }}</template>
                </el-table-column>
                <el-table-column label="推断字段名" width="160">
                  <template #default="{ row: col }">
                    <el-input v-model="col.name" size="small" />
                  </template>
                </el-table-column>
                <el-table-column label="类型" width="120">
                  <template #default="{ row: col }">
                    <el-select v-model="col.type" size="small" @change="onTypeChange(col)">
                      <el-option label="varchar" value="varchar" />
                      <el-option label="decimal" value="decimal" />
                      <el-option label="int" value="int" />
                      <el-option label="datetime" value="datetime" />
                      <el-option label="text" value="text" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="长度" width="90">
                  <template #default="{ row: col }">
                    <el-input-number v-if="col.type === 'varchar'" v-model="col.length" :min="1" :max="65535" size="small" controls-position="right" />
                    <span v-else-if="col.type === 'decimal'" class="text-muted">—</span>
                    <span v-else class="text-muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="精度" width="80">
                  <template #default="{ row: col }">
                    <el-input-number v-if="col.type === 'decimal'" v-model="col.precision" :min="1" :max="65" size="small" controls-position="right" />
                    <span v-else class="text-muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="小数位" width="80">
                  <template #default="{ row: col }">
                    <el-input-number v-if="col.type === 'decimal'" v-model="col.scale" :min="0" :max="30" size="small" controls-position="right" />
                    <span v-else class="text-muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="可空" width="60">
                  <template #default="{ row: col }">
                    <el-checkbox v-model="col.nullable" />
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createTable">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const tables = ref([])
const showCreate = ref(false)
const createMode = ref('manual')
const form = ref({
  code: '',
  name: '',
  table_name: '',
  columns_json: []
})
const inferredColumns = ref([])
const inferredTableName = ref('')

onMounted(async () => { await loadTables() })

watch(showCreate, (val) => {
  if (!val) {
    inferredColumns.value = []
    inferredTableName.value = ''
    createMode.value = 'manual'
  }
})

async function loadTables() {
  tables.value = await api.getDataTypes()
}

async function handleExcelUpload(uploadFile) {
  if (!uploadFile.raw) return
  try {
    const res = await api.inferSchema(uploadFile.raw)
    inferredColumns.value = res.columns
    inferredTableName.value = res.suggested_table_name
  } catch (e) {
    ElMessage.error('Excel解析失败: ' + (e.message || '未知错误'))
    inferredColumns.value = []
  }
}

function useInferred() {
  form.value.columns_json = inferredColumns.value.map(c => ({
    name: c.name,
    type: c.type,
    length: c.length || 255,
    precision: c.precision || 10,
    scale: c.scale || 2,
    nullable: c.nullable !== false
  }))
  form.value.table_name = inferredTableName.value
  const baseName = inferredTableName.value.replace(/^data_/, '')
  form.value.name = baseName
  form.value.code = baseName
  createMode.value = 'manual'
  ElMessage.success('表结构已填充，可在"手动创建"中编辑确认')
}

function addColumn() {
  form.value.columns_json.push({ name: '', type: 'varchar', length: 255, precision: 10, scale: 2, nullable: true })
}

function removeColumn(idx) {
  form.value.columns_json.splice(idx, 1)
}

function onTypeChange(col) {
  if (col.type === 'varchar' && !col.length) col.length = 255
  if (col.type === 'decimal') {
    if (!col.precision) col.precision = 10
    if (col.scale === undefined) col.scale = 2
  }
}

function formatLength(col) {
  if (col.type === 'varchar' && col.length) return `(${col.length})`
  if (col.type === 'decimal' && col.precision) return `(${col.precision},${col.scale || 0})`
  return ''
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
    inferredColumns.value = []
    inferredTableName.value = ''
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

<style scoped>
.text-muted { color: #909399; font-size: 12px; }
</style>
