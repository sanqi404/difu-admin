<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { fetchOverview, fetchTrend } from '@/api'
import type { OverviewData, TrendData } from '@/api/types'
import { usePerms } from '@/composables/usePerms'

const { hasPerm } = usePerms()

const RANGES = [7, 15, 30, 60, 90]
const days = ref(30)
const loading = ref(false)
const overview = ref<OverviewData | null>(null)
const trend = ref<TrendData | null>(null)

const trendRef = ref<HTMLDivElement | null>(null)
const regionRef = ref<HTMLDivElement | null>(null)
const trendChart = shallowRef<echarts.ECharts | null>(null)
const regionChart = shallowRef<echarts.ECharts | null>(null)

const GOLD = '#C9A227'
const PHOSPHOR = '#4CE0C3'
const CINNABAR = '#B3261E'
const PAPER = 'rgba(232,227,214,0.72)'

/** 后端 by_status / by_region 为 [{status,count}] 或字典，统一成字典 */
function toMap(v: unknown): Record<string, number> {
  if (Array.isArray(v)) {
    const out: Record<string, number> = {}
    v.forEach((it) => {
      const row = it as Record<string, unknown>
      const key = String(row.status ?? row.region ?? row.name ?? row.level ?? '')
      out[key] = Number(row.count ?? 0)
    })
    return out
  }
  return (v as Record<string, number>) || {}
}

function sortedPairs(map: Record<string, number>, dropZero = false) {
  return Object.entries(map)
    .filter(([, v]) => (dropZero ? v > 0 : true))
    .sort((a, b) => b[1] - a[1])
}

const soulStatus = computed(() => sortedPairs(toMap(overview.value?.soul.by_status)))
const soulRegion = computed(() => sortedPairs(toMap(overview.value?.soul.by_region), true))
const maxStatusCount = computed(() => Math.max(1, ...soulStatus.value.map((p) => p[1])))

const stageCards = computed(() => {
  const o = overview.value
  if (!o) return []
  const punishWorking = toMap(o.punishment.by_status)['服刑中'] || 0
  const reincTodo = (toMap(o.reincarnation.by_status)['待办理'] || 0) + (toMap(o.reincarnation.by_status)['待投胎'] || 0)
  const summonRunning = toMap(o.summon.by_status)['执行中'] || 0
  return [
    { label: '拘魂工单', total: o.summon.total, hint: `执行中 ${summonRunning}`, accent: PHOSPHOR },
    { label: '十殿审判', total: o.trial.total, hint: `待审 ${o.trial.pending} · 途中 ${o.trial.in_progress}`, accent: GOLD },
    { label: '地狱刑罚', total: o.punishment.total, hint: `服刑中 ${punishWorking}`, accent: CINNABAR },
    { label: '六道轮回', total: o.reincarnation.total, hint: `待办 ${reincTodo}`, accent: PHOSPHOR },
    { label: '生死簿', total: o.life_book.total, hint: `待复核 ${o.life_book.pending_review} · 篡改 ${o.life_book.tampered}`, accent: GOLD },
    { label: '业力条目', total: o.karma.total, hint: `善 ${o.karma.good} · 恶 ${o.karma.evil}`, accent: PHOSPHOR },
  ]
})

const baseCards = computed(() => {
  const b = overview.value?.base
  if (!b) return []
  return [
    { label: '在职鬼差', value: b.online_officer, note: `共 ${b.officer} 名` },
    { label: '城隍网点', value: b.city_god, note: '辖域布点' },
    { label: '在册文书', value: b.document, note: '含已验引' },
    { label: '阴律日志', value: b.audit, note: `篡改告警 ${b.tamper_audit}` },
  ]
})

const trendTotals = computed(() => {
  const t = trend.value?.total
  if (!t) return []
  return [
    { label: '新增亡魂', value: t.new_soul, color: GOLD },
    { label: '拘魂工单', value: t.summon_order, color: PHOSPHOR },
    { label: '审判记录', value: t.trial, color: CINNABAR },
    { label: '轮回档案', value: t.reincarnation, color: PHOSPHOR },
    { label: '日志条目', value: t.audit, color: 'rgba(232,227,214,0.6)' },
  ]
})

const dailyRows = computed(() => {
  const rows = trend.value?.series || []
  return [...rows].reverse()
})

function renderTrend() {
  if (!trendRef.value) return
  if (!trendChart.value) trendChart.value = echarts.init(trendRef.value)
  const series = trend.value?.series || []
  const x = series.map((p) => p.date.slice(5))
  const defs = [
    { key: 'new_soul', name: '新增亡魂', color: GOLD },
    { key: 'summon_order', name: '拘魂工单', color: PHOSPHOR },
    { key: 'trial', name: '审判', color: CINNABAR },
    { key: 'reincarnation', name: '轮回', color: 'rgba(76,224,195,0.55)' },
    { key: 'audit', name: '日志', color: 'rgba(232,227,214,0.35)' },
  ] as const
  trendChart.value.setOption(
    {
      backgroundColor: 'transparent',
      grid: { left: 42, right: 20, top: 44, bottom: 28 },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(11,11,16,0.92)', borderColor: 'rgba(201,162,39,0.4)', textStyle: { color: '#E8E3D6', fontSize: 12 } },
      legend: { top: 6, textStyle: { color: PAPER, fontSize: 11 }, itemWidth: 10, itemHeight: 6, icon: 'rect' },
      xAxis: {
        type: 'category',
        data: x,
        axisLine: { lineStyle: { color: 'rgba(232,227,214,0.16)' } },
        axisLabel: { color: 'rgba(232,227,214,0.42)', fontSize: 10 },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisLabel: { color: 'rgba(232,227,214,0.42)', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(232,227,214,0.06)' } },
      },
      series: defs.map((d) => ({
        name: d.name,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 1.6, color: d.color },
        itemStyle: { color: d.color },
        areaStyle: d.key === 'new_soul' ? { color: 'rgba(201,162,39,0.12)' } : undefined,
        data: series.map((p) => p[d.key]),
      })),
    },
    true,
  )
}

function renderRegion() {
  if (!regionRef.value) return
  if (!regionChart.value) regionChart.value = echarts.init(regionRef.value)
  const data = soulRegion.value.map(([name, value]) => ({ name, value }))
  regionChart.value.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', backgroundColor: 'rgba(11,11,16,0.92)', borderColor: 'rgba(201,162,39,0.4)', textStyle: { color: '#E8E3D6', fontSize: 12 } },
      legend: { bottom: 0, textStyle: { color: PAPER, fontSize: 11 }, itemWidth: 8, itemHeight: 8 },
      color: [GOLD, PHOSPHOR, CINNABAR, '#8E7CC3', '#5B8FF9', '#E8E3D6'],
      series: [
        {
          type: 'pie',
          radius: ['48%', '72%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: '#0B0B10', borderWidth: 2 },
          label: { color: PAPER, fontSize: 11, formatter: '{b} {d}%' },
          labelLine: { lineStyle: { color: 'rgba(232,227,214,0.24)' } },
          data: data.length ? data : [{ name: '暂无', value: 1 }],
        },
      ],
    },
    true,
  )
}

async function load() {
  loading.value = true
  try {
    const [o, t] = await Promise.all([fetchOverview(), fetchTrend(days.value)])
    overview.value = o
    trend.value = t
    await nextTick()
    renderTrend()
    renderRegion()
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '统计读取失败')
  } finally {
    loading.value = false
  }
}

function resize() {
  trendChart.value?.resize()
  regionChart.value?.resize()
}

watch(days, () => load())

onMounted(() => {
  if (!hasPerm('stats:view')) return
  load()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  trendChart.value?.dispose()
  regionChart.value?.dispose()
})
</script>

<template>
  <div v-loading="loading" class="st-page">
    <div class="mv-panel st-banner">
      <div>
        <h2 class="mv-title">统计看板</h2>
        <p class="mv-subtitle">观阴阳之数，察六道之衡。凡工单、审判、刑罚、轮回、文书、业力之流转，俱见于此。</p>
      </div>
      <div class="st-range">
        <button
          v-for="d in RANGES"
          :key="d"
          class="st-range__btn"
          :class="{ 'is-active': days === d }"
          @click="days = d"
        >
          {{ d }} 日
        </button>
      </div>
    </div>

    <div class="st-totals">
      <div v-for="c in trendTotals" :key="c.label" class="mv-panel st-total">
        <span class="st-total__label">{{ days }} 日内 {{ c.label }}</span>
        <strong class="st-total__value" :style="{ color: c.color }">{{ c.value }}</strong>
      </div>
      <div class="mv-panel st-total">
        <span class="st-total__label">亡魂在册</span>
        <strong class="st-total__value">{{ overview?.soul.total ?? 0 }}</strong>
      </div>
      <div class="mv-panel st-total">
        <span class="st-total__label">今日新至</span>
        <strong class="st-total__value mv-gold">{{ overview?.soul.today_new ?? 0 }}</strong>
      </div>
      <div class="mv-panel st-total">
        <span class="st-total__label">羁押冻魂</span>
        <strong class="st-total__value" style="color: #e05b45">{{ overview?.soul.frozen ?? 0 }}</strong>
      </div>
    </div>

    <div class="st-charts">
      <section class="mv-panel st-chart">
        <div class="mv-panel__head">
          <span class="mv-panel__title">业务趋势 · 近 {{ days }} 日</span>
        </div>
        <div ref="trendRef" class="st-chart__box"></div>
      </section>
      <section class="mv-panel st-chart st-chart--narrow">
        <div class="mv-panel__head">
          <span class="mv-panel__title">鬼域分布</span>
        </div>
        <div ref="regionRef" class="st-chart__box"></div>
      </section>
    </div>

    <div class="st-grid">
      <section class="mv-panel st-block">
        <div class="mv-panel__head">
          <span class="mv-panel__title">亡魂状态分布</span>
          <span class="st-dim">{{ soulStatus.length }} 种</span>
        </div>
        <div class="st-bars">
          <div v-for="[name, count] in soulStatus" :key="name" class="st-bar">
            <span class="st-bar__name">{{ name }}</span>
            <span class="st-bar__track">
              <i :style="{ width: `${Math.max(2, (count / maxStatusCount) * 100)}%` }"></i>
            </span>
            <span class="st-bar__val">{{ count }}</span>
          </div>
          <div v-if="!soulStatus.length" class="st-empty">暂无数据</div>
        </div>
      </section>

      <section class="mv-panel st-block">
        <div class="mv-panel__head">
          <span class="mv-panel__title">各司业务</span>
        </div>
        <div class="st-stages">
          <div v-for="s in stageCards" :key="s.label" class="st-stage">
            <div class="st-stage__head">
              <span class="st-stage__label">{{ s.label }}</span>
              <strong class="st-stage__value" :style="{ color: s.accent }">{{ s.total }}</strong>
            </div>
            <span class="st-stage__hint">{{ s.hint }}</span>
          </div>
        </div>
        <div class="st-base">
          <div v-for="b in baseCards" :key="b.label" class="st-base__item">
            <span class="st-base__label">{{ b.label }}</span>
            <strong class="st-base__value">{{ b.value }}</strong>
            <span class="st-base__note">{{ b.note }}</span>
          </div>
        </div>
      </section>
    </div>

    <section class="mv-panel st-table">
      <div class="mv-panel__head">
        <span class="mv-panel__title">逐日明细</span>
        <span class="st-dim">近 {{ days }} 日</span>
      </div>
      <el-table :data="dailyRows" size="small" height="320">
        <el-table-column prop="date" label="日期" width="130" />
        <el-table-column prop="new_soul" label="新增亡魂" width="110" />
        <el-table-column prop="summon_order" label="拘魂工单" width="110" />
        <el-table-column prop="trial" label="审判" width="90" />
        <el-table-column prop="reincarnation" label="轮回" width="90" />
        <el-table-column prop="audit" label="日志" width="90" />
        <template #empty>
          <div class="st-empty">暂无趋势数据</div>
        </template>
      </el-table>
    </section>
  </div>
</template>

<style scoped lang="scss">
.st-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.st-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.st-banner .mv-subtitle {
  margin-top: 8px;
  max-width: 560px;
}
.st-range {
  display: flex;
  gap: 6px;
}
.st-range__btn {
  padding: 5px 12px;
  font-size: 12px;
  color: var(--mv-muted);
  background: transparent;
  border: 1px solid rgba(232, 227, 214, 0.14);
  cursor: pointer;
  transition: all 0.14s;
}
.st-range__btn:hover {
  color: var(--mv-paper);
  border-color: rgba(201, 162, 39, 0.45);
}
.st-range__btn.is-active {
  color: var(--mv-gold);
  border-color: rgba(201, 162, 39, 0.75);
  background: rgba(201, 162, 39, 0.08);
}
.st-totals {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 10px;
}
.st-total {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.st-total__label {
  font-size: 11px;
  color: var(--mv-muted);
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.st-total__value {
  font-family: var(--mv-font-title);
  font-size: 22px;
  line-height: 1.1;
}
.st-charts {
  display: grid;
  grid-template-columns: minmax(0, 2.1fr) minmax(0, 1fr);
  gap: 12px;
}
.st-chart__box {
  height: 268px;
  padding: 4px 6px 0;
}
.st-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
  gap: 12px;
}
.st-block {
  padding-bottom: 12px;
  min-height: 300px;
}
.st-dim {
  font-size: 11px;
  color: var(--mv-muted);
}
.st-bars {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 12px 18px 0;
  max-height: 380px;
  overflow: auto;
}
.st-bar {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr) 40px;
  align-items: center;
  gap: 10px;
  font-size: 11px;
}
.st-bar__name {
  color: var(--mv-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.st-bar__track {
  height: 6px;
  background: rgba(232, 227, 214, 0.07);
}
.st-bar__track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--mv-gold), rgba(201, 162, 39, 0.25));
}
.st-bar__val {
  text-align: right;
  color: var(--mv-paper);
}
.st-stages {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 12px 18px;
}
.st-stage {
  padding: 10px 12px;
  border: 1px solid rgba(232, 227, 214, 0.1);
  background: rgba(232, 227, 214, 0.02);
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.st-stage__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.st-stage__label {
  font-size: 12px;
  color: var(--mv-paper);
}
.st-stage__value {
  font-family: var(--mv-font-title);
  font-size: 19px;
  line-height: 1;
}
.st-stage__hint {
  font-size: 11px;
  color: var(--mv-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.st-base {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 0 18px;
  margin-top: 2px;
}
.st-base__item {
  padding: 8px 10px;
  border: 1px dashed rgba(232, 227, 214, 0.12);
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.st-base__label {
  font-size: 11px;
  color: var(--mv-muted);
}
.st-base__value {
  font-family: var(--mv-font-title);
  font-size: 17px;
  color: var(--mv-paper);
}
.st-base__note {
  font-size: 10px;
  color: rgba(232, 227, 214, 0.36);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.st-table {
  padding-bottom: 4px;
}
.st-empty {
  padding: 26px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
  font-size: 12px;
}
@media (max-width: 1440px) {
  .st-totals {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
  .st-charts,
  .st-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .st-stages {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
