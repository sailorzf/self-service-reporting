const BASE_URL = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || '请求失败')
  }
  return res.json()
}

export const api = {
  getDataTypes: () => request('/data-types/'),
  createDataType: (data) => request('/data-types/', { method: 'POST', body: JSON.stringify(data) }),
  deleteDataType: (id) => request(`/data-types/${id}`, { method: 'DELETE' }),

  uploadPreview: async (file, dataTypeId = null) => {
    const formData = new FormData()
    formData.append('file', file)
    if (dataTypeId) formData.append('data_type_id', dataTypeId)
    const res = await fetch(`${BASE_URL}/imports/upload`, { method: 'POST', body: formData })
    return res.json()
  },

  inferSchema: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${BASE_URL}/imports/infer-schema`, { method: 'POST', body: formData })
    return res.json()
  },

  getReports: () => request('/reports/'),
  createReport: (data) => request('/reports/', { method: 'POST', body: JSON.stringify(data) }),
  executeQuery: (data) => request('/reports/execute', { method: 'POST', body: JSON.stringify(data) }),
  executeReport: (id) => request(`/reports/${id}/execute`, { method: 'POST' }),
  shareReport: (id, days = 7) => request(`/reports/${id}/share?days=${days}`, { method: 'POST' }),

  createAISession: (data) => request('/ai/sessions', { method: 'POST', body: JSON.stringify(data) }),
  sendAIMessage: (sessionId, content) =>
    request(`/ai/sessions/${sessionId}/message`, { method: 'POST', body: JSON.stringify({ content }) }),
  getAISession: (sessionId) => request(`/ai/sessions/${sessionId}`),

  viewShare: (token) => request(`/share/${token}`),
}
