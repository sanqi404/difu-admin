<script setup lang="ts">
/** 待办中心：待我审批 / 我发起的 / 已处理 */
import { computed, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { approvalsApi } from '@/api/mobile'
import type { ApprovalItem, ApprovalScope } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { bizTone, fromNow, remainTime, statusTone } from '@/utils/format'

defineOptions({ name: 'InboxView' })

const router = useRouter()
const app = useAppStore()

const SCOPES: { name: ApprovalScope; label: string }[] = [
  { name: 'todo', label: '待我审批' },
  { name: 'mine', label: '我发起的' },
  { name: 'done', label: '已处理' },
]

const scope = ref<ApprovalScope>('todo')
const items = ref<ApprovalItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const errorText = ref('')

const tick = ref(0)
let timer: number | undefined

const scopeCount = computed(() => (scope.value === 'todo' ? app.todoCount : total.value))

async function fetchPage(reset = false): Promise<void> {
  if (loading.value) return
  loading.value = true
  if (reset) {
    page.value = 1
    finished.value = false
    errorText.value = ''
  }
  try {
    const res = await approvalsApi.list({
      scope: scope.value,
      page: page.value,
      page_size: pageSize,
    })
    const list = res.items || []
    items.value = reset ? list : [...items.value, ...list]
    total.value = res.meta?.total ?? list.length
    if (scope.value === 'todo') app.setTodoCount(total.value)
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
  await fetchPage(true)
  refreshing.value = false
}

function switchScope(name: ApprovalScope): void {
  if (scope.value === name) return
  scope.value = name
}

function openDetail(item: ApprovalItem): void {
  void router.push({ name: 'approval-detail', params: { id: String(item.id) } })
}

function remainText(deadline?: string | null): string {
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

watch(scope, () => {
  items.value = []
  total.value = 0
  void fetchPage(true)
})

onActivated(() => {
  void fetchPage(true)
})

onMounted(() => {
  void fetchPage(true)
})

timer = window.setInterval(() => {
  tick.value += 1
}, 30_000)

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="m-page m-page--tabbar inbox">
    <header class="inbox__head">
      <div>
        <h1 class="inbox__title m-serif">待办中心</h1>
        <p class="inbox__sub m-faint">
          <template v-if="scope === 'todo'">共 {{ scopeCount }} 件文书待你裁决</template>
          <template v-else-if="scope === 'mine'">共 {{ total }} 件由你呈报</template>
          <template v-else>共 {{ total }} 件已过你手</template>
        </p>
      </div>
    </header>

    <van-tabs v-model:active="scope" class="inbox__tabs" shrink @change="switchScope">
      <van-tab v-for="item in SCOPES" :key="item.name" :name="item.name" :title="item.label" />
    </van-tabs>

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <div class="inbox__list">
        <div v-if="errorText && !items.length" class="m-empty">{{ errorText }}</div>

        <article
          v-for="row in items"
          :key="row.id"
          class="inbox__card"
          @click="openDetail(row)"
        >
          <div class="inbox__card-top">
            <span class="m-badge" :class="`m-badge--${bizTone(row.biz_type)}`">{{ row.biz_type }}</span>
            <span class="m-badge" :class="`m-badge--${statusTone(row.status)}`">{{ row.status }}</span>
            <span class="inbox__no m-mono">#{{ row.id }}</span>
          </div>

          <h2 class="inbox__card-title">{{ row.title }}</h2>
          <p v-if="row.summary" class="inbox__card-summary">{{ row.summary }}</p>

          <div class="inbox__card-meta">
            <span><van-icon name="user-o" /> {{ row.applicant_name || '—' }}</span>
            <span><van-icon name="clock-o" /> {{ fromNow(row.created_at) }}</span>
          </div>

          <div class="inbox__card-foot">
            <span class="inbox__step m-faint">
              环节 {{ row.current_step }} / {{ row.steps?.length || row.current_step }}
              <template v-if="row.biz_permission"> · {{ row.biz_permission }}</template>
            </span>
            <span :class="remainClass(row.deadline_at)">
              <van-icon v-if="row.is_final" name="passed" />
              <template v-else>{{ remainText(row.deadline_at) }}</template>
            </span>
          </div>
        </article>

        <van-list
          v-if="items.length || !errorText"
          v-model:loading="loading"
          :finished="finished"
          :finished-text="items.length ? '阴律卷宗已到底' : ''"
          :immediate-check="false"
          @load="onLoad"
        >
          <div v-if="!items.length && !loading" class="m-empty">此处空无一卷</div>
        </van-list>
      </div>
    </van-pull-refresh>
  </div>
</template>

<style scoped lang="scss">
.inbox__head {
  padding: 4px 2px 10px;
}

.inbox__title {
  margin: 0;
  color: var(--m-text-0);
  font-size: 20px;
  letter-spacing: 0.1em;
}

.inbox__sub {
  margin: 5px 0 0;
}

.inbox__tabs {
  margin: 0 -14px 8px;
  padding: 0 6px;
}

.inbox__list {
  min-height: 40vh;
}

.inbox__card {
  padding: 12px 13px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.008)), var(--m-ink-1);
  transition: border-color 0.16s ease;

  & + & {
    margin-top: 9px;
  }

  &:active {
    border-color: rgba(201, 162, 39, 0.4);
  }
}

.inbox__card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.inbox__no {
  margin-left: auto;
  color: var(--m-text-2);
  font-size: 11px;
}

.inbox__card-title {
  margin: 8px 0 0;
  color: var(--m-text-0);
  font-size: 14.5px;
  font-weight: 600;
  line-height: 1.45;
}

.inbox__card-summary {
  margin: 5px 0 0;
  display: -webkit-box;
  overflow: hidden;
  color: var(--m-text-2);
  font-size: 12px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.inbox__card-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 9px;
  color: var(--m-text-1);
  font-size: 11px;
}

.inbox__card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 9px;
  padding-top: 8px;
  border-top: 1px dashed rgba(255, 255, 255, 0.07);
  font-size: 11px;
}

.inbox__step {
  max-width: 58%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
