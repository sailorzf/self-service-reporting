<template>
  <el-table :data="tableData" border stripe style="width: 100%;">
    <el-table-column v-for="header in data.headers" :key="header" :prop="header" :label="header" />
  </el-table>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ data: { type: Object, required: true } })
const tableData = computed(() =>
  props.data.rows.map(row => {
    const obj = {}
    props.data.headers.forEach((h, i) => { obj[h] = row[i] })
    return obj
  })
)
</script>
