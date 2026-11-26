/**
 * 移动端统一 HTTP 封装
 * - 后端统一响应体 { code, msg, data, timestamp }，code === 0 视为成功，直接解包 data
 * - 401：清理令牌并跳转登录；code !== 0：抛出 BizError 并弹出 Vant Toast
 * - 令牌与 PC 端共用同一 localStorage 键，便于调试时相互识别
 */
import axios, { type AxiosError, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { showFailToast } from 'vant'

export const TOKEN_KEY = 'difu.access_token'
export const REFRESH_KEY = 'difu.refresh_token'

export interface ApiEnvelope<T> {
  code: number
  msg?: string
  data?: T
  timestamp?: string
}

export class BizError extends Error {
  code: number
  data: unknown

  constructor(code: number, message: string, data?: unknown) {
    super(message)
    this.name = 'BizError'
    this.code = code
    this.data = data
  }
}

export function getToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setTokens(access: string, refresh?: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  } catch {
    /* 忽略隐私模式写入失败 */
  }
}

export function clearTokens(): void {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  } catch {
    /* noop */
  }
}

// 由 router 注册未授权回调，避免 http <-> router 循环依赖
let unauthorizedHandler: (() => void) | null = null

export function onUnauthorized(handler: () => void): void {
  unauthorizedHandler = handler
}

let redirecting = false

function toLogin(): void {
  clearTokens()
  if (redirecting) return
  redirecting = true
  unauthorizedHandler?.()
  window.setTimeout(() => {
    redirecting = false
  }, 1200)
}

function notify(message: string): void {
  showFailToast({
    message: message || '幽冥线路繁忙，请稍后再试',
    duration: 2200,
  })
}

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response: AxiosResponse<ApiEnvelope<unknown>>) => {
    const body = response.data
    // 非统一响应体（如二进制/纯文本）原样返回
    if (!body || typeof body !== 'object' || typeof body.code !== 'number') {
      return response.data as never
    }
    if (body.code === 0) {
      return (body.data ?? null) as never
    }
    if (body.code === 401) {
      notify(body.msg || '令牌失效，请重新登录')
      toLogin()
    } else {
      notify(body.msg || '操作未通过')
    }
    throw new BizError(body.code, body.msg || '操作未通过', body.data)
  },
  (error: AxiosError<ApiEnvelope<unknown>>) => {
    const status = error.response?.status
    const body = error.response?.data
    const message = body?.msg || error.message || '网络异常'

    if (status === 401) {
      notify(message || '令牌失效，请重新登录')
      toLogin()
      throw new BizError(401, message)
    }
    if (status === 403) {
      notify(message || '当前身份无权访问')
      throw new BizError(403, message)
    }
    notify(message)
    throw new BizError(status ?? -1, message)
  },
)

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  return (await http.request<unknown, T>(config)) as T
}

export const api = {
  get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    return request<T>({ url, method: 'get', params })
  },
  post<T>(url: string, data?: unknown): Promise<T> {
    return request<T>({ url, method: 'post', data })
  },
  put<T>(url: string, data?: unknown): Promise<T> {
    return request<T>({ url, method: 'put', data })
  },
  delete<T>(url: string): Promise<T> {
    return request<T>({ url, method: 'delete' })
  },
}

export default api
