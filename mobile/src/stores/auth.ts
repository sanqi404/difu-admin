/** 登录态：令牌持久化、鬼差身份、权限点、登出 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  fetchPermissions,
  fetchProfile,
  login as loginApi,
  logout as logoutApi,
} from '@/api/auth'
import { clearTokens, getToken, setTokens } from '@/api/http'
import type { LoginPayload, OfficerProfile } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(getToken())
  const profile = ref<OfficerProfile | null>(null)
  const perms = ref<string[]>([])
  const isSuper = ref(false)
  const dataScope = ref('')
  const loaded = ref(false)
  const loading = ref(false)

  const isLogged = computed(() => !!token.value)
  const displayName = computed(() => profile.value?.real_name || profile.value?.username || '无名鬼差')
  const roleName = computed(() => profile.value?.role_name || profile.value?.role_code || '未授职')
  const dutyTitle = computed(() => profile.value?.title || '')
  const regionName = computed(() => profile.value?.region || '')
  /** 身份徽章文案：职衔 · 角色 */
  const badgeText = computed(() => {
    const parts = [dutyTitle.value, roleName.value].filter(Boolean)
    return parts.length ? parts.join(' · ') : '待授职'
  })

  function hasPerm(code?: string | string[], mode: 'any' | 'all' = 'any'): boolean {
    if (!code) return true
    if (isSuper.value || perms.value.includes('*')) return true
    const need = Array.isArray(code) ? code : [code]
    if (!need.length) return true
    return mode === 'all'
      ? need.every((item) => perms.value.includes(item))
      : need.some((item) => perms.value.includes(item))
  }

  async function loadIdentity(): Promise<void> {
    const [me, perm] = await Promise.all([fetchProfile(), fetchPermissions()])
    profile.value = me
    perms.value = perm.codes || me.permissions || []
    isSuper.value = perm.is_super ?? Boolean(me.is_super)
    dataScope.value = perm.data_scope || me.data_scope || ''
    loaded.value = true
  }

  async function signIn(payload: LoginPayload): Promise<void> {
    loading.value = true
    try {
      const res = await loginApi(payload)
      token.value = res.access_token
      setTokens(res.access_token, res.refresh_token)
      await loadIdentity()
    } catch (err) {
      reset()
      throw err
    } finally {
      loading.value = false
    }
  }

  /** 冷启动静默恢复身份；失败即清空登录态 */
  async function hydrate(): Promise<boolean> {
    if (!token.value) return false
    if (loaded.value) return true
    try {
      await loadIdentity()
      return true
    } catch {
      reset()
      return false
    }
  }

  function reset(): void {
    token.value = ''
    profile.value = null
    perms.value = []
    isSuper.value = false
    dataScope.value = ''
    loaded.value = false
    clearTokens()
  }

  async function signOut(): Promise<void> {
    try {
      await logoutApi()
    } catch {
      // 令牌可能已过期，忽略服务端登出失败
    } finally {
      reset()
    }
  }

  return {
    token,
    profile,
    perms,
    isSuper,
    dataScope,
    loaded,
    loading,
    isLogged,
    displayName,
    roleName,
    dutyTitle,
    regionName,
    badgeText,
    hasPerm,
    signIn,
    signOut,
    hydrate,
    loadIdentity,
    reset,
  }
})
