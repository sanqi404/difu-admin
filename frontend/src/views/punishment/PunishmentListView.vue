<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  adjustPunishment,
  executePunishment,
  fetchOfficers,
  fetchPunishmentSummary,
  fetchPunishments,
  finishPunishment,
} from '@/api'
import type { OfficerItem, PunishmentRecord, PunishmentSummary } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime } from '@/utils/status'

const { hasPerm } = usePerms()
const route = useRoute()
const router = useRouter()

const HELL_NAMES = [
  '拔舌地狱', '剪刀地狱', '铁树地狱', '孽镜地狱', '蒸笼地狱', '铜柱地狱',
  '刀山地狱', '冰山地狱', '油锅地狱', '牛坑地狱', '石压地狱', '舂臼地狱',
  '血池地狱', '枉死地狱', '磔刑地狱', '火山地狱', '石磨地狱', '刀锯地狱',
]
const HELL_TORTURES = [
  '拔舌穿腮', '剪断十指', '铁树刺身', '孽镜照业', '蒸笼薰蒸', '铜柱烙身',
  '刀山穿骨', '冰山裸冻', '油锅烹煮', '牛坑践踏', '石压碾骨', '舂臼舂磨',
  '血池浸体', '枉死偿命', '磔刑分尸', '火山焚身', '石磨磨浆', '刀锯解形',
]
const PUNISH_STATUS = ['待执行', '服刑中', '已刑满', '已转出', '已减免']
const DEFAULT_CAPACITY = [120, 110, 100, 96, 92, 88, 84, 80, 76, 72, 68, 64, 60, 56, 52, 48, 44, 40]
const CONFIG_KEY = 'difu.hell.config.v1'
const DAY = 86400000

interface HellConfig {
  torture: string
  capacity: number
}

const canAdjust = computed(() => hasPerm('punishment:adjust'))
const canExecute = computed(() => hasPerm('punishment:execute'))
const canViewReinc = computed(() => hasPerm(['reincarnation:view', 'reincarnation:create']))

const tab = ref<'hell' | 'ledger'>((route.meta.tab as 'hell' | 'ledger') === 'ledger' ? 'ledger' : 'hell')
const loading = ref(false)
const rows = ref<PunishmentRecord[]>([])
const total = ref(0)
const summary = ref<PunishmentSummary | null>(null)
const pendingRows = ref<PunishmentRecord[]>([])
const officers = ref<OfficerItem[]>([])
const acting = ref(0)

const query = reactive({
  keyword: '',
  status: '',
  hell_level: undefined as number | undefined,
  page: 1,
  page_size: 10,
})

const config = ref<Record<string, HellConfig>>(loadConfig())

function loadConfig(): Record<string, HellConfig> {
  const base: Record<string, HellConfig> = {}
  HELL_NAMES.forEach((_, i) => {
    base[String(i + 1)] = { torture: HELL_TORTURES[i], capacity: DEFAULT_CAPACITY[i] }
  })
  try {
    const raw = localStorage.getItem(CONFIG_KEY)
    if (raw) {
      const saved = JSON.parse(raw) as Record<string, Partial<HellConfig>>
      Object.keys(saved).forEach((k) => {
        if (!base[k]) return
        const item = saved[k] || {}
        base[k] = {
          torture: typeof item.torture === 'string' && item.torture ? item.torture : base[k].torture,
          capacity: typeof item.capacity === 'number' && item.capacity > 0 ? item.capacity : base[k].capacity,
        }
      })
    }
  } catch {
    /* 本地配置损坏时回落到默认值 */
  }
  return base
}

function saveConfig() {
  try {
    localStorage.setItem(CONFIG_KEY, JSON.stringify(config.value))
  } catch {
    ElMessage.warning('本机存储不可写，配置仅在本次会话生效')
  }
}

const hellUnits = computed(() =>
  HELL_NAMES.map((name, i) => {
    const level = i + 1
    const cfg = config.value[String(level)]
    const inUse = summary.value?.by_hell?.find((h) => h.level === level)?.count ?? 0
    return {
      level,
      name,
      torture: cfg.torture,
      capacity: cfg.capacity,
      inUse,
      ratio: Math.min(100, Math.round((inUse / Math.max(1, cfg.capacity)) * 100)),
    }
  }),
)

const pendingCount = computed(() => pendingRows.value.length)

const ledgerTabs = computed(() => [
  { key: 'hell' as const, label: '十八层地狱', count: 18 },
  { key: 'ledger' as const, label: '刑期台账', count: summary.value?.total ?? 0 },
])

function countStatus(status: string) {
  return summary.value?.by_status?.find((s) => s.status === status)?.count ?? 0
}

function punishStyle(status?: string) {
  switch (status) {
    case '服刑中':
      return { color: '#cf7a48', bg: 'rgba(207,122,72,0.16)', border: 'rgba(207,122,72,0.48)' }
    case '已刑满':
      return { color: '#c9a227', bg: 'rgba(201,162,39,0.18)', border: 'rgba(201,162,39,0.55)' }
    case '已转出':
      return { color: '#9adfd0', bg: 'rgba(76,224,195,0.12)', border: 'rgba(76,224,195,0.4)' }
    case '已减免':
      return { color: '#4ce0c3', bg: 'rgba(76,224,195,0.14)', border: 'rgba(76,224,195,0.45)' }
    default:
      return { color: '#e0b86a', bg: 'rgba(224,184,106,0.12)', border: 'rgba(224,184,106,0.42)' }
  }
}

function actualYears(row: PunishmentRecord) {
  return Math.max(0, (row.sentence_years || 0) - (row.reduced_years || 0))
}

function remainDays(row: PunishmentRecord) {
  if (!row.end_at) return 0
  const diff = new Date(row.end_at).getTime() - Date.now()
  return diff > 0 ? Math.ceil(diff / DAY) : 0
}

function elapsedPercent(row: PunishmentRecord) {
  if (!row.start_at || !row.end_at) return 0
  const start = new Date(row.start_at).getTime()
  const end = new Date(row.end_at).getTime()
  if (!start || end <= start) return 0
  const pct = ((Date.now() - start) / (end - start)) * 100
  return Math.min(100, Math.max(0, Math.round(pct)))
}

function progressColor(row: PunishmentRecord) {
  const pct = elapsedPercent(row)
  if (pct >= 90) return '#c9a227'
  if (pct >= 50) return '#cf7a48'
  return '#b3261e'
}

function isDueToday(row: PunishmentRecord) {
  if (row.status !== '服刑中' || !row.end_at) return false
  const end = new Date(row.end_at)
  if (Number.isNaN(end.getTime())) return false
  const endDay = new Date(end.getFullYear(), end.getMonth(), end.getDate()).getTime()
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  return endDay <= today
}

async function loadSummary() {
  try {
    summary.value = await fetchPunishmentSummary()
  } catch {
    summary.value = null
  }
}

async function loadPending() {
  try {
    const data = await fetchPunishments({ status: '服刑中', page: 1, page_size: 200 })
    pendingRows.value = (data.items || []).filter((r) => isDueToday(r))
  } catch {
    pendingRows.value = []
  }
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchPunishments({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      status: query.status || undefined,
      hell_level: query.hell_level,
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

async function loadOfficers() {
  try {
    const data = await fetchOfficers({ page: 1, page_size: 200, status: '在职' })
    officers.value = data.items || []
  } catch {
    officers.value = []
  }
}

async function refresh() {
  await Promise.all([loadSummary(), loadList(), loadPending()])
}

function search() {
  query.page = 1
  loadList()
}

function resetQuery() {
  query.keyword = ''
  query.status = ''
  query.hell_level = undefined
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

function switchTab(key: 'hell' | 'ledger') {
  tab.value = key
  if (key === 'ledger') loadList()
}

function pickHell(level: number) {
  query.hell_level = query.hell_level === level ? undefined : level
  tab.value = 'ledger'
  query.page = 1
  loadList()
}

function goReincarnation() {
  router.push('/reincarnation/list')
}

/* ---------------- 地狱配置编辑 ---------------- */
const cfgDialog = reactive({
  open: false,
  level: 1,
  capacity: 100,
  torture: '',
})

function openConfig(level: number) {
  const cfg = config.value[String(level)]
  cfgDialog.level = level
  cfgDialog.capacity = cfg.capacity
  cfgDialog.torture = cfg.torture
  cfgDialog.open = true
}

async function saveUnitConfig() {
  if (!cfgDialog.torture.trim()) {
    ElMessage.warning('刑种不可空缺')
    return
  }
  const level = cfgDialog.level
  const prev = config.value[String(level)] || { torture: '', capacity: 0 }
  const nextTorture = cfgDialog.torture.trim()
  const nextCapacity = Math.max(1, Math.round(cfgDialog.capacity))
  try {
    await ElMessageBox.confirm(
      `第${level}层「${HELL_NAMES[level - 1]}」改制：\n刑种 ${prev.torture} → ${nextTorture}\n容量 ${prev.capacity} → ${nextCapacity}\n存档后立即生效于在押率展示，需狱政权限，请确认无误。`,
      '改制复核',
      { confirmButtonText: '确认存档', cancelButtonText: '再核一遍', type: 'warning' },
    )
  } catch {
    return
  }
  config.value[String(level)] = { torture: nextTorture, capacity: nextCapacity }
  saveConfig()
  cfgDialog.open = false
  ElMessage.success(`第${level}层「${HELL_NAMES[level - 1]}」配置已存档`)
}

/* ---------------- 行刑与释放 ---------------- */
async function startServe(row: PunishmentRecord) {
  try {
    await ElMessageBox.confirm(
      `确认押解「${row.soul_name}」入${row.hell_name || '地狱'}服刑？\n刑期 ${actualYears(row)} 年，服刑开始后状态转为「服刑中」，期间不可撤销。`,
      '开刑确认',
      { confirmButtonText: '押解入狱', cancelButtonText: '暂缓', type: 'warning' },
    )
  } catch {
    return
  }
  acting.value = row.id
  try {
    await executePunishment(row.id)
    ElMessage.success(`「${row.soul_name}」已入${row.hell_name || '地狱'}服刑`)
    await refresh()
  } finally {
    acting.value = 0
  }
}

async function release(row: PunishmentRecord) {
  try {
    await ElMessageBox.confirm(
      `确认「${row.soul_name}」刑满释放？\n释放后亡魂状态转为「刑满」，将进入轮回司待办，不可回退。`,
      '刑满释放',
      { confirmButtonText: '开枷释放', cancelButtonText: '再候', type: 'warning' },
    )
  } catch {
    return
  }
  acting.value = row.id
  try {
    await finishPunishment(row.id)
    ElMessage.success(`「${row.soul_name}」刑满释放，已转入轮回司待办`)
    await refresh()
  } finally {
    acting.value = 0
  }
}

/* ---------------- 减刑 / 赦免 ---------------- */
const reduceDialog = reactive({
  open: false,
  mode: 'reduce' as 'reduce' | 'pardon',
  row: null as PunishmentRecord | null,
  years: 1,
  reviewer: '',
  executor: '',
  reason: '',
  submitting: false,
})

const reduceMax = computed(() => {
  const row = reduceDialog.row
  if (!row) return 1
  return Math.max(1, (row.sentence_years || 0) - (row.reduced_years || 0))
})

const reducePreview = computed(() => {
  const row = reduceDialog.row
  if (!row) return { before: 0, after: 0, beforeEnd: '', afterEnd: '' }
  const before = actualYears(row)
  const cut = Math.min(Math.max(1, reduceDialog.years), reduceMax.value)
  const after = Math.max(0, before - cut)
  const now = Date.now()
  const beforeEnd = row.end_at ? new Date(row.end_at) : new Date(now + before * 365 * DAY)
  const afterEnd = new Date(beforeEnd.getTime() - cut * 365 * DAY)
  return {
    before,
    after,
    beforeEnd: formatDateTime(beforeEnd.toISOString()),
    afterEnd: formatDateTime(afterEnd.toISOString()),
  }
})

function openReduce(row: PunishmentRecord, mode: 'reduce' | 'pardon') {
  reduceDialog.row = row
  reduceDialog.mode = mode
  reduceDialog.years = mode === 'pardon' ? reduceMaxValue(row) : 1
  reduceDialog.reviewer = ''
  reduceDialog.executor = ''
  reduceDialog.reason = ''
  reduceDialog.submitting = false
  reduceDialog.open = true
}

function reduceMaxValue(row: PunishmentRecord) {
  return Math.max(1, (row.sentence_years || 0) - (row.reduced_years || 0))
}

function officerName(id: string) {
  return officers.value.find((o) => String(o.id) === id)?.real_name || id
}

async function submitReduce() {
  const row = reduceDialog.row
  if (!row) return
  if (!reduceDialog.reviewer || !reduceDialog.executor) {
    ElMessage.warning('减刑须双人确认：请选择复核鬼差与监刑鬼差')
    return
  }
  if (reduceDialog.reviewer === reduceDialog.executor) {
    ElMessage.warning('双人确认不可为同一鬼差')
    return
  }
  if (reduceDialog.reason.trim().length < 6) {
    ElMessage.warning('减免理由不得少于 6 字')
    return
  }
  const years = reduceDialog.mode === 'pardon' ? reduceMax.value : Math.min(Math.max(1, reduceDialog.years), reduceMax.value)
  try {
    await ElMessageBox.confirm(
      `${reduceDialog.mode === 'pardon' ? '赦免' : '减刑'}影响说明：\n亡魂「${row.soul_name}」原判 ${row.sentence_years || 0} 年，已减 ${row.reduced_years || 0} 年，实刑 ${reducePreview.value.before} 年。\n本次减免 ${years} 年 → 实刑 ${reducePreview.value.after} 年，预计释放由 ${reducePreview.value.beforeEnd} 提前至 ${reducePreview.value.afterEnd}。\n复核：${officerName(reduceDialog.reviewer)} ／ 监刑：${officerName(reduceDialog.executor)}。\n减免行为写入阴律日志（告警级留痕），不可撤销。`,
      '双人复核确认',
      { confirmButtonText: '落印执行', cancelButtonText: '再议', type: 'warning' },
    )
  } catch {
    return
  }
  reduceDialog.submitting = true
  try {
    await adjustPunishment(row.id, {
      reduced_years: years,
      reason: `【双人确认】复核：${officerName(reduceDialog.reviewer)}／监刑：${officerName(reduceDialog.executor)}｜${reduceDialog.mode === 'pardon' ? '赦免' : '减刑'} ${years} 年｜理由：${reduceDialog.reason.trim()}`,
    })
    let released = false
    if (reduceDialog.mode === 'pardon' && row.status === '服刑中') {
      try {
        await finishPunishment(row.id)
        released = true
      } catch {
        released = false
      }
    }
    ElMessage.success(
      `「${row.soul_name}」${reduceDialog.mode === 'pardon' ? '赦免' : `减刑 ${years} 年`}已落印${released ? '，并即时开枷释放' : ''}`,
    )
    reduceDialog.open = false
    await refresh()
  } finally {
    reduceDialog.submitting = false
  }
}

/* ---------------- 详情 ---------------- */
const detail = reactive({ open: false, row: null as PunishmentRecord | null })

function onRowClick(row: PunishmentRecord, column?: { label?: string }) {
  if (column?.label === '操作') return
  openDetail(row)
}

function openDetail(row: PunishmentRecord) {
  detail.row = row
  detail.open = true
}

watch(
  () => [query.status, query.hell_level],
  () => {
    query.page = 1
    loadList()
  },
)

watch(
  () => route.meta.tab,
  (v) => {
    if (v === 'hell' || v === 'ledger') tab.value = v
  },
)

onMounted(async () => {
  await Promise.all([loadSummary(), loadList(), loadPending(), loadOfficers()])
})
</script>

<template>
  <div class="mv-page">
    <!-- 概览 -->
    <div class="mv-panel pu-overview">
      <div class="pu-stats">
        <div class="pu-stat">
          <span class="pu-stat__label">在册刑期</span>
          <span class="pu-stat__value">{{ summary?.total ?? 0 }}</span>
        </div>
        <div class="pu-stat">
          <span class="pu-stat__label">服刑中</span>
          <span class="pu-stat__value pu-stat__value--fire">{{ summary?.serving ?? countStatus('服刑中') }}</span>
        </div>
        <div class="pu-stat">
          <span class="pu-stat__label">已刑满</span>
          <span class="pu-stat__value pu-stat__value--gold">{{ summary?.served ?? countStatus('已刑满') }}</span>
        </div>
        <div class="pu-stat">
          <span class="pu-stat__label">待执行</span>
          <span class="pu-stat__value pu-stat__value--warn">{{ countStatus('待执行') }}</span>
        </div>
        <div class="pu-stat">
          <span class="pu-stat__label">本日刑满待转</span>
          <span class="pu-stat__value pu-stat__value--teal">{{ pendingCount }}</span>
        </div>
      </div>
      <div class="pu-actions">
        <el-button class="mv-ghost-btn" @click="refresh">刷 新 刑 册</el-button>
      </div>
    </div>

    <!-- 刑满结转待办 -->
    <div v-if="pendingCount" class="mv-panel pu-todo">
      <div class="pu-todo__head">
        <span class="mv-subtitle">刑满结转待办</span>
        <span class="mv-muted">本日 {{ pendingCount }} 名亡魂刑满待转轮回，须转轮回司办理投胎</span>
        <span class="mv-spacer" />
        <el-button v-if="canViewReinc" class="mv-seal-btn mv-seal-btn--sm" @click="goReincarnation">前往轮回司结转</el-button>
      </div>
      <div class="pu-todo__list">
        <div v-for="item in pendingRows.slice(0, 6)" :key="item.id" class="pu-todo__item">
          <span class="pu-todo__name">{{ item.soul_name }}</span>
          <span class="pu-todo__meta mv-mono">{{ item.hell_name }} · {{ remainDays(item) > 0 ? `剩余 ${remainDays(item)} 天` : '今日刑满' }}</span>
          <span class="pu-todo__meta mv-mono">刑满 {{ formatDateTime(item.end_at) }}</span>
        </div>
        <span v-if="pendingRows.length > 6" class="mv-muted">另有 {{ pendingRows.length - 6 }} 单待办…</span>
      </div>
    </div>

    <!-- 十八层地狱配置 -->
    <div v-show="tab === 'hell'" class="mv-panel pu-hell">
      <div class="pu-hell__head">
        <span class="mv-subtitle">十八层地狱配置</span>
        <span class="mv-muted">
          点选地狱可筛阅其刑期台账；{{ canAdjust ? '可编辑各层刑种与容量' : '刑种与容量编辑需「狱政」权限（punishment:adjust）' }}
        </span>
      </div>
      <div class="pu-hell__grid">
        <div
          v-for="unit in hellUnits"
          :key="unit.level"
          class="pu-hell__card"
          :class="{ 'is-loaded': unit.inUse > 0 }"
          @click="pickHell(unit.level)"
        >
          <div class="pu-hell__top">
            <span class="pu-hell__level">{{ unit.level }}</span>
            <span class="pu-hell__name">{{ unit.name }}</span>
          </div>
          <div class="pu-hell__torture mv-muted">刑种 · {{ unit.torture }}</div>
          <div class="pu-hell__meter">
            <el-progress
              :percentage="unit.ratio"
              :stroke-width="6"
              :show-text="false"
              :color="unit.ratio >= 90 ? '#b3261e' : unit.ratio >= 60 ? '#cf7a48' : '#c9a227'"
            />
          </div>
          <div class="pu-hell__bottom">
            <span class="mv-mono">在押 {{ unit.inUse }} / 容量 {{ unit.capacity }}</span>
            <el-button v-if="canAdjust" link class="pu-link pu-link--gold" @click.stop="openConfig(unit.level)">改 制</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 刑期台账 -->
    <div v-show="tab === 'ledger'" class="mv-panel mv-panel--table">
      <div class="pu-tabs">
        <button
          v-for="item in ledgerTabs"
          :key="item.key"
          class="pu-tab"
          :class="{ 'is-active': tab === item.key }"
          type="button"
          @click="switchTab(item.key)"
        >
          {{ item.label }}
          <em class="pu-tab__count">{{ item.count }}</em>
        </button>
      </div>

      <div class="mv-toolbar pu-filters">
        <div class="mv-toolbar__left">
          <el-input v-model="query.keyword" class="pu-w220" placeholder="刑期号 / 亡魂姓名" clearable @keyup.enter="search">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="query.hell_level" class="pu-w180" placeholder="地狱层级" clearable>
            <el-option v-for="(name, i) in HELL_NAMES" :key="name" :label="`${i + 1} 层 · ${name}`" :value="i + 1" />
          </el-select>
          <el-select v-model="query.status" class="pu-w130" placeholder="刑期状态" clearable>
            <el-option v-for="s in PUNISH_STATUS" :key="s" :label="s" :value="s" />
          </el-select>
          <el-button class="mv-seal-btn mv-seal-btn--sm" @click="search">查 阅</el-button>
          <el-button class="mv-ghost-btn" @click="resetQuery">重置</el-button>
        </div>
        <div class="mv-toolbar__right">
          <span class="mv-muted">共 <em class="mv-count">{{ total }}</em> 单刑期</span>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        row-key="id"
        class="mv-table pu-table"
        height="calc(100vh - 452px)"
        @row-click="onRowClick"
      >
        <el-table-column label="刑期号" width="160">
          <template #default="{ row }"><span class="mv-mono">{{ row.punish_no }}</span></template>
        </el-table-column>
        <el-table-column prop="soul_name" label="亡魂" width="100" />
        <el-table-column label="地狱" width="150">
          <template #default="{ row }">
            <span class="pu-hell-tag">{{ row.hell_level }} 层 · {{ row.hell_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="刑期（年）" width="120">
          <template #default="{ row }">
            <span class="mv-mono">{{ row.sentence_years || 0 }}</span>
            <span class="mv-sub"> / 已减 </span>
            <span class="mv-mono pu-cut">{{ row.reduced_years || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="服刑起止" width="158">
          <template #default="{ row }">
            <div class="mv-mono mv-sub">{{ formatDateTime(row.start_at) }}</div>
            <div class="mv-mono mv-sub">{{ formatDateTime(row.end_at) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="剩余刑期" width="170">
          <template #default="{ row }">
            <el-progress :percentage="elapsedPercent(row)" :stroke-width="6" :show-text="false" :color="progressColor(row)" />
            <span class="mv-mono mv-sub">
              {{ row.status === '已刑满' ? '刑期已尽' : `剩余 ${remainDays(row)} 天 · 已服 ${elapsedPercent(row)}%` }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <span
              class="pu-badge"
              :style="{ color: punishStyle(row.status).color, background: punishStyle(row.status).bg, borderColor: punishStyle(row.status).border }"
            >
              {{ row.status }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="executor_name" label="执行鬼差" width="104">
          <template #default="{ row }">{{ row.executor_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="196" fixed="right">
          <template #default="{ row }">
            <div class="pu-row-actions">
              <el-button v-if="canExecute && row.status === '待执行'" link class="pu-link pu-link--ok" :loading="acting === row.id" @click="startServe(row)">
                开刑收监
              </el-button>
              <el-button
                v-if="canAdjust && ['待执行', '服刑中'].includes(row.status || '')"
                link
                class="pu-link pu-link--gold"
                @click="openReduce(row, 'reduce')"
              >
                减刑
              </el-button>
              <el-button
                v-if="canAdjust && ['待执行', '服刑中'].includes(row.status || '')"
                link
                class="pu-link pu-link--danger"
                @click="openReduce(row, 'pardon')"
              >
                赦免
              </el-button>
              <el-button v-if="canExecute && row.status === '服刑中'" link class="pu-link" :loading="acting === row.id" @click="release(row)">
                刑满释放
              </el-button>
              <el-button link class="pu-link" @click="openDetail(row)">查阅</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="pu-empty">刑册无载，狱门虚掩</div>
        </template>
      </el-table>

      <div class="pu-pager">
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

    <!-- 地狱配置编辑 -->
    <el-dialog v-model="cfgDialog.open" title="地狱改制" width="460px" append-to-body>
      <div class="pu-form">
        <div class="pu-field">
          <label>地狱层级</label>
          <el-input :model-value="`第${cfgDialog.level}层 · ${HELL_NAMES[cfgDialog.level - 1]}`" disabled />
        </div>
        <div class="pu-field">
          <label>刑种</label>
          <el-input v-model="cfgDialog.torture" maxlength="20" placeholder="如：拔舌穿腮" />
        </div>
        <div class="pu-field">
          <label>容量（可押亡魂数）</label>
          <el-input-number v-model="cfgDialog.capacity" :min="1" :max="9999" :step="10" />
        </div>
        <div class="pu-note">容量与刑种为地狱配置台账，保存后立即生效于本页在押率展示，并留痕于本机配置。</div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" @click="cfgDialog.open = false">取 消</el-button>
        <el-button class="mv-seal-btn mv-seal-btn--sm" @click="saveUnitConfig">存 档</el-button>
      </template>
    </el-dialog>

    <!-- 减刑 / 赦免 -->
    <el-dialog v-model="reduceDialog.open" :title="reduceDialog.mode === 'pardon' ? '赦免落印' : '减刑落印'" width="620px" append-to-body>
      <div v-if="reduceDialog.row" class="pu-form">
        <div class="pu-balance">
          <div class="pu-balance__row">
            <span class="mv-muted">亡魂</span>
            <span>{{ reduceDialog.row.soul_name }}</span>
            <span class="mv-muted">刑期号</span>
            <span class="mv-mono">{{ reduceDialog.row.punish_no }}</span>
          </div>
          <div class="pu-balance__row">
            <span class="mv-muted">地狱</span>
            <span>{{ reduceDialog.row.hell_name }}</span>
            <span class="mv-muted">原判 / 已减</span>
            <span class="mv-mono">{{ reduceDialog.row.sentence_years || 0 }} 年 / {{ reduceDialog.row.reduced_years || 0 }} 年</span>
          </div>
        </div>

        <div class="pu-field">
          <label>减免年限</label>
          <el-input-number
            v-model="reduceDialog.years"
            :min="1"
            :max="reduceMax"
            :disabled="reduceDialog.mode === 'pardon'"
          />
          <span class="mv-muted">可减上限 {{ reduceMax }} 年（累计减免不得超过原判）</span>
        </div>
        <div class="pu-field">
          <label>复核鬼差</label>
          <el-select v-model="reduceDialog.reviewer" filterable class="pu-full" placeholder="选择第一确认人">
            <el-option v-for="o in officers" :key="o.id" :label="`${o.real_name}（${o.role_name || o.title || '鬼差'}）`" :value="String(o.id)" />
          </el-select>
        </div>
        <div class="pu-field">
          <label>监刑鬼差</label>
          <el-select v-model="reduceDialog.executor" filterable class="pu-full" placeholder="选择第二确认人（不可与复核人相同）">
            <el-option v-for="o in officers" :key="o.id" :label="`${o.real_name}（${o.role_name || o.title || '鬼差'}）`" :value="String(o.id)" />
          </el-select>
        </div>
        <div class="pu-field">
          <label>减免理由</label>
          <el-input
            v-model="reduceDialog.reason"
            type="textarea"
            :rows="3"
            maxlength="300"
            show-word-limit
            placeholder="如：狱中悔过，助赈饿鬼道有功，酌情减免"
          />
        </div>

        <div class="pu-impact">
          <div class="pu-impact__title">影响说明</div>
          <div class="pu-impact__line">实刑：{{ reducePreview.before }} 年 → <em class="pu-em">{{ reducePreview.after }} 年</em></div>
          <div class="pu-impact__line">预计释放：{{ reducePreview.beforeEnd }} → <em class="pu-em">{{ reducePreview.afterEnd }}</em></div>
          <div class="pu-impact__line">亡魂状态：{{ reduceDialog.mode === 'pardon' && reduceDialog.row.status === '服刑中' ? '服刑中 → 刑满（即时释放）' : '维持原状态，刑期缩短' }}</div>
          <div class="pu-impact__line">留痕：写入阴律日志，级别为「告警」，不可撤销</div>
        </div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" @click="reduceDialog.open = false">取 消</el-button>
        <el-button class="mv-seal-btn mv-seal-btn--sm" :loading="reduceDialog.submitting" @click="submitReduce">
          {{ reduceDialog.mode === 'pardon' ? '赦 免 落 印' : '减 刑 落 印' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情 -->
    <el-drawer v-model="detail.open" title="刑期卷宗" size="480px" destroy-on-close>
      <div v-if="detail.row" class="pu-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="刑期号">{{ detail.row.punish_no }}</el-descriptions-item>
          <el-descriptions-item label="亡魂">{{ detail.row.soul_name }}（ID {{ detail.row.soul_id }}）</el-descriptions-item>
          <el-descriptions-item label="地狱">{{ detail.row.hell_level }} 层 · {{ detail.row.hell_name }}</el-descriptions-item>
          <el-descriptions-item label="刑期">{{ detail.row.sentence_years || 0 }} 年（已减 {{ detail.row.reduced_years || 0 }} 年，实刑 {{ actualYears(detail.row) }} 年）</el-descriptions-item>
          <el-descriptions-item label="起止">
            {{ formatDateTime(detail.row.start_at) }} 至 {{ formatDateTime(detail.row.end_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="剩余">{{ remainDays(detail.row) }} 天（已服 {{ elapsedPercent(detail.row) }}%）</el-descriptions-item>
          <el-descriptions-item label="状态">{{ detail.row.status }}</el-descriptions-item>
          <el-descriptions-item label="执行鬼差">{{ detail.row.executor_name || '未指派' }}</el-descriptions-item>
          <el-descriptions-item label="备注">{{ detail.row.remark || '—' }}</el-descriptions-item>
          <el-descriptions-item label="立案">{{ formatDateTime(detail.row.created_at) }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.pu-overview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  flex-wrap: wrap;
}
.pu-stats {
  display: flex;
  gap: 26px;
  flex-wrap: wrap;
}
.pu-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.pu-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.1em;
}
.pu-stat__value {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 22px;
  color: var(--mv-paper);
}
.pu-stat__value--gold {
  color: var(--mv-gold);
}
.pu-stat__value--teal {
  color: var(--mv-phosphor);
}
.pu-stat__value--warn {
  color: #d9a13b;
}
.pu-stat__value--fire {
  color: #cf7a48;
}
.pu-actions {
  display: flex;
  gap: 8px;
}
.pu-todo {
  margin-top: 12px;
  padding: 12px 18px 14px;
  border-left: 2px solid rgba(179, 38, 30, 0.7);
}
.pu-todo__head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.pu-todo__list {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
}
.pu-todo__item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 10px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  border-radius: 2px;
}
.pu-todo__name {
  color: var(--mv-paper);
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
}
.pu-todo__meta {
  font-size: 12px;
  color: var(--mv-muted);
}
.pu-hell {
  margin-top: 12px;
  padding: 12px 18px 16px;
}
.pu-hell__head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.pu-hell__grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}
.pu-hell__card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 10px 8px;
  background: rgba(232, 227, 214, 0.03);
  border: 1px solid rgba(232, 227, 214, 0.12);
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.18s;
}
.pu-hell__card:hover {
  border-color: rgba(201, 162, 39, 0.5);
}
.pu-hell__card.is-loaded {
  box-shadow: inset 0 -2px 0 rgba(179, 38, 30, 0.45);
}
.pu-hell__top {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.pu-hell__level {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 18px;
  color: var(--mv-cinnabar);
  min-width: 18px;
}
.pu-hell__name {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  color: var(--mv-paper);
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pu-hell__torture {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pu-hell__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}
.pu-tabs {
  display: flex;
  gap: 6px;
  padding: 4px 18px 0;
  border-bottom: 1px solid rgba(232, 227, 214, 0.08);
}
.pu-tab {
  position: relative;
  padding: 10px 14px;
  background: transparent;
  border: none;
  color: var(--mv-muted);
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  cursor: pointer;
  font-size: 14px;
}
.pu-tab.is-active {
  color: var(--mv-gold);
}
.pu-tab.is-active::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: -1px;
  height: 2px;
  background: var(--mv-cinnabar);
}
.pu-tab__count {
  font-style: normal;
  margin-left: 6px;
  font-size: 12px;
  color: var(--mv-gold);
}
.pu-filters {
  padding: 12px 18px;
}
.pu-w220 {
  width: 220px;
}
.pu-w180 {
  width: 190px;
}
.pu-w130 {
  width: 130px;
}
.pu-hell-tag {
  font-size: 12px;
  padding: 2px 8px;
  border: 1px solid rgba(207, 122, 72, 0.4);
  color: #cf7a48;
  border-radius: 2px;
}
.pu-cut {
  color: #4ce0c3;
}
.pu-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  border: 1px solid transparent;
  border-radius: 2px;
}
.pu-row-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pu-link {
  color: var(--mv-muted);
  padding: 0;
  font-size: 12px;
}
.pu-link--ok {
  color: #4ce0c3;
}
.pu-link--gold {
  color: var(--mv-gold);
}
.pu-link--danger {
  color: #e05b45;
}
.pu-empty {
  padding: 30px 0;
  color: var(--mv-muted);
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
}
.pu-pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 18px;
}
.pu-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.pu-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pu-field label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.pu-full {
  width: 100%;
}
.pu-note {
  font-size: 12px;
  color: var(--mv-muted);
  line-height: 1.7;
}
.pu-balance {
  padding: 10px 12px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pu-balance__row {
  display: grid;
  grid-template-columns: 76px 1fr 96px 1fr;
  gap: 8px;
  font-size: 13px;
}
.pu-impact {
  padding: 10px 12px;
  border: 1px solid rgba(201, 162, 39, 0.35);
  background: rgba(201, 162, 39, 0.06);
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}
.pu-impact__title {
  color: var(--mv-gold);
  letter-spacing: 0.1em;
}
.pu-em {
  font-style: normal;
  color: #e05b45;
}
.pu-detail {
  padding: 4px 2px;
}
@media (max-width: 1400px) {
  .pu-hell__grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>
