/** 认证相关接口（与 PC 端 frontend/src/api/index.ts 完全对齐） */
import api from './http'
import type { CaptchaData, LoginPayload, LoginResult, OfficerProfile, PermissionResult } from './types'

/** 获取图形验证码：返回 captcha_id 与 base64 图片 */
export function fetchCaptcha() {
  return api.get<CaptchaData>('/auth/captcha')
}

/** 账号密码 + 图形验证码登录 */
export function login(payload: LoginPayload) {
  return api.post<LoginResult>('/auth/login', payload)
}

/** 当前登录鬼差信息 */
export function fetchProfile() {
  return api.get<OfficerProfile>('/auth/profile')
}

/** 当前角色权限点 */
export function fetchPermissions() {
  return api.get<PermissionResult>('/auth/permissions')
}

/** 登出（令牌加入黑名单） */
export function logout() {
  return api.post<unknown>('/auth/logout')
}
