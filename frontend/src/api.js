import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

export const getCases = (params = {}) =>
  api.get('/cases', { params }).then((r) => r.data)

export const getCase = (id) => api.get(`/cases/${id}`).then((r) => r.data)

export const analyzeCase = (id) =>
  api.post(`/cases/${id}/analyze`).then((r) => r.data)

export const approveCase = (id, note) =>
  api.post(`/cases/${id}/approve`, { note }).then((r) => r.data)

export const rejectCase = (id, reason) =>
  api.post(`/cases/${id}/reject`, { reason }).then((r) => r.data)

export const getDisputes = () => api.get('/disputes').then((r) => r.data)

export const getDashboard = () =>
  api.get('/analytics/dashboard').then((r) => r.data)

export default api
