<template>
  <div class="ai-panel">
    <h4>AI 分析</h4>
    <div class="messages">
      <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role]">
        <div class="text">{{ msg.content }}</div>
        <div v-if="msg.result" class="result">
          <TableRenderer v-if="msg.result.headers" :data="msg.result" />
        </div>
      </div>
    </div>
    <div class="follow-ups" v-if="followUps.length">
      <el-button v-for="(fu, i) in followUps" :key="i" size="small" @click="sendFollowUp(fu)">{{ fu }}</el-button>
    </div>
    <div class="input-area">
      <el-input v-model="input" placeholder="输入你的问题..." @keyup.enter="sendMessage" :disabled="loading" />
      <el-button type="primary" @click="sendMessage" :loading="loading">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api'
import TableRenderer from './TableRenderer.vue'

const props = defineProps({ sessionId: { type: String, required: true } })
const emit = defineEmits(['query-complete'])
const messages = ref([])
const followUps = ref([])
const input = ref('')
const loading = ref(false)

async function sendMessage(text) {
  if (!text) text = input.value
  if (!text) return
  loading.value = true
  messages.value.push({ role: 'user', content: text })
  try {
    const res = await api.sendAIMessage(props.sessionId, text)
    messages.value.push({ role: 'assistant', content: res.text, result: res.result_preview })
    followUps.value = res.follow_ups || []
    emit('query-complete', res)
  } catch (e) {
    messages.value.push({ role: 'assistant', content: `错误: ${e.message}` })
  } finally {
    loading.value = false
    input.value = ''
  }
}
function sendFollowUp(text) { sendMessage(text) }
defineExpose({ sendMessage })
</script>

<style scoped>
.ai-panel { display: flex; flex-direction: column; height: 100%; }
.messages { flex: 1; overflow-y: auto; padding: 10px; }
.msg { margin-bottom: 12px; }
.msg.user { text-align: right; }
.msg.assistant { text-align: left; }
.follow-ups { padding: 8px; display: flex; gap: 8px; flex-wrap: wrap; }
.input-area { display: flex; gap: 8px; padding: 8px; }
</style>
