<template>
  <div>
    <h3>分享报表</h3>
    <ReportPreview v-if="result" :data="result" chart-type="bar" />
    <el-alert v-if="error" :title="error" type="error" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import ReportPreview from '../components/ReportPreview.vue'

const route = useRoute()
const result = ref(null)
const error = ref('')

onMounted(async () => {
  try { result.value = await api.viewShare(route.params.token) }
  catch (e) { error.value = e.message }
})
</script>
