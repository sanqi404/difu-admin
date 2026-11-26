import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as api from '@/api'
import { clearTokens, getToken, setTokens } from '@/api/http'
import type { MenuNode, Profile } from '@/api/types'

const MENU_CACHE_KEY = 'difu.menus'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(getToken())
  const profile = ref<Profile | null>(null)
  const permissions = ref<string[]>([])
  const menus = ref<MenuNode[]>([])
  const isSuper = ref(false)
  const dataScope = ref('SELF')
  const loaded = ref(false)

  const isLogged = computed(() => Boolean(token.value))
  const roleName = computed(() => profile.value?.role_name || '冥府游魂')
  const dutyTitle = computed(() => profile.value?.title || profile.value?.role_name || '待诏值司')
  const regionName = computed(() => profile.value?.region || '—')

  async function signIn(payload: {
    username: string
    password: string
    captcha_id: string
    captcha_code: string
  }) {
    const res = await api.login(payload)
    token.value = res.access_token
    setTokens(res.access_token, res.refresh_token)
    profile.value = res.profile
    permissions.value = res.profile.permissions || []
    isSuper.value = res.profile.is_super
    dataScope.value = res.profile.data_scope
    await loadMenus()
    loaded.value = true
    return res.profile
  }

  async function loadMenus() {
    const res = await api.fetchMenus()
    menus.value = res?.items || []
    localStorage.setItem(MENU_CACHE_KEY, JSON.stringify(menus.value))
    return menus.value
  }

  /** 刷新页面后恢复会话：profile + 权限 + 菜单 */
  async function hydrate() {
    if (!token.value) return false
    const [p, perm] = await Promise.all([api.fetchProfile(), api.fetchPermissions()])
    profile.value = p
    permissions.value = perm.codes || []
    isSuper.value = perm.is_super
    dataScope.value = perm.data_scope
    await loadMenus()
    loaded.value = true
    return true
  }

  function hasPerm(code?: string | string[]): boolean {
    if (!code) return true
    if (isSuper.value || permissions.value.includes('*')) return true
    const need = Array.isArray(code) ? code : [code]
    return need.some((c) => permissions.value.includes(c))
  }

  function reset() {
    token.value = ''
    profile.value = null
    permissions.value = []
    menus.value = []
    isSuper.value = false
    loaded.value = false
    clearTokens()
    localStorage.removeItem(MENU_CACHE_KEY)
  }

  async function signOut() {
    try {
      await api.logout()
    } catch {
      /* 令牌可能已失效，忽略 */
    } finally {
      reset()
    }
  }

  return {
    token,
    profile,
    permissions,
    menus,
    isSuper,
    dataScope,
    loaded,
    isLogged,
    roleName,
    dutyTitle,
    regionName,
    signIn,
    signOut,
    hydrate,
    loadMenus,
    hasPerm,
    reset,
  }
})
