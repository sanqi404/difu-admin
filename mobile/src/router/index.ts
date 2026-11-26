import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'

import { onUnauthorized } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    /** 无需登录即可访问 */
    public?: boolean
    /** 需要的权限点，缺省表示仅需登录 */
    perm?: string | string[]
    /** 归属的底部 Tab */
    tab?: 'dashboard' | 'inbox' | 'messages' | 'me'
  }
}

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '鬼门关 · 登录', public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/TabLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '工作台', tab: 'dashboard' },
      },
      {
        path: 'inbox',
        name: 'inbox',
        component: () => import('@/views/InboxView.vue'),
        meta: { title: '待办中心', tab: 'inbox' },
      },
      {
        path: 'messages',
        name: 'messages',
        component: () => import('@/views/MessagesView.vue'),
        meta: { title: '消息中心', tab: 'messages' },
      },
      {
        path: 'me',
        name: 'me',
        component: () => import('@/views/ProfileView.vue'),
        meta: { title: '我的', tab: 'me' },
      },
    ],
  },
  {
    path: '/approval/:id(\\d+)',
    name: 'approval-detail',
    component: () => import('@/views/ApprovalDetailView.vue'),
    meta: { title: '审批详情' },
  },
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('@/views/ForbiddenView.vue'),
    meta: { title: '无权通行', public: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/ForbiddenView.vue'),
    meta: { title: '迷途忘川', public: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0, left: 0 }),
})

// 401 统一由 HTTP 层回调，这里只负责跳转，避免循环依赖
onUnauthorized(() => {
  const current = router.currentRoute.value
  if (current.name === 'login') return
  void router.replace({ name: 'login', query: { redirect: current.fullPath } })
})

function loginTarget(to: RouteLocationNormalized) {
  return {
    name: 'login' as const,
    query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : {},
  }
}

router.beforeEach(async (to) => {
  document.title = to.meta.title ? `${to.meta.title} · 幽冥政务` : '幽冥政务 · 移动端'

  if (to.meta.public) return true

  const auth = useAuthStore()
  if (!auth.token) return loginTarget(to)

  if (!auth.loaded) {
    const ok = await auth.hydrate()
    if (!ok) return loginTarget(to)
  }

  const need = to.meta.perm
  if (need && !auth.hasPerm(need)) {
    return {
      name: 'forbidden',
      query: { from: to.fullPath, need: Array.isArray(need) ? need.join(' / ') : need },
    }
  }

  return true
})

export default router
