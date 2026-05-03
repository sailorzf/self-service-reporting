<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
      <h3>数据表管理</h3>
      <el-button type="primary" @click="showCreate = true">新建数据表</el-button>
    </div>

    <el-table :data="tables" border>
      <el-table-column prop="code" label="标识" width="150" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="database_name" label="数据库" width="120">
        <template #default="{ row }">
          <span v-if="row.database_name">{{ row.database_name }}</span>
          <span v-else class="text-muted">默认</span>
        </template>
      </el-table-column>
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
            <el-form-item>
              <template #label>
                <span>标识</span>
                <el-tooltip content="系统内部的唯一标识，用于API引用和报表配置。例: operation" placement="top">
                  <el-icon style="margin-left: 4px; color: #909399; cursor: help;"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-input v-model="form.code" placeholder="系统内部的唯一标识，不能重复" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span>名称</span>
                <el-tooltip content="界面展示时使用的中文名，用户可以直观看到。例: 运营数据" placement="top">
                  <el-icon style="margin-left: 4px; color: #909399; cursor: help;"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-input v-model="form.name" placeholder="界面展示时使用的中文名" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span>物理表名</span>
                <el-tooltip content="MySQL数据库中实际存储数据的表名。创建数据表后会自动在MySQL中建立此表，不能与已有表重名" placement="top">
                  <el-icon style="margin-left: 4px; color: #909399; cursor: help;"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-input v-model="form.table_name" placeholder="MySQL中的实际表名，不能与已有表重名" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span>数据库名</span>
                <el-tooltip content="可选。表所在的数据库名。留空表示使用当前连接的默认数据库" placement="top">
                  <el-icon style="margin-left: 4px; color: #909399; cursor: help;"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-input v-model="form.database_name" placeholder="可选，留空表示使用默认数据库" />
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
            <el-form :model="form" label-width="100px">
              <el-form-item>
                <template #label>
                  <span>标识</span>
                  <el-tooltip content="系统内部的唯一标识，用于API引用和报表配置。例: operation" placement="top">
                    <el-icon style="margin-left: 4px; color: #909399; cursor: help;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input v-model="form.code" placeholder="自动填充，可修改，不能重复" />
              </el-form-item>
              <el-form-item>
                <template #label>
                  <span>名称</span>
                  <el-tooltip content="界面展示时使用的中文名，用户可以直观看到。例: 运营数据" placement="top">
                    <el-icon style="margin-left: 4px; color: #909399; cursor: help;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input v-model="form.name" placeholder="自动填充，可修改" />
              </el-form-item>
              <el-form-item>
                <template #label>
                  <span>物理表名</span>
                  <el-tooltip content="MySQL数据库中实际存储数据的表名。创建数据表后会自动在MySQL中建立此表，不能与已有表重名" placement="top">
                    <el-icon style="margin-left: 4px; color: #909399; cursor: help;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input v-model="form.table_name" placeholder="自动填充，可修改，不能重复" />
              </el-form-item>
              <el-form-item>
                <template #label>
                  <span>数据库名</span>
                  <el-tooltip content="可选。表所在的数据库名。留空表示使用当前连接的默认数据库" placement="top">
                    <el-icon style="margin-left: 4px; color: #909399; cursor: help;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>
                <el-input v-model="form.database_name" placeholder="可选，留空表示使用默认数据库" />
              </el-form-item>
            </el-form>
            <el-upload action="" :auto-upload="false" :on-change="handleExcelUpload" accept=".xlsx,.xls" drag :disabled="loading" :show-file-list="false">
              <div style="padding: 20px;">
                <p>拖拽文件到此处，或点击选择Excel文件</p>
                <p class="text-muted">上传后自动解析表头和数据类型，生成表结构</p>
              </div>
            </el-upload>
            <div v-if="form.columns_json.length > 0 && createMode === 'excel'" style="margin-top: 8px;">
              <el-button size="small" @click="reupload">重新上传文件</el-button>
            </div>
            <div v-if="loading" style="margin-top: 16px; text-align: center; padding: 20px;">
              <el-icon class="is-loading" style="font-size: 24px; color: #409eff;"><Loading /></el-icon>
              <p style="color: #909399; margin-top: 8px;">正在解析文件并调用 AI 翻译字段名，请稍候...</p>
            </div>
            <div v-if="form.columns_json.length > 0 && createMode === 'excel'" style="margin-top: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span>推断的表结构（共 {{ form.columns_json.length }} 个字段，可编辑后创建）</span>
              </div>
              <el-table :data="form.columns_json" border size="small">
                <el-table-column label="Excel列名" width="150">
                  <template #default="{ row }">{{ row.original_name || row.name }}</template>
                </el-table-column>
                <el-table-column label="字段名" width="160">
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
import { Loading, QuestionFilled } from '@element-plus/icons-vue'
import { api } from '../api'

const tables = ref([])
const showCreate = ref(false)
const createMode = ref('manual')
const loading = ref(false)
const form = ref({
  code: '',
  name: '',
  database_name: '',
  table_name: '',
  columns_json: []
})
onMounted(async () => { await loadTables() })

watch(showCreate, (val) => {
  if (!val) {
    resetForm()
  }
})

async function loadTables() {
  tables.value = await api.getDataTypes()
}

function resetForm() {
  form.value = { code: '', name: '', database_name: '', table_name: '', columns_json: [] }
  createMode.value = 'manual'
  loading.value = false
}

async function handleExcelUpload(uploadFile) {
  if (!uploadFile.raw) return
  loading.value = true
  try {
    const res = await api.inferSchema(uploadFile.raw)
    const baseName = res.suggested_table_name.replace(/^data_/, '')
    form.value.code = baseName
    form.value.name = baseName
    form.value.table_name = res.suggested_table_name
    form.value.columns_json = res.columns
    createMode.value = 'excel'
    ElMessage.success(`已解析 ${res.columns.length} 个字段，请检查后创建`)
  } catch (e) {
    ElMessage.error('Excel解析失败: ' + (e.message || '未知错误'))
    form.value.columns_json = []
  } finally {
    loading.value = false
  }
}

function reupload() {
  form.value.columns_json = []
  form.value.code = ''
  form.value.name = ''
  form.value.table_name = ''
  createMode.value = 'excel'
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
      database_name: form.value.database_name || null,
      table_name: form.value.table_name,
      columns_json: form.value.columns_json
    })
    ElMessage.success('数据表创建成功')
    showCreate.value = false
    resetForm()
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
