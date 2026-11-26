import { useAuthStore } from '@/stores/auth'

/**
 * 按钮级权限：模板中 v-if="perms.hasPerm('soul:create')"
 */
export function usePerms() {
  const auth = useAuthStore()

  const hasPerm = (code?: string | string[], mode: 'any' | 'all' = 'any'): boolean => {
    if (!code || (Array.isArray(code) && code.length === 0)) return true
    if (auth.isSuper || auth.permissions.includes('*')) return true
    const need = Array.isArray(code) ? code : [code]
    return mode === 'all'
      ? need.every((c) => auth.permissions.includes(c))
      : need.some((c) => auth.permissions.includes(c))
  }

  return { hasPerm, auth }
}
