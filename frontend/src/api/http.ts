import axios from 'axios'

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || ''
const rawUseMockApi = import.meta.env.VITE_USE_MOCK_API

function resolveUseMockApi() {
  if (rawUseMockApi === 'true') {
    return true
  }

  if (rawUseMockApi === 'false') {
    return false
  }

  // Safety default:
  // - local dev without env: mock ON
  // - production build without env: mock OFF
  return import.meta.env.DEV
}

export const useMockApi = resolveUseMockApi()

export const http = axios.create({
  baseURL: apiBaseUrl,
  timeout: 180_000,
  headers: {
    'Content-Type': 'application/json',
  },
})
