<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  cancelSummonOrder,
  createSummonOrder,
  dispatchSummonOrder,
  exceptionSummonOrder,
  fetchOfficers,
  fetchSummonOrder,
  fetchSummonOrders,
  fetchSummonSummary,
  finishSummonOrder,
} from '@/api'
import type { OfficerItem, SoulItem, SummonOrderRecord, SummonSummary } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/status'
import SoulPicker from '@/components/SoulPicker.vue'

const { hasPerm } = usePerms()
const auth = useAuthStore()

const REGIONS = ['中央', '东方', '南方', '西方', '北方']
const PRIORITIES = ['普通', '加急', '特急']
const DEATH_TYPES = ['寿终正寝', '疾病', '意外', '自尽', '刑戮', '战乱', '溺水', '枉死']

const canCreate = computed(() => hasPerm('summon:create'))
const canDispatch = computed(() => hasPerm('summon:dispatch'))
const canExecute = computed(() => hasPerm('summon:execute'))
const canFinish = computed(() => hasPerm('summon:finish'))
const canException = computed(() => hasPerm('summon:exception'))

/** 数据域内才可操作：超管 / ALL 全域放行，其余按鬼域比对 */
function inScope(row: SummonOrderRecord) {
  if (auth.isSuper || auth.dataScope === 'ALL') return true
  const mine = auth.profile?.region || ''
  return !row.region || !mine || row.region === mine
}

type TabKey = '待派发' | '执行中' | '已完成' | '已超时' | '异常' | ''

const tab = ref<TabKey>('待派发')
const loading = ref(false)
const rows = ref<SummonOrderRecord[]>([])
const total = ref(0)
const summary = ref<SummonSummary | null>(null)
const query = reactive({
  keyword: '',
  priority: '',
  region: '',
  page: 1,
  page_size: 10,
})

const tabs = computed(() => [
  { key: '待派发' as TabKey, label: '待派工单', count: countOf('待派发') },
  { key: '执行中' as TabKey, label: '执行中', count: countOf('执行中') },
  { key: '已超时' as TabKey, label: '已超时', count: countOf('已超时'), danger: true },
  { key: '异常' as TabKey, label: '异常', count: countOf('异常') },
  { key: '已完成' as TabKey, label: '已完成', count: countOf('已完成') },
  { key: '' as TabKey, label: '全部工单', count: summary.value?.total ?? 0 },
])

function countOf(status: string) {
  return summary.value?.by_status?.find((s) => s.status === status)?.count ?? 0
}

function statusStyle(status?: string | null) {
  switch (status) {
    case '执行中':
      return { color: '#4ce0c3', bg: 'rgba(76,224,195,0.12)', border: 'rgba(76,224,195,0.4)' }
    case '已完成':
      return { color: '#8f9a90', bg: 'rgba(143,154,144,0.12)', border: 'rgba(143,154,144,0.35)' }
    case '已超时':
      return { color: '#e05b45', bg: 'rgba(224,91,69,0.16)', border: 'rgba(224,91,69,0.5)' }
    case '异常':
      return { color: '#d9a13b', bg: 'rgba(217,161,59,0.14)', border: 'rgba(217,161,59,0.45)' }
    case '已撤销':
      return { color: '#7d776c', bg: 'rgba(125,119,108,0.12)', border: 'rgba(125,119,108,0.3)' }
    default:
      return { color: '#c9a227', bg: 'rgba(201,162,39,0.12)', border: 'rgba(201,162,39,0.42)' }
  }
}

function priorityStyle(priority: string) {
  if (priority === '特急') return { color: '#e05b45', border: 'rgba(224,91,69,0.6)' }
  if (priority === '加急') return { color: '#d9a13b', border: 'rgba(217,161,59,0.5)' }
  return { color: '#a9a294', border: 'rgba(169,162,148,0.32)' }
}

/** 超时工单置顶，其次按截止时间升序 */
const sortedRows = computed(() => {
  const list = [...rows.value]
  return list.sort((a, b) => {
    const aTimeout = a.status === '已超时' ? 0 : 1
    const bTimeout = b.status === '已超时' ? 0 : 1
    if (aTimeout !== bTimeout) return aTimeout - bTimeout
    const at = a.deadline_at ? new Date(a.deadline_at).getTime() : Number.MAX_SAFE_INTEGER
    const bt = b.deadline_at ? new Date(b.deadline_at).getTime() : Number.MAX_SAFE_INTEGER
    return at - bt
  })
})

function rowClass({ row }: { row: SummonOrderRecord }) {
  if (row.status === '已超时') return 'is-timeout'
  if (row.status === '异常') return 'is-abnormal'
  return ''
}

function deadlineText(row: SummonOrderRecord) {
  if (!row.deadline_at) return '—'
  const diff = new Date(row.deadline_at).getTime() - Date.now()
  if (diff < 0) {
    const hours = Math.floor(Math.abs(diff) / 3600000)
    return `超期 ${hours} 小时`
  }
  const hours = Math.floor(diff / 3600000)
  return hours < 24 ? `余 ${hours} 小时` : `余 ${Math.floor(hours / 24)} 日`
}

async function loadSummary() {
  try {
    summary.value = await fetchSummonSummary()
  } catch {
    summary.value = null
  }
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchSummonOrders({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      priority: query.priority || undefined,
      region: query.region || undefined,
      status: tab.value || undefined,
    })
    rows.value = data.items || []
    total.value = data.meta?.total || 0
  } catch {
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await Promise.all([loadSummary(), loadList()])
}

function switchTab(key: TabKey) {
  if (tab.value === key) return
  tab.value = key
  query.page = 1
  loadList()
}

function search() {
  query.page = 1
  loadList()
}

function resetQuery() {
  query.keyword = ''
  query.priority = ''
  query.region = ''
  query.page = 1
  loadList()
}

function onPageChange(page: number) {
  query.page = page
  loadList()
}

function onSizeChange(size: number) {
  query.page_size = size
  query.page = 1
  loadList()
}

/* ---------------- 派单 ---------------- */
const dispatchDialog = reactive({ open: false, order: null as SummonOrderRecord | null })
const assignees = ref<OfficerItem[]>([])
const assigneeLoading = ref(false)
const assigneeId = ref<number | null>(null)
const dispatching = ref(false)

const FALLBACK_ASSIGNEES: OfficerItem[] = [
  { id: 11, username: 'wuchang_hei', real_name: '黑无常', role_id: 0, role_code: 'FIELD_OFFICER', role_name: '黑白无常', title: '勾魂使者·黑', region: '中央', status: '在职' },
  { id: 12, username: 'wuchang_bai', real_name: '白无常', role_id: 0, role_code: 'FIELD_OFFICER', role_name: '黑白无常', title: '勾魂使者·白', region: '东方', status: '在职' },
  { id: 13, username: 'niutou', real_name: '牛头', role_id: 0, role_code: 'ESCORT', role_name: '牛头马面', title: '押解鬼差·牛', region: '南方', status: '在职' },
  { id: 14, username: 'mamian', real_name: '马面', role_id: 0, role_code: 'ESCORT', role_name: '牛头马面', title: '押解鬼差·马', region: '北方', status: '在职' },
]

/** 凶死/横死宜押解，寿终/病故宜引魂 */
const ESCORT_DEATHS = ['意外', '自尽', '刑戮', '战乱', '溺水', '枉死']

function recommendRole(deathType?: string) {
  return ESCORT_DEATHS.includes(deathType || '') ? 'ESCORT' : 'FIELD_OFFICER'
}

function recommendText(deathType?: string) {
  return recommendRole(deathType) === 'ESCORT' ? '牛头马面 · 押解' : '黑白无常 · 引魂'
}

function isRecommended(officer: OfficerItem) {
  return (officer.role_code || '') === recommendRole(dispatchDialog.order?.death_type)
}

async function loadAssignees() {
  assigneeLoading.value = true
  try {
    const data = await fetchOfficers({ status: '在职', page: 1, page_size: 60 })
    const list = (data.items || []).filter((o) => ['FIELD_OFFICER', 'ESCORT'].includes(o.role_code || ''))
    assignees.value = list.length ? list : FALLBACK_ASSIGNEES
  } catch {
    assignees.value = FALLBACK_ASSIGNEES
  } finally {
    assigneeLoading.value = false
  }
}

async function openDispatch(order: SummonOrderRecord) {
  dispatchDialog.order = order
  dispatchDialog.open = true
  assigneeId.value = order.assignee_id ?? null
  if (!assignees.value.length) await loadAssignees()
}

async function submitDispatch() {
  if (!dispatchDialog.order) return
  if (!assigneeId.value) {
    ElMessage.warning('请选择接引使')
    return
  }
  dispatching.value = true
  try {
    await dispatchSummonOrder(dispatchDialog.order.id, assigneeId.value)
    ElMessage.success('已派发，接引使即刻启程')
    dispatchDialog.open = false
    await refresh()
  } catch {
    await refresh()
  } finally {
    dispatching.value = false
  }
}

/* ---------------- 接单（认领至本人） ---------------- */
async function claimOrder(order: SummonOrderRecord) {
  const officerId = auth.profile?.id
  if (!officerId) {
    ElMessage.warning('未取得本官名籍，无法接单')
    return
  }
  try {
    await ElMessageBox.confirm(
      `以「${auth.profile?.real_name}」名义接下工单 ${order.order_no}？接单后状态转为执行中，限期三日。`,
      '接 单 回 执',
      { confirmButtonText: '接 单', cancelButtonText: '再看看' },
    )
  } catch {
    return
  }
  try {
    await dispatchSummonOrder(order.id, officerId)
    ElMessage.success('已接单，速往阳世拘魂')
    await refresh()
  } catch {
    await refresh()
  }
}

/* ---------------- 完成回执 ---------------- */
const finishDialog = reactive({ open: false, order: null as SummonOrderRecord | null, result: '', submitting: false })

function openFinish(order: SummonOrderRecord) {
  finishDialog.order = order
  finishDialog.result = ''
  finishDialog.open = true
}

async function submitFinish() {
  if (!finishDialog.order) return
  if (finishDialog.result.trim().length < 2) {
    ElMessage.warning('回执内容不得少于 2 字')
    return
  }
  finishDialog.submitting = true
  try {
    await finishSummonOrder(finishDialog.order.id, finishDialog.result.trim())
    ElMessage.success('勾魂完成，亡魂已归阴司')
    finishDialog.open = false
    await refresh()
  } catch {
    await refresh()
  } finally {
    finishDialog.submitting = false
  }
}

/* ---------------- 异常上报 ---------------- */
const exceptionDialog = reactive({ open: false, order: null as SummonOrderRecord | null, reason: '', submitting: false })

function openException(order: SummonOrderRecord) {
  exceptionDialog.order = order
  exceptionDialog.reason = order.abnormal_reason || ''
  exceptionDialog.open = true
}

async function submitException() {
  if (!exceptionDialog.order) return
  if (exceptionDialog.reason.trim().length < 2) {
    ElMessage.warning('请填写异常缘由（不少于 2 字）')
    return
  }
  exceptionDialog.submitting = true
  try {
    await exceptionSummonOrder(exceptionDialog.order.id, exceptionDialog.reason.trim())
    ElMessage.warning('异常已登记，待判官处置')
    exceptionDialog.open = false
    await refresh()
  } catch {
    await refresh()
  } finally {
    exceptionDialog.submitting = false
  }
}

/* ---------------- 撤销 ---------------- */
async function cancelOrder(row: SummonOrderRecord) {
  try {
    await ElMessageBox.confirm(`撤销工单 ${row.order_no}？撤销后不可恢复。`, '撤 销 工 单', {
      confirmButtonText: '撤 销',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await cancelSummonOrder(row.id)
    ElMessage.warning('工单已撤销')
    await refresh()
  } catch {
    await refresh()
  }
}

/* ---------------- 开立工单 ---------------- */
const createDialog = reactive({ open: false, submitting: false })
const createForm = reactive({
  soul_id: null as number | null,
  soul: null as SoulItem | null,
  priority: '普通',
  death_type: '寿终正寝',
  location: '',
  days: 3,
})

function openCreate() {
  createForm.soul_id = null
  createForm.soul = null
  createForm.priority = '普通'
  createForm.death_type = '寿终正寝'
  createForm.location = ''
  createForm.days = 3
  createDialog.open = true
}

async function submitCreate() {
  if (!createForm.soul_id || !createForm.soul) {
    ElMessage.warning('请先检索并选定亡魂')
    return
  }
  createDialog.submitting = true
  try {
    await createSummonOrder({
      soul_id: createForm.soul_id,
      priority: createForm.priority,
      death_type: createForm.death_type,
      location: createForm.location || undefined,
      deadline_at: new Date(Date.now() + createForm.days * 86400000).toISOString(),
    })
    ElMessage.success('工单已开立，待派发')
    createDialog.open = false
    await refresh()
    if (tab.value !== '待派发') switchTab('待派发')
  } catch {
    await refresh()
  } finally {
    createDialog.submitting = false
  }
}

/* ---------------- 详情 ---------------- */
const drawerOpen = ref(false)
const detail = ref<SummonOrderRecord | null>(null)

async function openDetail(row: SummonOrderRecord) {
  drawerOpen.value = true
  detail.value = row
  try {
    detail.value = await fetchSummonOrder(row.id)
  } catch {
    /* 拦截器已提示 */
  }
}

onMounted(() => {
  // 无派单权限（接引使）默认落在「执行中」池，避免开局空池
  if (!canDispatch.value) tab.value = '执行中'
  refresh()
})
</script>

<template>
  <div class="mv-page">
    <!-- 概览 -->
    <div class="mv-panel so-overview">
      <div class="so-stats">
        <div class="so-stat">
          <span class="so-stat__label">工单总数</span>
          <span class="so-stat__value">{{ summary?.total ?? 0 }}</span>
        </div>
        <div class="so-stat">
          <span class="so-stat__label">待派发</span>
          <span class="so-stat__value so-stat__value--gold">{{ countOf('待派发') }}</span>
        </div>
        <div class="so-stat">
          <span class="so-stat__label">执行中</span>
          <span class="so-stat__value so-stat__value--teal">{{ summary?.running ?? 0 }}</span>
        </div>
        <div class="so-stat">
          <span class="so-stat__label">已超时</span>
          <span class="so-stat__value so-stat__value--red">{{ summary?.timeout ?? 0 }}</span>
        </div>
        <div class="so-stat">
          <span class="so-stat__label">异常</span>
          <span class="so-stat__value so-stat__value--warn">{{ summary?.abnormal ?? 0 }}</span>
        </div>
        <div class="so-stat">
          <span class="so-stat__label">已完成</span>
          <span class="so-stat__value">{{ summary?.finished ?? 0 }}</span>
        </div>
      </div>
      <div class="so-actions">
        <el-button v-if="canCreate" class="mv-seal-btn mv-seal-btn--sm" @click="openCreate">开 立 工 单</el-button>
        <el-button class="mv-ghost-btn" @click="refresh">刷 新 工 单 池</el-button>
      </div>
    </div>

    <div class="mv-panel mv-panel--table">
      <div class="so-tabs">
        <button
          v-for="item in tabs"
          :key="item.key"
          class="so-tab"
          :class="{ 'is-active': tab === item.key, 'is-danger': item.danger }"
          type="button"
          @click="switchTab(item.key)"
        >
          {{ item.label }}
          <em class="so-tab__count">{{ item.count }}</em>
        </button>
      </div>

      <div class="mv-toolbar so-filters">
        <div class="mv-toolbar__left">
          <el-input
            v-model="query.keyword"
            class="so-w220"
            placeholder="工单号 / 亡魂姓名"
            clearable
            @keyup.enter="search"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="query.priority" class="so-w130" placeholder="紧急程度" clearable>
            <el-option v-for="p in PRIORITIES" :key="p" :label="p" :value="p" />
          </el-select>
          <el-select v-model="query.region" class="so-w130" placeholder="归属鬼域" clearable>
            <el-option v-for="r in REGIONS" :key="r" :label="`${r}鬼域`" :value="r" />
          </el-select>
          <el-button class="mv-seal-btn mv-seal-btn--sm" @click="search">查 阅</el-button>
          <el-button class="mv-ghost-btn" @click="resetQuery">重置</el-button>
        </div>
        <div class="mv-toolbar__right">
          <span class="mv-muted">共 <em class="mv-count">{{ total }}</em> 张工单</span>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="sortedRows"
        row-key="id"
        :row-class-name="rowClass"
        class="mv-table so-table"
        height="calc(100vh - 372px)"
        @row-click="openDetail"
      >
        <el-table-column label="工单号" width="152">
          <template #default="{ row }">
            <span class="mv-mono">{{ row.order_no }}</span>
            <span v-if="row.status === '已超时'" class="so-flag">超时</span>
          </template>
        </el-table-column>
        <el-table-column prop="soul_name" label="亡魂" width="100" />
        <el-table-column label="死因" width="100">
          <template #default="{ row }">{{ row.death_type || '—' }}</template>
        </el-table-column>
        <el-table-column label="紧急" width="80">
          <template #default="{ row }">
            <span class="so-priority" :style="{ color: priorityStyle(row.priority).color, borderColor: priorityStyle(row.priority).border }">
              {{ row.priority || '普通' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span
              class="so-badge"
              :style="{
                color: statusStyle(row.status).color,
                background: statusStyle(row.status).bg,
                borderColor: statusStyle(row.status).border,
              }"
            >
              {{ row.status }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="接引使" width="112">
          <template #default="{ row }">{{ row.assignee_name || '待派' }}</template>
        </el-table-column>
        <el-table-column prop="location" label="拘魂之所" min-width="150" show-overflow-tooltip />
        <el-table-column label="限期" width="126">
          <template #default="{ row }">
            <span :class="row.status === '已超时' ? 'so-deadline so-deadline--bad' : 'so-deadline'">
              {{ deadlineText(row) }}
            </span>
            <div class="mv-sub mv-mono">{{ formatDateTime(row.deadline_at) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="开单时间" width="144">
          <template #default="{ row }">
            <span class="mv-mono">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="196" fixed="right">
          <template #default="{ row }">
            <div class="so-row-actions" @click.stop>
              <el-button link class="so-link" @click="openDetail(row)">详情</el-button>
              <el-button
                v-if="inScope(row) && canDispatch && ['待派发', '已超时', '异常'].includes(row.status)"
                link
                class="so-link so-link--ok"
                @click="openDispatch(row)"
              >
                派单
              </el-button>
              <el-button
                v-if="inScope(row) && canDispatch && ['待派发', '已超时', '异常'].includes(row.status)"
                link
                class="so-link"
                @click="claimOrder(row)"
              >
                接单
              </el-button>
              <el-button
                v-if="inScope(row) && canFinish && ['执行中', '已超时'].includes(row.status)"
                link
                class="so-link so-link--ok"
                @click="openFinish(row)"
              >
                完成回执
              </el-button>
              <el-button
                v-if="inScope(row) && canException && !['已完成', '已撤销'].includes(row.status)"
                link
                class="so-link so-link--warn"
                @click="openException(row)"
              >
                报异常
              </el-button>
              <el-button
                v-if="inScope(row) && canDispatch && !['已完成', '已撤销'].includes(row.status)"
                link
                class="so-link so-link--bad"
                @click="cancelOrder(row)"
              >
                撤销
              </el-button>
              <span v-if="!inScope(row) || (!canDispatch && !canFinish && !canException)" class="mv-sub">越界只阅</span>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="so-empty">此池无单，阴风暂歇</div>
        </template>
      </el-table>

      <div class="so-pager">
        <el-pagination
          :current-page="query.page"
          :page-size="query.page_size"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </div>

    <!-- 详情 -->
    <el-drawer v-model="drawerOpen" title="拘魂工单 · 卷宗" size="560px" destroy-on-close>
      <div v-if="detail" class="mv-drawer">
        <div class="so-drawer-head">
          <div>
            <div class="so-drawer-title">{{ detail.soul_name }}</div>
            <div class="mv-mono mv-sub">{{ detail.order_no }}</div>
          </div>
          <span
            class="so-badge"
            :style="{
              color: statusStyle(detail.status).color,
              background: statusStyle(detail.status).bg,
              borderColor: statusStyle(detail.status).border,
            }"
          >
            {{ detail.status }}
          </span>
        </div>

        <el-descriptions :column="2" border size="small" class="so-desc">
          <el-descriptions-item label="紧急度">{{ detail.priority || '普通' }}</el-descriptions-item>
          <el-descriptions-item label="死因">{{ detail.death_type || '—' }}</el-descriptions-item>
          <el-descriptions-item label="归属">{{ detail.region }}</el-descriptions-item>
          <el-descriptions-item label="接引使">{{ detail.assignee_name || '待派' }}</el-descriptions-item>
          <el-descriptions-item label="拘魂之所" :span="2">{{ detail.location || '—' }}</el-descriptions-item>
          <el-descriptions-item label="开单时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="限期">{{ formatDateTime(detail.deadline_at) }}</el-descriptions-item>
          <el-descriptions-item label="出发时间">{{ formatDateTime(detail.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatDateTime(detail.finished_at) }}</el-descriptions-item>
          <el-descriptions-item label="回执" :span="2">{{ detail.result || '—' }}</el-descriptions-item>
          <el-descriptions-item label="异常缘由" :span="2">{{ detail.abnormal_reason || '—' }}</el-descriptions-item>
        </el-descriptions>

        <div class="so-drawer-actions">
          <el-button
            v-if="inScope(detail) && canDispatch && ['待派发', '已超时', '异常'].includes(String(detail.status || ''))"
            class="mv-seal-btn mv-seal-btn--sm"
            @click="openDispatch(detail)"
          >
            派 单
          </el-button>
          <el-button
            v-if="inScope(detail) && (canFinish || canExecute) && ['执行中', '已超时'].includes(String(detail.status || ''))"
            class="mv-seal-btn mv-seal-btn--sm"
            @click="openFinish(detail)"
          >
            完 成 回 执
          </el-button>
          <el-button
            v-if="inScope(detail) && (canException || canExecute) && !['已完成', '已撤销'].includes(String(detail.status || ''))"
            class="mv-ghost-btn"
            @click="openException(detail)"
          >
            上 报 异 常
          </el-button>
          <span v-if="!inScope(detail)" class="mv-sub">此单属他域，仅可查阅</span>
        </div>
      </div>
    </el-drawer>

    <!-- 派单 -->
    <el-dialog v-model="dispatchDialog.open" title="拘魂司 · 派单" width="560px" destroy-on-close>
      <div v-if="dispatchDialog.order" class="so-form">
        <div class="so-order-tip">
          工单 <span class="mv-mono">{{ dispatchDialog.order.order_no }}</span> · 亡魂
          <strong>{{ dispatchDialog.order.soul_name }}</strong> · 死因
          <strong>{{ dispatchDialog.order.death_type || '未录' }}</strong>
          <div class="so-recommend">按亡魂类别推荐：{{ recommendText(dispatchDialog.order.death_type) }}</div>
        </div>
        <div class="so-field">
          <label>接引使</label>
          <el-select v-model="assigneeId" v-loading="assigneeLoading" placeholder="择一鬼差领单" class="so-full">
            <el-option
              v-for="o in assignees"
              :key="o.id"
              :label="`${o.real_name} · ${o.title}`"
              :value="o.id"
            >
              <div class="so-assignee">
                <span>
                  {{ o.real_name }}
                  <em class="so-assignee__role">{{ o.role_name || o.role_code }}</em>
                </span>
                <span class="so-assignee__meta">
                  {{ o.region }} · {{ o.title }}
                  <em v-if="isRecommended(o)" class="so-recommend-tag">推荐</em>
                </span>
              </div>
            </el-option>
          </el-select>
        </div>
        <div class="so-note">派单后状态转为「执行中」，限期三日；逾时自动转「已超时」并可改派。</div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" @click="dispatchDialog.open = false">取 消</el-button>
        <el-button class="mv-seal-btn mv-seal-btn--sm" :loading="dispatching" @click="submitDispatch">落 印 派 单</el-button>
      </template>
    </el-dialog>

    <!-- 完成回执 -->
    <el-dialog v-model="finishDialog.open" title="拘魂司 · 完成回执" width="520px" destroy-on-close>
      <div class="so-form">
        <div class="so-order-tip">
          工单 <span class="mv-mono">{{ finishDialog.order?.order_no }}</span> · 亡魂
          <strong>{{ finishDialog.order?.soul_name }}</strong>
        </div>
        <div class="so-field">
          <label>勾魂回执</label>
          <el-input
            v-model="finishDialog.result"
            type="textarea"
            :rows="4"
            maxlength="300"
            show-word-limit
            placeholder="例：已于子时三刻拘得亡魂，押至酆都城候审"
          />
        </div>
        <div class="so-note">提交后亡魂状态随之流转，可在亡魂台账查看轨迹。</div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" @click="finishDialog.open = false">取 消</el-button>
        <el-button class="mv-seal-btn mv-seal-btn--sm" :loading="finishDialog.submitting" @click="submitFinish">
          回 执 报 完
        </el-button>
      </template>
    </el-dialog>

    <!-- 异常上报 -->
    <el-dialog v-model="exceptionDialog.open" title="拘魂司 · 异常上报" width="520px" destroy-on-close>
      <div class="so-form">
        <div class="so-order-tip">
          工单 <span class="mv-mono">{{ exceptionDialog.order?.order_no }}</span> · 亡魂
          <strong>{{ exceptionDialog.order?.soul_name }}</strong>
        </div>
        <div class="so-field">
          <label>异常缘由</label>
          <el-input
            v-model="exceptionDialog.reason"
            type="textarea"
            :rows="4"
            maxlength="300"
            show-word-limit
            placeholder="例：阳寿未尽，魂魄难拘 / 有阴差拦阻，请判官增援"
          />
        </div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" @click="exceptionDialog.open = false">取 消</el-button>
        <el-button class="mv-seal-btn mv-seal-btn--sm" :loading="exceptionDialog.submitting" @click="submitException">
          登 记 异 常
        </el-button>
      </template>
    </el-dialog>

    <!-- 开立工单 -->
    <el-dialog v-model="createDialog.open" title="拘魂司 · 开立工单" width="560px" destroy-on-close>
      <div class="so-form">
        <div class="so-field">
          <label>亡魂</label>
          <SoulPicker v-model="createForm.soul_id" @change="(s: SoulItem | null) => (createForm.soul = s)" />
        </div>
        <div class="so-field so-field--row">
          <div>
            <label>紧急程度</label>
            <el-select v-model="createForm.priority" class="so-full">
              <el-option v-for="p in PRIORITIES" :key="p" :label="p" :value="p" />
            </el-select>
          </div>
          <div>
            <label>死因</label>
            <el-select v-model="createForm.death_type" class="so-full">
              <el-option v-for="d in DEATH_TYPES" :key="d" :label="d" :value="d" />
            </el-select>
          </div>
          <div>
            <label>限期（日）</label>
            <el-input-number v-model="createForm.days" :min="1" :max="30" controls-position="right" />
          </div>
        </div>
        <div class="so-field">
          <label>拘魂之所</label>
          <el-input v-model="createForm.location" placeholder="例：青州府临淄县城西 第三户" />
        </div>
        <div class="so-note">工单开立后进入「待派发」池，由拘魂司判官指派接引使。</div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" @click="createDialog.open = false">取 消</el-button>
        <el-button class="mv-seal-btn mv-seal-btn--sm" :loading="createDialog.submitting" @click="submitCreate">
          开 立 工 单
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.so-overview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  flex-wrap: wrap;
}
.so-stats {
  display: flex;
  gap: 26px;
  flex-wrap: wrap;
}
.so-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.so-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.1em;
}
.so-stat__value {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 22px;
  color: var(--mv-paper);
}
.so-stat__value--gold {
  color: var(--mv-gold);
}
.so-stat__value--teal {
  color: var(--mv-phosphor);
}
.so-stat__value--red {
  color: #e05b45;
}
.so-stat__value--warn {
  color: #d9a13b;
}
.so-actions {
  display: flex;
  gap: 8px;
}
.so-tabs {
  display: flex;
  gap: 6px;
  padding: 4px 18px 0;
  border-bottom: 1px solid rgba(232, 227, 214, 0.08);
  flex-wrap: wrap;
}
.so-tab {
  position: relative;
  padding: 10px 14px;
  background: transparent;
  border: none;
  color: var(--mv-muted);
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 15px;
  letter-spacing: 0.12em;
  cursor: pointer;
}
.so-tab:hover {
  color: var(--mv-paper);
}
.so-tab.is-active {
  color: var(--mv-gold);
}
.so-tab.is-danger .so-tab__count {
  color: #e05b45;
}
.so-tab.is-active::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: -1px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--mv-cinnabar), transparent);
}
.so-tab__count {
  margin-left: 6px;
  font-size: 11px;
  font-style: normal;
  color: var(--mv-muted);
}
.so-filters {
  border-bottom: none;
}
.so-w220 {
  width: 220px;
}
.so-w130 {
  width: 130px;
}
.so-full {
  width: 100%;
}
.so-table :deep(.el-table__row) {
  cursor: pointer;
}
.so-table :deep(.is-timeout) {
  background: rgba(224, 91, 69, 0.08);
}
.so-table :deep(.is-timeout td) {
  color: #e8b4a8;
}
.so-timeout-bar {
  box-shadow: inset 2px 0 0 #e05b45;
}
.so-flag {
  margin-left: 6px;
  padding: 0 4px;
  font-size: 10px;
  color: #e05b45;
  border: 1px solid rgba(224, 91, 69, 0.55);
  border-radius: 2px;
}
.so-priority {
  padding: 1px 6px;
  font-size: 12px;
  border: 1px solid;
  border-radius: 2px;
}
.so-badge {
  padding: 1px 8px;
  font-size: 12px;
  border: 1px solid;
  border-radius: 2px;
}
.so-deadline {
  color: var(--mv-muted);
  font-size: 12px;
}
.so-deadline--bad {
  color: #e05b45;
}
.so-row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.so-link {
  color: var(--mv-muted);
  font-size: 12px;
}
.so-link--ok {
  color: var(--mv-phosphor);
}
.so-link--warn {
  color: #d9a13b;
}
.so-link--bad {
  color: #e05b45;
}
.so-pager {
  display: flex;
  justify-content: flex-end;
  padding: 10px 18px 4px;
}
.so-empty {
  padding: 26px 0;
  color: var(--mv-muted);
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  letter-spacing: 0.16em;
}
.so-drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}
.so-drawer-title {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 20px;
  color: var(--mv-paper);
  letter-spacing: 0.12em;
}
.so-desc :deep(.el-descriptions__label) {
  width: 92px;
}
.so-drawer-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}
.so-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.so-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.so-field label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.12em;
}
.so-field--row {
  flex-direction: row;
  gap: 16px;
}
.so-field--row > div {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.so-order-tip {
  padding: 10px 12px;
  font-size: 13px;
  color: var(--mv-paper);
  background: rgba(232, 227, 214, 0.04);
  border: 1px solid rgba(232, 227, 214, 0.12);
  border-radius: 2px;
  line-height: 1.7;
}
.so-recommend {
  margin-top: 4px;
  font-size: 12px;
  color: var(--mv-gold);
}
.so-recommend-tag {
  margin-left: 6px;
  padding: 0 4px;
  font-style: normal;
  font-size: 10px;
  color: var(--mv-gold);
  border: 1px solid rgba(201, 162, 39, 0.6);
  border-radius: 2px;
}
.so-assignee {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}
.so-assignee__role {
  margin-left: 4px;
  font-style: normal;
  font-size: 11px;
  color: var(--mv-muted);
}
.so-assignee__meta {
  font-size: 11px;
  color: var(--mv-muted);
}
.so-note {
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--mv-muted);
  border-left: 2px solid rgba(201, 162, 39, 0.5);
  background: rgba(201, 162, 39, 0.06);
}
</style>
