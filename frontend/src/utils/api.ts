/**
 * API utility — axios instance with JWT auth interceptors.
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

function getStoredAccessToken(): string | null {
  const directToken = localStorage.getItem('access_token')
  if (directToken) return directToken

  try {
    const persistedAuth = JSON.parse(localStorage.getItem('kissanflow-auth') || '{}') as {
      state?: { accessToken?: string | null }
    }
    return persistedAuth.state?.accessToken || null
  } catch {
    return null
  }
}

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Attach JWT token to every request
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getStoredAccessToken()
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 — clear auth and redirect to login
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('kissanflow-auth')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const res = await api.get<ApiResponse<T>>(url, { params })
  if (!res.data.success) throw new Error(res.data.error ?? 'Request failed')
  return res.data.data as T
}

export async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await api.post<ApiResponse<T>>(url, body)
  if (!res.data.success) throw new Error(res.data.error ?? 'Request failed')
  return res.data.data as T
}

export async function put<T>(url: string, body?: unknown): Promise<T> {
  const res = await api.put<ApiResponse<T>>(url, body)
  if (!res.data.success) throw new Error(res.data.error ?? 'Request failed')
  return res.data.data as T
}

export async function del<T>(url: string): Promise<T> {
  const res = await api.delete<ApiResponse<T>>(url)
  if (!res.data.success) throw new Error(res.data.error ?? 'Request failed')
  return res.data.data as T
}
