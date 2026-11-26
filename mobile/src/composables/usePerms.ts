/** 权限判定组合式函数：与 PC 端 usePerms 行为一致 */
import { useAuthStore } from '@/stores/auth'

export interface PermChecker {
  hasPerm: (code?: string | string[], mode?: 'any' | 'all') => boolean
  auth: ReturnType<typeof useAuthStore>
}

export function usePerms(): PermChecker {
  const auth = useAuthStore()

  function hasPerm(code?: string | string[], mode: 'any' | 'all' = 'any'): boolean {
    return auth.hasPerm(code, mode)
  }

  return { hasPerm, auth }
}
