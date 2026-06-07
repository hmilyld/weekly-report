import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 globally → redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

// ─── Auth ──────────────────────────────────────────────
export const getAuthStatus = () => api.get('/auth/status')

export const setupAccount = (username, password) => api.post('/auth/setup', { username, password })

export const login = (username, password) => api.post('/auth/login', { username, password })

export const changePassword = (newPassword) =>
  api.post('/auth/change-password', { new_password: newPassword })

// ─── Daily Reports ─────────────────────────────────────
export const getDailyReportsWeek = (weekStart) => api.get(`/daily/week/${weekStart}`)

export const getDailyReportsRange = (startDate, endDate) =>
  api.get(`/daily?start_date=${startDate}&end_date=${endDate}`)

export const saveDailyReport = (date, content) => api.post('/daily', { date, content })

export const deleteDailyReport = (date) => api.delete(`/daily/${date}`)

// ─── Weekly Reports ────────────────────────────────────
export const getWeeklyReport = (weekStart) => api.get(`/weekly/${weekStart}`)

export const generateWeeklyReport = (weekStart) => api.post(`/weekly/${weekStart}`)

export const updateWeeklyReport = (weekStart, content) =>
  api.put(`/weekly/${weekStart}`, { content })

// ─── Config ────────────────────────────────────────────
export const getConfig = () => api.get('/config')

export const updateConfig = (data) => api.put('/config', data)

export const testConnection = () => api.post('/config/test')

// ─── API Tokens ────────────────────────────────────────
export const getTokens = () => api.get('/tokens')

export const createToken = (name = 'default') => api.post('/tokens', { name })

export const deleteToken = (tokenId) => api.delete(`/tokens/${tokenId}`)

// ─── Tasks ─────────────────────────────────────────────
export const getTasks = () => api.get('/tasks')

export const getCompletedTasks = (offset = 0, limit = 20) =>
  api.get(`/tasks/completed?offset=${offset}&limit=${limit}`)

export const createTask = (content, deadline = null) =>
  api.post('/tasks', { content, deadline })

export const updateTask = (taskId, data) => api.put(`/tasks/${taskId}`, data)

export const deleteTask = (taskId) => api.delete(`/tasks/${taskId}`)

export default api
