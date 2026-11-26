<script setup lang="ts">
/**
 * 消息中心：全部 / 未读 / 紧急 三类筛选，分页加载。
 * 点击单条：标记已读 + 扣减全局未读数；若 biz_ref 指向审批单则跳转审批详情。
 */
import { computed, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast } from 'vant'
import { messagesApi } from '@/api/mobile'
import type { MessageItem } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { fromNow } from '@/utils/format'

defineOptions({ name: 'MessagesView' })

type FilterName = 'all' | 'unread' | 'urgent'

const FILTERS: { name: FilterName; label: string }[] = [
  { name: 'all', label: '全部' },
  { name: 'unread', label: '未读' },
  { name: 'urgent', label: '紧急' },
]

const router = useRouter()
const app = useAppStore()

const filter = ref<FilterName>('all')
const items = ref<MessageItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 15
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const errorText = ref('')
const marking = ref(false)
const tick = ref(0)

let timer: number | undefined

const unreadCount = computed(() => app.unreadCount)

const subText = computed(() => {
  if (filter.value === 'unread') return `共 ${total.value} 条未启封`
  if (filter.value === 'urgent') return `共 ${total.value} 条急报`
  return unreadCount.value > 0 ? `共 ${total.value} 条阴讯 · ${unreadCount.value} 条未读` : `共 ${total.value} 条阴讯`
})

function queryOf() {
  if (filter.value === 'unread') return { is_read: false }
  if (filter.value === 'urgent') return { type: '紧急通告' }
  return {}
}

async function fetchPage(reset = false): Promise<void> {
  if (loading.value) return
  loading.value = true
  if (reset) {
    page.value = 1
    finished.value = false
    errorText.value = ''
  }
  try {
    const res = await messagesApi.list({ ...queryOf(), page: page.value, page_size: pageSize })
    const list = res.items || []
    items.value = reset ? list : [...items.value, ...list]
    total.value = res.meta?.total ?? list.length
    page.value += 1
    finished.value = items.value.length >= total.value || list.length < pageSize
  } catch {
    errorText.value = '幽冥线路中断，请稍后重试'
    finished.value = true
  } finally {
    loading.value = false
  }
}

function onLoad(): void {
  void fetchPage(false)
}

async function onRefresh(): Promise<void> {
  refreshing.value = true
  try {
    await fetchPage(true)
    void app.refreshCounters()
  } finally {
    refreshing.value = false
  }
}

function switchFilter(name: FilterName): void {
  filter.value = name
}

watch(filter, () => {
  items.value = []
  total.value = 0
  finished.value = false
  void fetchPage(true)
})

/** 从 biz_ref 中解析审批单号，兼容 "approval:12" / "approval_request#12" / "12" */
function approvalIdOf(ref?: string | null): number | null {
  if (!ref) return null
  const hit = /(\d+)\s*$/.exec(ref.trim())
  if (!hit) return null
  if (/^\d+$/.test(ref.trim())) return Number(hit[1])
  return /approval|approve|request|shenpi/i.test(ref) ? Number(hit[1]) : null
}

async function openMessage(row: MessageItem): Promise<void> {
  if (!row.is_read) {
    row.is_read = true
    try {
      await messagesApi.read(row.id)
      app.decrementUnread()
    } catch {
      row.is_read = false
    }
  }
  const approvalId = approvalIdOf(row.biz_ref)
  if (approvalId) void router.push({ name: 'approval-detail', params: { id: String(approvalId) } })
}

async function onReadAll(): Promise<void> {
  if (marking.value) return
  marking.value = true
  try {
    const res = await messagesApi.readAll()
    const changed = res?.updated ?? 0
    items.value.forEach((row) => {
      row.is_read = true
    })
    app.setUnreadCount(0)
    showSuccessToast(changed > 0 ? `已启封 ${changed} 条` : '并无未读阴讯')
    if (filter.value === 'unread') void fetchPage(true)
  } catch {
    /* 错误提示由 http 层统一弹出 */
  } finally {
    marking.value = false
  }
}

function priorityClass(priority?: string | null): string {
  if (priority === '紧急') return 'msg__p--urgent'
  if (priority === '重要') return 'msg__p--important'
  return 'msg__p--normal'
}

function timeText(value?: string | null): string {
  void tick.value
  return fromNow(value)
}

onMounted(() => {
  void fetchPage(true)
  void app.refreshCounters()
  timer = window.setInterval(() => {
    tick.value += 1
  }, 30000)
})

onActivated(() => {
  void fetchPage(true)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="m-page m-page--tabbar msg">
    <header class="msg__head">
      <div class="msg__head-main">
        <h1 class="msg__title m-serif">消息中心</h1>
        <p class="msg__sub m-faint">{{ subText }}</p>
      </div>
      <button
        type="button"
        class="msg__readall"
        :disabled="marking || unreadCount <= 0"
        @click="onReadAll"
      >
        <van-icon name="eye-o" />
        <span>{{ marking ? '启封中' : '全部已读' }}</span>
      </button>
    </header>

    <van-tabs v-model:active="filter" class="msg__tabs" shrink @change="switchFilter">
      <van-tab v-for="item in FILTERS" :key="item.name" :name="item.name" :title="item.label" />
    </van-tabs>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <div class="msg__list">
        <div v-if="errorText && !items.length" class="m-empty">{{ errorText }}</div>

        <article
          v-for="row in items"
          :key="row.id"
          class="msg__card"
          :class="{ 'msg__card--unread': !row.is_read }"
          @click="openMessage(row)"
        >
          <div class="msg__card-top">
            <span class="m-badge">{{ row.type || '系统通知' }}</span>
            <span class="msg__p" :class="priorityClass(row.priority)">{{ row.priority || '普通' }}</span>
            <span v-if="!row.is_read" class="msg__dot" aria-label="未读" />
            <span class="msg__no m-mono">{{ timeText(row.created_at) }}</span>
          </div>

          <h2 class="msg__card-title">{{ row.title }}</h2>
          <p v-if="row.content" class="msg__card-body">{{ row.content }}</p>

          <div v-if="approvalIdOf(row.biz_ref)" class="msg__card-foot">
            <span class="msg__ref m-faint m-mono">{{ row.biz_ref }}</span>
            <span class="msg__go">查看详情 <van-icon name="arrow" /></span>
          </div>
        </article>

        <van-list
          v-if="items.length || !errorText"
          v-model:loading="loading"
          :finished="finished"
          :finished-text="items.length ? '阴讯已到底' : ''"
          :immediate-check="false"
          @load="onLoad"
        >
          <div v-if="!items.length && !loading" class="m-empty">此处空无一讯</div>
        </van-list>
      </div>
    </van-pull-refresh>
  </div>
</template>

<style scoped lang="scss">
.msg__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 4px 2px 10px;
}

.msg__head-main {
  min-width: 0;
}

.msg__title {
  margin: 0;
  color: var(--m-text-0);
  font-size: 20px;
  letter-spacing: 0.1em;
}

.msg__sub {
  margin: 5px 0 0;
}

.msg__readall {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--m-gold-line);
  border-radius: 14px;
  color: var(--m-gold-soft);
  font-size: 12px;
  background: rgba(201, 162, 39, 0.08);

  &:disabled {
    opacity: 0.4;
  }
}

.msg__tabs {
  margin: 0 -14px 8px;
  padding: 0 6px;
}

.msg__list {
  min-height: 40vh;
}

.msg__card {
  padding: 12px 13px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.008)), var(--m-ink-1);
  transition: border-color 0.16s ease;

  & + & {
    margin-top: 10px;
  }

  &:active {
    border-color: rgba(201, 162, 39, 0.4);
  }
}

.msg__card--unread {
  border-color: rgba(201, 162, 39, 0.28);
}

.msg__card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.msg__p {
  font-size: 11px;
  line-height: 1;
  padding: 3px 6px;
  border-radius: 4px;
  border: 1px solid transparent;
}

.msg__p--normal {
  color: var(--m-text-2);
  border-color: rgba(255, 255, 255, 0.1);
}

.msg__p--important {
  color: var(--m-warn);
  border-color: rgba(224, 163, 63, 0.4);
  background: rgba(224, 163, 63, 0.1);
}

.msg__p--urgent {
  color: var(--m-fire);
  border-color: rgba(212, 85, 63, 0.45);
  background: rgba(212, 85, 63, 0.12);
}

.msg__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--m-fire);
  box-shadow: 0 0 6px rgba(212, 85, 63, 0.8);
}

.msg__no {
  margin-left: auto;
  color: var(--m-text-2);
  font-size: 11px;
}

.msg__card-title {
  margin: 8px 0 0;
  color: var(--m-text-0);
  font-size: 14.5px;
  font-weight: 600;
  line-height: 1.45;
}

.msg__card-body {
  margin: 5px 0 0;
  display: -webkit-box;
  overflow: hidden;
  color: var(--m-text-2);
  font-size: 12px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.msg__card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 9px;
  padding-top: 8px;
  border-top: 1px dashed rgba(255, 255, 255, 0.07);
  font-size: 11px;
}

.msg__ref {
  max-width: 62%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.msg__go {
  color: var(--m-gold-soft);
}
</style>
