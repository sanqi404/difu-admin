<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchOverview, fetchSouls, fetchSoulTimeline } from '@/api'
import type { OverviewData, SoulItem, SoulTimeline } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime, karmaStyle, statusStyle } from '@/utils/status'

const { hasPerm } = usePerms()
const canView = computed(() => hasPerm('soul:view'))

/** 状态机主干顺序（用于流转漏斗） */
const MAIN_FLOW = ['在册', '已勾魂', '已备案', '已过境', '待审', '审判中', '已定罪', '服刑中', '刑满', '待投胎', '已投胎', '已注销']
const BRANCH_FLOW = ['还阳', '枉死城', '异常冻结']
const REGIONS = ['东方', '南方', '西方', '北方', '中央']

const overview = ref<OverviewData | null>(null)
const loading = ref(false)
const rows = ref<SoulItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const query = reactive({ keyword: '', status: '', region: '' })

function statusCounts(): Record<string, number> {
  const raw = overview.value?.soul?.by_status as unknown
  if (!raw) return {}
  if (Array.isArray(raw)) {
    const map: Record<string, number> = {}
    ;(raw as { status: string; count: number }[]).forEach((i) => (map[i.status] = i.count))
    return map
  }
  return raw as Record<string, number>
}

const flowNodes = computed(() => {
  const counts = statusCounts()
  const main = MAIN_FLOW.map((s) => ({ status: s, count: counts[s] || 0 }))
  const branch = BRANCH_FLOW.map((s) => ({ status: s, count: counts[s] || 0 }))
  const max = Math.max(1, ...main.concat(branch).map((n) => n.count))
  return { main, branch, max }
})

const statusOptions = computed(() => {
  const counts = statusCounts()
  return Object.keys(counts).map((s) => ({ status: s, count: counts[s] }))
})

async function loadOverview() {
  try {
    overview.value = await fetchOverview()
  } catch {
    overview.value = null
  }
}

async function load() {
  loading.value = true
  try {
    const res = await fetchSouls({
      keyword: query.keyword || undefined,
      status: query.status || undefined,
      region: query.region || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = res.items || []
    total.value = res.meta?.total ?? rows.value.length
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '流转台账读取失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.keyword = ''
  query.status = ''
  query.region = ''
  page.value = 1
  load()
}

function pickStatus(status: string) {
  query.status = query.status === status ? '' : status
  page.value = 1
  load()
}

/* ---------------- 流转轨迹 ---------------- */
const drawer = ref(false)
const timelineLoading = ref(false)
const timeline = ref<SoulTimeline | null>(null)

interface FlowNode {
  key: string
  label: string
  at: string | null | undefined
  detail: string
}

const flowNodes2 = computed<FlowNode[]>(() => {
  const t = timeline.value
  if (!t) return []
  const nodes: FlowNode[] = []
  const s = t.soul
  nodes.push({
    key: 'soul',
    label: '亡魂立档',
    at: s.created_at,
    detail: `入册为「${s.status}」，籍贯 ${s.native_place || '—'}，死因 ${s.death_type || '—'}`,
  })
  ;(t.life_books || []).forEach((lb) => {
    nodes.push({
      key: `lb-${lb.id}`,
      label: '生死簿登记',
      at: lb.created_at,
      detail: `${lb.book_no || ''} · 阳寿 ${lb.lifespan_years ?? '—'} · 核定 ${lb.review_status || ''}`,
    })
  })
  ;(t.summon_orders || []).forEach((o) => {
    nodes.push({
      key: `so-${o.id}`,
      label: '拘魂工单',
      at: o.summon_at || o.created_at,
      detail: `${o.order_no || ''} · ${o.status} · 拘魂使 ${o.assignee_name || '—'}`,
    })
  })
  ;(t.karmas || []).forEach((k) => {
    nodes.push({
      key: `km-${k.id}`,
      label: '业力记录',
      at: k.occurred_at,
      detail: `${k.karma_type} · ${k.category} · ${k.score} 分 · 来源 ${k.source}`,
    })
  })
  ;(t.trials || []).forEach((tr) => {
    nodes.push({
      key: `tr-${tr.id}`,
      label: `审判 · 第${tr.court_level}殿`,
      at: tr.started_at || tr.created_at,
      detail: `${tr.verdict || '未判'} · 量刑 ${tr.sentence_years ?? '—'} 年`,
    })
  })
  ;(t.punishments || []).forEach((p) => {
    nodes.push({
      key: `pu-${p.id}`,
      label: `刑罚 · ${p.hell_name || '地狱'}`,
      at: p.start_at || p.created_at,
      detail: `${p.status} · 刑期 ${p.sentence_years ?? '—'} 年`,
    })
  })
  ;(t.reincarnations || []).forEach((r) => {
    nodes.push({
      key: `rc-${r.id}`,
      label: '轮回投胎',
      at: r.reincarnated_at || r.created_at,
      detail: `${r.path || ''} · ${r.target_world || ''} · ${r.status || ''}`,
    })
  })
  return nodes
    .filter((n) => n.at)
    .sort((a, b) => new Date(a.at as string).getTime() - new Date(b.at as string).getTime())
})

async function openTimeline(row: SoulItem) {
  drawer.value = true
  timelineLoading.value = true
  timeline.value = null
  try {
    timeline.value = await fetchSoulTimeline(row.id)
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '流转轨迹读取失败')
  } finally {
    timelineLoading.value = false
  }
}

function onPageChange(p: number) {
  page.value = p
  load()
}

onMounted(() => {
  loadOverview()
  load()
})
</script>

<template>
  <div class="sf-page">
    <div class="mv-panel sf-banner">
      <div class="sf-banner__main">
        <h2 class="mv-title">流转台账</h2>
        <p class="mv-subtitle">亡魂自入册至注销之主干流转，逐站可核。状态跳步由状态机拦截，非法流转返回 409。</p>
      </div>
      <div class="sf-banner__stats">
        <div class="sf-stat">
          <span class="sf-stat__label">在册亡魂</span>
          <strong class="sf-stat__value">{{ overview?.soul?.total ?? '—' }}</strong>
        </div>
        <div class="sf-stat">
          <span class="sf-stat__label">今日新增</span>
          <strong class="sf-stat__value mv-gold">{{ overview?.soul?.today_new ?? '—' }}</strong>
        </div>
        <div class="sf-stat">
          <span class="sf-stat__label">冻结</span>
          <strong class="sf-stat__value" style="color: #e05b45">{{ overview?.soul?.frozen ?? '—' }}</strong>
        </div>
      </div>
    </div>

    <section class="mv-panel sf-flow">
      <div class="mv-panel__head">
        <span class="mv-panel__title">主干预流</span>
        <span class="sf-flow__hint">点击状态可筛列表</span>
      </div>
      <div class="sf-flow__main">
        <button
          v-for="n in flowNodes.main"
          :key="n.status"
          class="sf-node"
          :class="{ 'is-active': query.status === n.status }"
          @click="pickStatus(n.status)"
        >
          <span class="sf-node__bar">
            <i :style="{ height: `${Math.max(6, (n.count / flowNodes.max) * 100)}%` }"></i>
          </span>
          <span class="sf-node__count">{{ n.count }}</span>
          <span class="sf-node__name">{{ n.status }}</span>
        </button>
      </div>
      <div class="sf-flow__branch">
        <button
          v-for="n in flowNodes.branch"
          :key="n.status"
          class="sf-branch"
          :class="{ 'is-active': query.status === n.status }"
          @click="pickStatus(n.status)"
        >
          <span class="sf-branch__name">{{ n.status }}</span>
          <span class="sf-branch__count">{{ n.count }}</span>
        </button>
      </div>
    </section>

    <section class="mv-panel sf-list">
      <div class="mv-panel__head">
        <span class="mv-panel__title">流转明细</span>
        <div class="sf-filters">
          <el-input
            v-model="query.keyword"
            placeholder="姓名 / 亡魂编号"
            clearable
            size="small"
            class="sf-w200"
            @keyup.enter="page = 1; load()"
            @clear="page = 1; load()"
          />
          <el-select v-model="query.status" placeholder="全部状态" clearable size="small" class="sf-w130" @change="page = 1; load()">
            <el-option v-for="s in statusOptions" :key="s.status" :label="`${s.status}（${s.count}）`" :value="s.status" />
          </el-select>
          <el-select v-model="query.region" placeholder="全部鬼域" clearable size="small" class="sf-w110" @change="page = 1; load()">
            <el-option v-for="r in REGIONS" :key="r" :label="r" :value="r" />
          </el-select>
          <el-button class="mv-ghost-btn" size="small" @click="page = 1; load()">查阅</el-button>
          <el-button class="mv-ghost-btn" size="small" @click="resetQuery">重置</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" size="small">
        <el-table-column prop="soul_no" label="亡魂编号" width="126" />
        <el-table-column label="姓名" width="120">
          <template #default="{ row }">
            <button class="sf-name" @click="openTimeline(row)">{{ row.name }}</button>
          </template>
        </el-table-column>
        <el-table-column prop="region" label="鬼域" width="88" />
        <el-table-column label="状态流转" width="190">
          <template #default="{ row }">
            <div class="sf-trans">
              <span class="sf-trans__prev">{{ row.prev_status || '—' }}</span>
              <span class="sf-trans__arrow">→</span>
              <span
                class="sf-tag"
                :style="{
                  color: statusStyle(row.status).color,
                  borderColor: statusStyle(row.status).border,
                  background: statusStyle(row.status).bg,
                }"
              >{{ row.status }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="业力" width="96">
          <template #default="{ row }">
            <span :style="{ color: karmaStyle(row.karma_score || 0).color }">{{ row.karma_score }}</span>
            <span class="sf-sin">{{ row.sin_level }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="current_location" label="现处" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.current_location || '—' }}</template>
        </el-table-column>
        <el-table-column label="最后更新" width="150">
          <template #default="{ row }">
            <span class="sf-time">{{ formatDateTime(row.updated_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canView" link class="sf-link" @click="openTimeline(row)">流转轨迹</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="sf-empty">此条件下无流转记录</div>
        </template>
      </el-table>

      <div class="sf-pager">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          @current-change="onPageChange"
        />
      </div>
    </section>

    <el-drawer v-model="drawer" title="流转轨迹" size="480px">
      <div v-loading="timelineLoading" class="sf-timeline">
        <template v-if="timeline">
          <div class="sf-tl__head">
            <div class="sf-tl__name">{{ timeline.soul.name }}</div>
            <div class="sf-tl__meta">
              {{ timeline.soul.soul_no }} · {{ timeline.soul.gender }} · 卒年 {{ timeline.soul.age }} ·
              当前「{{ timeline.soul.status }}」
            </div>
          </div>
          <div v-if="flowNodes2.length" class="sf-tl__list">
            <div v-for="node in flowNodes2" :key="node.key" class="sf-tl__item">
              <span class="sf-tl__dot"></span>
              <div class="sf-tl__body">
                <div class="sf-tl__label">{{ node.label }}</div>
                <div class="sf-tl__detail">{{ node.detail }}</div>
                <div class="sf-tl__at">{{ formatDateTime(node.at) }}</div>
              </div>
            </div>
          </div>
          <div v-else class="sf-tl__empty">该魂暂无流转节点</div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.sf-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sf-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.sf-banner__main {
  max-width: 560px;
}
.sf-banner__main .mv-subtitle {
  margin-top: 8px;
  line-height: 1.75;
}
.sf-banner__stats {
  display: flex;
  gap: 10px;
}
.sf-stat {
  min-width: 88px;
  padding: 8px 12px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sf-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.sf-stat__value {
  font-family: var(--mv-font-title);
  font-size: 22px;
  line-height: 1.1;
}
.sf-flow {
  padding-bottom: 14px;
}
.sf-flow__hint {
  font-size: 12px;
  color: var(--mv-muted);
}
.sf-flow__main {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 6px;
  padding: 14px 16px 4px;
}
.sf-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px 2px 10px;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.16s;
}
.sf-node:hover,
.sf-node.is-active {
  border-color: rgba(201, 162, 39, 0.5);
  background: rgba(201, 162, 39, 0.06);
}
.sf-node__bar {
  position: relative;
  width: 100%;
  height: 56px;
  display: flex;
  align-items: flex-end;
  background: rgba(232, 227, 214, 0.04);
}
.sf-node__bar i {
  display: block;
  width: 100%;
  background: linear-gradient(180deg, rgba(76, 224, 195, 0.85), rgba(76, 224, 195, 0.25));
  transition: height 0.3s;
}
.sf-node__count {
  font-family: var(--mv-font-title);
  font-size: 15px;
  color: var(--mv-paper);
}
.sf-node__name {
  font-size: 11px;
  color: var(--mv-muted);
  white-space: nowrap;
}
.sf-flow__branch {
  display: flex;
  gap: 8px;
  padding: 6px 16px 0;
  flex-wrap: wrap;
}
.sf-branch {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px;
  font-size: 12px;
  background: rgba(179, 38, 30, 0.08);
  border: 1px solid rgba(224, 91, 69, 0.3);
  color: var(--mv-paper);
  cursor: pointer;
}
.sf-branch.is-active {
  border-color: rgba(224, 91, 69, 0.8);
}
.sf-branch__count {
  color: #e05b45;
  font-family: var(--mv-font-title);
}
.sf-list {
  padding-bottom: 6px;
}
.sf-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.sf-w200 {
  width: 200px;
}
.sf-w130 {
  width: 130px;
}
.sf-w110 {
  width: 110px;
}
.sf-name {
  background: transparent;
  border: none;
  padding: 0;
  font-family: var(--mv-font-title);
  font-size: 14px;
  color: var(--mv-paper);
  cursor: pointer;
}
.sf-name:hover {
  color: var(--mv-gold);
}
.sf-trans {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.sf-trans__prev {
  color: var(--mv-muted);
}
.sf-trans__arrow {
  color: rgba(232, 227, 214, 0.3);
}
.sf-tag {
  padding: 1px 7px;
  border: 1px solid transparent;
  border-radius: 2px;
}
.sf-sin {
  margin-left: 6px;
  font-size: 11px;
  color: var(--mv-muted);
}
.sf-time {
  font-size: 12px;
  color: var(--mv-muted);
}
.sf-link {
  color: var(--mv-gold);
  padding: 0;
  font-size: 12px;
}
.sf-pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px 6px;
}
.sf-empty {
  padding: 26px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
.sf-timeline {
  min-height: 200px;
}
.sf-tl__head {
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(232, 227, 214, 0.12);
}
.sf-tl__name {
  font-family: var(--mv-font-title);
  font-size: 20px;
  color: var(--mv-gold);
}
.sf-tl__meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--mv-muted);
}
.sf-tl__list {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
}
.sf-tl__item {
  position: relative;
  padding: 0 0 16px 20px;
  border-left: 1px solid rgba(232, 227, 214, 0.14);
}
.sf-tl__item:last-child {
  border-left-color: transparent;
}
.sf-tl__dot {
  position: absolute;
  left: -4px;
  top: 5px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--mv-gold);
  box-shadow: 0 0 0 3px rgba(201, 162, 39, 0.14);
}
.sf-tl__label {
  font-family: var(--mv-font-title);
  font-size: 14px;
  color: var(--mv-paper);
}
.sf-tl__detail {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--mv-muted);
}
.sf-tl__at {
  margin-top: 3px;
  font-size: 11px;
  color: rgba(232, 227, 214, 0.38);
}
.sf-tl__empty {
  padding: 24px 0;
  text-align: center;
  font-size: 12px;
  color: var(--mv-muted);
}
@media (max-width: 1360px) {
  .sf-flow__main {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}
</style>
