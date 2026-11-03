import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export const apiDocsUrl = new URL('/docs', apiBaseUrl).toString()

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
})

export function errorMessage(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ')
  return error?.message || 'Something went wrong. Please try again.'
}

export default api
