import { del, get, patch, post, put, upload } from './api'
import { useAuthStore } from '@/stores/auth'

const apiBase = '/api/v1'

const getAccessToken = () => {
  try {
    const authStore = useAuthStore()
    return authStore.token || localStorage.getItem('token') || ''
  } catch {
    return localStorage.getItem('token') || ''
  }
}

async function postStream(path, payload = {}, options = {}) {
  const headers = new Headers(options.headers || {})
  headers.set('Accept', 'text/event-stream')
  headers.set('Content-Type', 'application/json')

  const accessToken = getAccessToken()
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  return fetch(`${apiBase}${path}`, {
    method: 'POST',
    credentials: 'same-origin',
    body: JSON.stringify(payload || {}),
    ...options,
    headers
  })
}

export const canvasService = {
  list(params = {}) {
    return get('/canvas-documents', { params })
  },

  create(payload) {
    return post('/canvas-documents', payload)
  },

  get(documentId) {
    return get(`/canvas-documents/${documentId}`)
  },

  getLite(documentId) {
    return get(`/canvas-documents/${documentId}`, { params: { mode: 'lite' } })
  },

  getModelCatalog() {
    return get('/canvas-model-catalog')
  },

  update(documentId, payload) {
    return patch(`/canvas-documents/${documentId}`, payload)
  },

  remove(documentId) {
    return del(`/canvas-documents/${documentId}`)
  },

  getGraph(documentId) {
    return get(`/canvas-documents/${documentId}/graph`)
  },

  saveGraph(documentId, payload) {
    return put(`/canvas-documents/${documentId}/graph`, payload)
  },

  createItem(documentId, payload) {
    return post(`/canvas-documents/${documentId}/items`, payload)
  },

  getItem(documentId, itemId) {
    return get(`/canvas-documents/${documentId}/items/${itemId}`)
  },

  updateItem(documentId, itemId, payload) {
    return patch(`/canvas-documents/${documentId}/items/${itemId}`, payload)
  },

  deleteItem(documentId, itemId) {
    return del(`/canvas-documents/${documentId}/items/${itemId}`)
  },

  getItemPreviews(documentId, itemIds = []) {
    return post(`/canvas-documents/${documentId}/items/previews`, { item_ids: itemIds })
  },

  createConnection(documentId, payload) {
    return post(`/canvas-documents/${documentId}/connections`, payload)
  },

  deleteConnection(documentId, connectionId) {
    return del(`/canvas-documents/${documentId}/connections/${connectionId}`)
  },

  getVideoTask(documentId, itemId, taskId) {
    return get(`/canvas-documents/${documentId}/items/${itemId}/video-tasks/${taskId}`)
  },

  uploadVideo(documentId, itemId, formData, config = {}) {
    return upload(`/canvas-documents/${documentId}/items/${itemId}/upload-video`, formData, config)
  },

  generateText(itemId, payload = {}) {
    return post(`/canvas-items/${itemId}/generate-text`, payload)
  },

  generateTextStream(itemId, payload = {}, options = {}) {
    return postStream(`/canvas-items/${itemId}/generate-text/stream`, payload, options)
  },

  generateImage(itemId, payload = {}) {
    return post(`/canvas-items/${itemId}/generate-image`, payload)
  },

  generateImageStream(itemId, payload = {}, options = {}) {
    return postStream(`/canvas-items/${itemId}/generate-image/stream`, payload, options)
  },

  generateVideo(itemId, payload = {}) {
    return post(`/canvas-items/${itemId}/generate-video`, payload)
  },

  generateVideoStream(itemId, payload = {}, options = {}) {
    return postStream(`/canvas-items/${itemId}/generate-video/stream`, payload, options)
  },

  listGenerations(itemId, params = {}) {
    return get(`/canvas-items/${itemId}/generations`, { params })
  },

  applyGeneration(itemId, generationId) {
    return post(`/canvas-items/${itemId}/generations/${generationId}/apply`)
  }
}

export default canvasService
