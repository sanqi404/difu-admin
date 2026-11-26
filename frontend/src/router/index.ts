import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'


const businessRoutes: RouteRecordRaw[] = [
  {
    path: '/soul/list',
    name: 'SoulList',
    component: () => import('@/views/soul/SoulListView.vue'),
    meta: { title: '亡魂主档', menu: 'soul:list', perm: 'soul:view' },
  },
  { path: '/soul/flow', name: 'SoulFlow', component: () => import('@/views/flow/SoulFlowView.vue'), meta: { title: '流转台账', menu: 'soul:flow', perm: 'soul:view' } },
  { path: '/life-book/list', name: 'LifeBookList', component: () => import('@/views/lifebook/LifeBookListView.vue'), meta: { title: '生死簿流水', menu: 'lifebook:list', perm: 'lifebook:view' } },
  { path: '/life-book/review', name: 'LifeBookReview', component: () => import('@/views/lifebook/LifeBookListView.vue'), meta: { title: '生死簿待复核', menu: 'lifebook:review', perm: 'lifebook:review' } },
  { path: '/summon/list', name: 'SummonList', component: () => import('@/views/summon/SummonListView.vue'), meta: { title: '勾魂工单', menu: 'summon:list', perm: 'summon:view' } },
  { path: '/summon/dispatch', name: 'SummonDispatch', component: () => import('@/views/summon/SummonListView.vue'), meta: { title: '派单调度', menu: 'summon:dispatch', perm: 'summon:view' } },
  { path: '/gate/verify', name: 'GateVerify', component: () => import('@/views/gate/GateVerifyView.vue'), meta: { title: '鬼门关验引', menu: 'gate:verify', perm: 'doc:verify' } },
  { path: '/lost/record', name: 'LostRecord', component: () => import('@/views/lost/LostRecordView.vue'), meta: { title: '迷魂殿录供', menu: 'lost:record', perm: 'soul:view' } },
  { path: '/lost/karma', name: 'KarmaMirror', component: () => import('@/views/karma/KarmaMirrorView.vue'), meta: { title: '孽镜台评分', menu: 'lost:karma', perm: 'karma:score' } },
  { path: '/trial/list', name: 'TrialList', component: () => import('@/views/trial/TrialListView.vue'), meta: { title: '十殿审判', menu: 'trial:list', perm: 'trial:view' } },
  { path: '/trial/court', name: 'TrialCourt', component: () => import('@/views/trial/TrialCourtView.vue'), meta: { title: '十殿会审', menu: 'trial:court', perm: 'trial:view' } },
  { path: '/punishment/list', name: 'PunishmentList', component: () => import('@/views/punishment/PunishmentListView.vue'), meta: { title: '十八层地狱', menu: 'punishment:list', perm: 'punishment:view' } },
  { path: '/reincarnation/list', name: 'ReincList', component: () => import('@/views/reincarnation/ReincarnationView.vue'), meta: { title: '轮回司', menu: 'reincarnation:list', perm: 'reincarnation:view' } },
  { path: '/reincarnation/soup', name: 'SoupDesk', component: () => import('@/views/reincarnation/ReincarnationView.vue'), meta: { title: '轮回司 · 孟婆汤', menu: 'reincarnation:soup', perm: 'reincarnation:soup' } },
  { path: '/city-god/list', name: 'CityGodList', component: () => import('@/views/citygod/CityGodView.vue'), meta: { title: '城隍网点', menu: 'citygod:list', perm: 'citygod:view' } },
  { path: '/document/list', name: 'DocumentList', component: () => import('@/views/document/DocumentView.vue'), meta: { title: '文书台账', menu: 'document:list', perm: 'doc:view' } },
  { path: '/stats', name: 'StatsBoard', component: () => import('@/views/StatsView.vue'), meta: { title: '统计看板', menu: 'stats', perm: 'stats:view' } },
  { path: '/system/officer', name: 'OfficerList', component: () => import('@/views/system/OfficerView.vue'), meta: { title: '鬼差账号', menu: 'system:officer', perm: 'officer:view' } },
  { path: '/system/role', name: 'RoleList', component: () => import('@/views/system/RoleView.vue'), meta: { title: '角色权限', menu: 'system:role', perm: 'role:view' } },
  { path: '/system/menu', name: 'MenuList', component: () => import('@/views/system/MenuView.vue'), meta: { title: '菜单配置', menu: 'system:menu', perm: 'menu:view' } },
  { path: '/system/permission', name: 'PermissionList', component: () => import('@/views/system/PermissionView.vue'), meta: { title: '权限点', menu: 'system:permission', perm: 'permission:view' } },
  { path: '/system/audit', name: 'AuditLogList', component: () => import('@/views/system/AuditView.vue'), meta: { title: '阴律日志', menu: 'system:audit', perm: 'audit:view' } },
]

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, title: '鬼门关' },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '酆都城舆图', menu: 'dashboard' },
      },
      ...businessRoutes,
      {
        path: '/403',
        name: 'Forbidden',
        component: () => import('@/views/ForbiddenView.vue'),
        meta: { title: '阴律闭门' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { public: true, title: '黄泉无路' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const title = (to.meta.title as string) || ''
  document.title = title ? `${title} · 地府生死铺` : '地府生死铺 · 幽冥后台'

  if (to.meta.public) {
    if (to.path === '/login' && auth.isLogged) return { path: '/dashboard' }
    return true
  }

  if (!auth.isLogged) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (!auth.loaded) {
    try {
      await auth.hydrate()
    } catch {
      auth.reset()
      ElMessage.error('阴司会籍校验未过，请重新过鬼门关')
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  const needPerm = to.meta.perm as string | undefined
  if (needPerm && !auth.hasPerm(needPerm)) return { path: '/403' }

  return true
})

export default router
