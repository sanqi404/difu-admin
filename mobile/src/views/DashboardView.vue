<script setup lang="ts">
/** 工作台：按角色渲染欢迎语、统计瓦片、权限宫格与近期待办 */
import { computed, onActivated, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'

import { approvalsApi, fetchSummonOrders, messagesApi } from '@/api/mobile'
import type { ApprovalItem } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { bizTone, remainTime, statusTone } from '@/utils/format'

defineOptions({ name: 'DashboardView' })

const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const loading = ref(false)
const todoItems = ref<ApprovalItem[]>([])
const todoTotal = ref(0)
const orderTotal = ref(0)
const unreadTotal = ref(0)
const loadError = ref('')

// 每 30 秒刷新一次倒计时文案
const tick = ref(0)
let timer: number | undefined

const CHINESE_HOURS = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

const greet = computed(() => {
  const hour = new Date().getHours()
  const idx = Math.floor(((hour + 1) % 24) / 2)
  const period = hour < 5 ? '夜半' : hour < 11 ? '晨起' : hour < 13 ? '日中' : hour < 18 ? '午后' : '入夜'
  return `${period}${CHINESE_HOURS[idx]}时安好`
})

const sealChar = computed(() => (auth.displayName || '鬼').slice(0, 1))

interface QuickEntry {
  key: string
  label: string
  icon: string
  to?: string
  perm?: string
  hint?: string
}

const quickEntries: QuickEntry[] = [
  { key: 'inbox', label: '待我审批', icon: 'todo-list-o', to: '/inbox' },
  { key: 'messages', label: '消息中心', icon: 'envelop-o', to: '/messages' },
  { key: 'me', label: '我的文牒', icon: 'manager-o', to: '/me' },
  { key: 'lifebook', label: '生死簿', icon: 'notes-o', perm: 'lifebook:view', hint: '生死簿台账将在后续版本开放' },
  { key: 'karma', label: '孽镜台', icon: 'aim', perm: 'karma:score', hint: '孽镜台评分将在后续版本开放' },
  { key: 'citygod', label: '城隍网点', icon: 'shop-o', perm: 'citygod:view', hint: '城隍网点将在后续版本开放' },
  { key: 'audit', label: '阴律日志', icon: 'records-o', perm: 'audit:view', hint: '阴律日志将在后续版本开放' },
]

const entries = computed(() => quickEntries.filter((item) => auth.hasPerm(item.perm)))

function openEntry(entry: QuickEntry): void {
  if (entry.hint) {
    showToast({ message: entry.hint, duration: 1600 })
    return
  }
  if (entry.to) void router.push(entry.to)
}

async function loadAll(): Promise<void> {
  if (loading.value) return
  loading.value = true
  loadError.value = ''
  try {
    const [todo, orders, unread] = await Promise.allSettled([
      approvalsApi.list({ scope: 'todo', page: 1, page_size: 5 }),
      fetchSummonOrders({ assignee_id: auth.profile?.id, page: 1, page_size: 1 }),
      messagesApi.unreadCount(),
    ])

    if (todo.status === 'fulfilled') {
      todoItems.value = todo.value.items || []
      todoTotal.value = todo.value.meta?.total ?? 0
      app.setTodoCount(todoTotal.value)
    }
    if (orders.status === 'fulfilled') {
      orderTotal.value = orders.value.meta?.total ?? 0
    }
    if (unread.status === 'fulfilled') {
      unreadTotal.value = unread.value.unread ?? 0
      app.setUnreadCount(unreadTotal.value)
    }
    if (todo.status === 'rejected' && unread.status === 'rejected') {
      loadError.value = '幽冥线路暂时不通，下拉可重试'
    }
  } finally {
    loading.value = false
  }
}

function remainText(deadline?: string | null): string {
  // 读取 tick 让倒计时随定时器重算
  void tick.value
  const info = remainTime(deadline)
  return info.none ? '无时限' : info.text
}

function remainClass(deadline?: string | null): string {
  void tick.value
  const info = remainTime(deadline)
  if (info.none) return 'm-faint'
  return info.overdue ? 'm-fire' : info.urgent ? 'm-gold' : 'm-muted'
}

function goDetail(item: ApprovalItem): void {
  void router.push({ name: 'approval-detail', params: { id: String(item.id) } })
}

onMounted(() => {
  void loadAll()
  timer = window.setInterval(() => {
    tick.value += 1
  }, 30_000)
})

onActivated(() => {
  void loadAll()
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="m-page m-page--tabbar dash">
    <header class="dash__head">
      <div class="dash__head-main">
        <p class="dash__greet">
          {{ greet }}，<span class="dash__name m-serif">{{ auth.displayName }}</span>
        </p>
        <p class="dash__meta">
          <span class="m-badge">{{ auth.badgeText }}</span>
          <span v-if="auth.regionName" class="dash__region">{{ auth.regionName }}</span>
        </p>
      </div>
      <div class="dash__seal m-serif">{{ sealChar }}</div>
    </header>

    <section class="m-tiles dash__tiles">
      <button class="m-tile" type="button" @click="router.push('/inbox')">
        <span class="m-tile__value">{{ todoTotal }}</span>
        <span class="m-tile__label">待我审批</span>
      </button>
      <div class="m-tile">
        <span class="m-tile__value m-tile__value--teal">{{ orderTotal }}</span>
        <span class="m-tile__label">在办工单</span>
      </div>
      <button class="m-tile" type="button" @click="router.push('/messages')">
        <span class="m-tile__value m-tile__value--fire">{{ unreadTotal }}</span>
        <span class="m-tile__label">未读消息</span>
      </button>
    </section>

    <section class="m-card dash__quick">
      <div class="m-card__head">
        <span class="m-card__title">快捷入口</span>
        <span class="m-card__more">{{ entries.length }} 项可用</span>
      </div>
      <div class="m-grid">
        <button
          v-for="entry in entries"
          :key="entry.key"
          class="m-grid__item"
          type="button"
          @click="openEntry(entry)"
        >
          <span class="m-grid__icon"><van-icon :name="entry.icon" /></span>
          <span>{{ entry.label }}</span>
        </button>
      </div>
    </section>

    <section class="m-card dash__todo">
      <div class="m-card__head">
        <span class="m-card__title">近期待办</span>
        <button class="dash__more" type="button" @click="router.push('/inbox')">
          全部 <van-icon name="arrow" />
        </button>
      </div>

      <van-loading v-if="loading && !todoItems.length" class="dash__loading" size="18" vertical>
        正在查阅卷宗
      </van-loading>

      <div v-else-if="!todoItems.length" class="m-empty">
        {{ loadError || '当前无待审文书，可安心值守' }}
      </div>

      <ul v-else class="dash__list">
        <li
          v-for="item in todoItems"
          :key="item.id"
          class="dash__item"
          @click="goDetail(item)"
        >
          <div class="dash__item-top">
            <span class="m-badge" :class="`m-badge--${bizTone(item.biz_type)}`">{{ item.biz_type }}</span>
            <span class="m-badge m-badge--plain">{{ item.status }}</span>
          </div>
          <p class="dash__item-title">{{ item.title }}</p>
          <p v-if="item.summary" class="dash__item-summary">{{ item.summary }}</p>
          <div class="dash__item-foot">
            <span class="m-faint">呈报：{{ item.applicant_name || '—' }}</span>
            <span :class="remainClass(item.deadline_at)">{{ remainText(item.deadline_at) }}</span>
          </div>
        </li>
      </ul>
    </section>

    <p class="dash__foot m-faint">
      数据截至 {{ new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}
    </p>
  </div>
</template>

<style scoped lang="scss">
.dash__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 2px 14px;
}

.dash__head-main {
  min-width: 0;
}

.dash__greet {
  margin: 0;
  color: var(--m-text-0);
  font-size: 17px;
  letter-spacing: 0.04em;
}

.dash__name {
  color: var(--m-gold);
}

.dash__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0 0;
}

.dash__region {
  color: var(--m-text-2);
  font-size: 11px;
}

.dash__seal {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(201, 162, 39, 0.45);
  border-radius: 6px;
  color: var(--m-gold);
  font-size: 20px;
  background: rgba(201, 162, 39, 0.08);
  box-shadow: inset 0 0 12px rgba(201, 162, 39, 0.18);
}

.dash__tiles {
  margin-bottom: 12px;
}

.dash__quick {
  padding-bottom: 8px;
}

.dash__todo {
  margin-top: 10px;
}

.dash__more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
  border: 0;
  color: var(--m-text-2);
  font-size: 12px;
  background: transparent;
}

.dash__loading {
  padding: 18px 0;
  color: var(--m-text-2);
}

.dash__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.dash__item {
  padding: 11px 0;
  border-top: 1px dashed rgba(255, 255, 255, 0.07);
  transition: background 0.16s ease;

  &:first-child {
    border-top: 0;
    padding-top: 2px;
  }

  &:active {
    background: rgba(201, 162, 39, 0.06);
  }
}

.dash__item-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dash__item-title {
  margin: 7px 0 0;
  color: var(--m-text-0);
  font-size: 14px;
  line-height: 1.45;
}

.dash__item-summary {
  margin: 4px 0 0;
  display: -webkit-box;
  overflow: hidden;
  color: var(--m-text-2);
  font-size: 12px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.dash__item-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 7px;
  font-size: 11px;
}

.dash__foot {
  margin: 14px 0 0;
  text-align: center;
}
</style>
