import axios, { AxiosError, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage, ElNotification } from 'element-plus'

export const TOKEN_KEY = 'difu.access_token'
export const REFRESH_KEY = 'difu.refresh_token'
const CONFLICT_EVENT = 'difu:conflict'

export interface ApiEnvelope<T = unknown> {
  code: number
  msg?: string
  data?: T
  timestamp?: string
}

export class BizError extends Error {
  code: number
  data: unknown
  constructor(code: number, msg: string, data?: unknown) {
    super(msg)
    this.name = 'BizError'
    this.code = code
    this.data = data
  }
}

export const getToken = (): string => localStorage.getItem(TOKEN_KEY) || ''
export const setTokens = (access: string, refresh?: string): void => {
  localStorage.setItem(TOKEN_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}
export const clearTokens = (): void => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

/** 409 冲突时提取后端提示中的「可用动作」清单 */
export function parseAllowedActions(msg: string): string[] {
  const matched = /可用动作[：:]\s*(.+)$/.exec(msg || '')
  if (!matched) return []
  return matched[1]
    .split(/[、,，]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

export interface ConflictDetail {
  msg: string
  actions: string[]
}
export const CONFLICT_EVT = CONFLICT_EVENT
export function onConflict(handler: (detail: ConflictDetail) => void): () => void {
  const listener = (e: Event) => handler((e as CustomEvent<ConflictDetail>).detail)
  window.addEventListener(CONFLICT_EVENT, listener)
  return () => window.removeEventListener(CONFLICT_EVENT, listener)
}

let redirecting = false
function toLogin(): void {
  if (redirecting) return
  redirecting = true
  clearTokens()
  const here = window.location.pathname + window.location.search
  if (!here.startsWith('/login')) {
    window.location.assign(`/login?redirect=${encodeURIComponent(here)}`)
  }
  window.setTimeout(() => (redirecting = false), 1200)
}

function handleBizError(code: number, msg: string): void {
  switch (code) {
    case 401:
      ElMessage.closeAll()
      ElMessage.error('阴司通行令已失效，请重新过鬼门关')
      toLogin()
      break
    case 403:
      ElNotification({
        title: '阴律不容',
        message: msg || '此令无权动用该项事务',
        type: 'error',
        duration: 4000,
      })
      break
    case 409: {
      const actions = parseAllowedActions(msg)
      const actionHtml = actions.length
        ? `<div style="margin-top:6px;color:#c9a227">此刻可行之令：${actions.join(' · ')}</div>`
        : ''
      ElNotification({
        title: '状态流转非法',
        dangerouslyUseHTMLString: true,
        message: `<div>${msg || '当前状态不允许该动作'}</div>${actionHtml}`,
        type: 'warning',
        duration: 6500,
      })
      window.dispatchEvent(new CustomEvent(CONFLICT_EVENT, { detail: { msg, actions } }))
      break
    }
    case 429:
      ElMessage.error(msg || '操作过于频繁，请稍后再试')
      break
    case 404:
      ElMessage.warning(msg || '查无此物')
      break
    default:
      ElMessage.error(msg || `冥府事务处理失败（${code}）`)
  }
}

const instance = axios.create({
  baseURL: '/api/v1',
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

instance.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

instance.interceptors.response.use(
  (response: AxiosResponse) => {
    if (response.config.responseType === 'blob') return response
    const body = response.data as ApiEnvelope
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data as never
      handleBizError(body.code, body.msg || '')
      return Promise.reject(new BizError(body.code, body.msg || '', body.data))
    }
    return body as never
  },
  (error: AxiosError<ApiEnvelope>) => {
    if (!error.response) {
      ElMessage.error('幽冥链路中断，请确认后台服务（127.0.0.1:8000）是否在线')
      return Promise.reject(error)
    }
    const body = error.response.data
    const code = body?.code ?? error.response.status
    handleBizError(code, body?.msg || `请求失败（${error.response.status}）`)
    return Promise.reject(new BizError(code, body?.msg || '', body?.data))
  },
)

export const http = {
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.get(url, config) as unknown as Promise<T>
  },
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return instance.post(url, data, config) as unknown as Promise<T>
  },
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return instance.put(url, data, config) as unknown as Promise<T>
  },
  del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.delete(url, config) as unknown as Promise<T>
  },
}

export default http
