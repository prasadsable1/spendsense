import axios from 'axios'

const configuredApiUrl = import.meta.env.VITE_API_URL
if (import.meta.env.PROD && !configuredApiUrl) {
  throw new Error('VITE_API_URL must be configured for a production build.')
}

const apiBaseUrl = configuredApiUrl || '/api'

export const apiDocsUrl = new URL(
  '/docs',
  new URL(apiBaseUrl, window.location.origin),
).toString()

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('spendsense_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(undefined, (error) => {
  if (error.response?.status === 401 && sessionStorage.getItem('spendsense_token')) {
    sessionStorage.removeItem('spendsense_token')
    window.dispatchEvent(new Event('spendsense:auth-required'))
  }
  return Promise.reject(error)
})

export function errorMessage(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ')
  return error?.message || 'Something went wrong. Please try again.'
}

export default api
