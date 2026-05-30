import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // 2 分钟，AI 生成需要较长时间
})

// 项目 API
export const projectApi = {
  list: () => api.get('/projects'),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.put(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
}

// 章节 API
export const chapterApi = {
  list: (projectId) => api.get(`/projects/${projectId}/chapters`),
  get: (projectId, id) => api.get(`/projects/${projectId}/chapters/${id}`),
  create: (projectId, data) => api.post(`/projects/${projectId}/chapters`, data),
  update: (projectId, id, data) => api.put(`/projects/${projectId}/chapters/${id}`, data),
  delete: (projectId, id) => api.delete(`/projects/${projectId}/chapters/${id}`),
}

// 模型配置 API
export const modelApi = {
  listProviders: () => api.get('/ai/providers'),
  createProvider: (data) => api.post('/ai/providers', data),
  updateProvider: (id, data) => api.put(`/ai/providers/${id}`, data),
  deleteProvider: (id) => api.delete(`/ai/providers/${id}`),
  setActiveModel: (data) => api.post('/ai/active-model', data),
  getActiveModel: () => api.get('/ai/active-model'),
  testConnection: (providerId) => api.post('/ai/test-connection', null, { params: { provider_id: providerId } }),
}

// AI API
export const aiApi = {
  generateOutline: (data) => api.post('/ai/generate-outline', data),
  analyze: (chapterId) => api.post(`/ai/analyze/${chapterId}`),
  planScenes: (chapterId) => api.post(`/ai/plan-scenes/${chapterId}`),
  polish: (text, instruction) => api.post('/ai/polish', null, { params: { text, instruction } }),
  rewrite: (text, instruction) => api.post('/ai/rewrite', null, { params: { text, instruction } }),
  expand: (text, instruction) => api.post('/ai/expand', null, { params: { text, instruction } }),
}

// 文档 API
export const documentApi = {
  list: (projectId) => api.get(`/projects/${projectId}/documents`),
  get: (projectId, docType) => api.get(`/projects/${projectId}/documents/${docType}`),
  update: (projectId, docType, data) => api.put(`/projects/${projectId}/documents/${docType}`, data),
}

// 质量检查 API
export const qualityApi = {
  check: (projectId, chapterId) => api.get(`/projects/${projectId}/quality/${chapterId}`),
  summary: (projectId, chapterId) => api.get(`/projects/${projectId}/quality/${chapterId}/summary`),
}

// 对话历史 API
export const conversationApi = {
  list: (projectId) => api.get(`/projects/${projectId}/conversations`),
  create: (projectId) => api.post(`/projects/${projectId}/conversations`),
  delete: (projectId, convId) => api.delete(`/projects/${projectId}/conversations/${convId}`),
  getMessages: (projectId, convId) => api.get(`/projects/${projectId}/conversations/${convId}/messages`),
  addMessage: (projectId, convId, data) => api.post(`/projects/${projectId}/conversations/${convId}/messages`, data),
  getHistory: (projectId, convId, limit = 30) => api.get(`/projects/${projectId}/conversations/${convId}/history`, { params: { limit } }),
  rewind: (projectId, convId, messageId) => api.post(`/projects/${projectId}/conversations/${convId}/rewind`, { message_id: messageId }),
}

// 故事元素 API（伏笔/时间线/角色）
export const storyApi = {
  // 伏笔
  listForeshadowings: (projectId, status) => api.get(`/projects/${projectId}/foreshadowings`, { params: status ? { status } : {} }),
  createForeshadowing: (projectId, data) => api.post(`/projects/${projectId}/foreshadowings`, data),
  updateForeshadowing: (projectId, fsId, data) => api.put(`/projects/${projectId}/foreshadowings/${fsId}`, data),
  deleteForeshadowing: (projectId, fsId) => api.delete(`/projects/${projectId}/foreshadowings/${fsId}`),
  // 时间线
  listTimeline: (projectId) => api.get(`/projects/${projectId}/timeline`),
  createTimelineEvent: (projectId, data) => api.post(`/projects/${projectId}/timeline`, data),
  updateTimelineEvent: (projectId, eventId, data) => api.put(`/projects/${projectId}/timeline/${eventId}`, data),
  deleteTimelineEvent: (projectId, eventId) => api.delete(`/projects/${projectId}/timeline/${eventId}`),
  // 角色
  listCharacters: (projectId) => api.get(`/projects/${projectId}/characters`),
  createCharacter: (projectId, data) => api.post(`/projects/${projectId}/characters`, data),
  updateCharacter: (projectId, charId, data) => api.put(`/projects/${projectId}/characters/${charId}`, data),
  deleteCharacter: (projectId, charId) => api.delete(`/projects/${projectId}/characters/${charId}`),
}

// 流式写入
export async function writeChapterStream(chapterId, scenePlan, onChunk, onDone) {
  const params = scenePlan ? { scene_plan: JSON.stringify(scenePlan) } : {}
  const response = await fetch(`/api/ai/write-stream/${chapterId}?${new URLSearchParams(params)}`, {
    method: 'POST',
  })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const text = decoder.decode(value)
    const lines = text.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (data.done) {
            onDone?.(data)
          } else if (data.content) {
            onChunk?.(data.content)
          }
        } catch {}
      }
    }
  }
}

export default api
