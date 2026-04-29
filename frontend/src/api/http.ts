import axios from 'axios'

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
export const useMockApi = import.meta.env.VITE_USE_MOCK_API !== 'false'

export const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 180_000,
  headers: {
    'Content-Type': 'application/json',
  },
})
