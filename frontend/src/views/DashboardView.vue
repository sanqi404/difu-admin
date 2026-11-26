<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import * as echarts from 'echarts'
import { fetchAuditLogs, fetchOverview, fetchTrend } from '@/api'
import type { AuditLogItem, OverviewData, TrendData } from '@/api/types'
import { formatDateTime } from '@/utils/status'

const loading = ref(false)
const overview = ref<OverviewData | null>(null)
const trend = ref<TrendData | null>(null)
const alerts = ref<AuditLogItem[]>([])

const chartRef = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)

interface MetricCard {
  key: string
  label: string
  value: number | string
  unit: string
  sub: string
  accent: 'teal' | 'gold' | 'cinnabar' | 'paper'
  icon: string
}

const metrics = computed<MetricCard[]>(() => {
  const o = overview.value
  if (!o) return []
  const byStatus = o.soul.by_status || {}
  const inTransit = Math.max(0, o.soul.total - (byStatus['已投胎'] || 0) - (byStatus['已注销'] || 0))
  const reincTodo = (o.reincarnation.by_status?.['待办理'] || 0) + (o.reincarnation.by_status?.['待投胎'] || 0)
  const hellWorking = o.punishment.by_status?.['服刑中'] || 0
  const loadRate = o.punishment.total ? Math.round((hellWorking / o.punishment.total) * 100) : 0
  return [
    {
      key: 'in_transit',
      label: '在途亡魂',
      value: inTransit,
      unit: '魂',
      sub: `在册总数 ${o.soul.total} · 今日入册 ${o.soul.today_new}`,
      accent: 'teal',
      icon: 'User',
    },
    {
      key: 'summon_today',
      label: '今日勾魂',
      value: o.soul.today_new,
      unit: '魂',
      sub: `勾魂工单 ${o.summon.total} · 执行中 ${o.summon.by_status?.['执行中'] || 0}`,
      accent: 'gold',
      icon: 'Bell',
    },
    {
      key: 'trial_backlog',
      label: '各殿积压',
      value: o.trial.pending + o.trial.in_progress,
      unit: '案',
      sub: `待审 ${o.trial.pending} · 审理中 ${o.trial.in_progress} · 已结 ${o.trial.closed}`,
      accent: 'cinnabar',
      icon: 'ScaleToOriginal',
    },
    {
      key: 'hell_load',
      label: '地狱负载',
      value: hellWorking,
      unit: '魂',
      sub: `十八层地狱共 ${o.punishment.total} · 负载 ${loadRate}%`,
      accent: 'cinnabar',
      icon: 'Chainsaw',
    },
    {
      key: 'reinc_todo',
      label: '轮回待办',
      value: reincTodo,
      unit: '魂',
      sub: `轮回档案 ${o.reincarnation.total} · 已投胎 ${o.reincarnation.by_status?.['已投胎'] || 0}`,
      accent: 'teal',
      icon: 'RefreshRight',
    },
    {
      key: 'tamper',
      label: '篡改告警',
      value: o.base.tamper_audit,
      unit: '条',
      sub: `阴律日志 ${o.base.audit} 条 · 生死簿篡改 ${o.life_book.tampered}`,
      accent: 'gold',
      icon: 'Warning',
    },
    {
      key: 'lifebook_review',
      label: '生死簿待复核',
      value: o.life_book.pending_review,
      unit: '卷',
      sub: `总计 ${o.life_book.total} · 已驳回 ${o.life_book.rejected}`,
      accent: 'paper',
      icon: 'Notebook',
    },
    {
      key: 'frozen',
      label: '异常冻结',
      value: o.soul.frozen,
      unit: '魂',
      sub: `城隍网点 ${o.base.city_god} · 在线鬼差 ${o.base.online_officer}`,
      accent: 'gold',
      icon: 'Snowy',
    },
  ]
})

const regions = computed(() => {
  const data = overview.value?.soul.by_region || {}
  const max = Math.max(1, ...Object.values(data))
  return Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value, percent: Math.round((value / max) * 100) }))
})

function renderChart() {
  if (!chartRef.value) return
  if (!chart.value) chart.value = echarts.init(chartRef.value)
  const series = trend.value?.series || []
  const dates = series.map((p) => p.date.slice(5))
  const opt: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    grid: { left: 46, right: 54, top: 46, bottom: 34 },
    legend: {
      top: 6,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: { color: '#a9a294', fontSize: 11 },
      data: ['新入亡魂', '勾魂工单', '审判', '轮回', '阴律日志'],
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(18,24,31,0.95)',
      borderColor: 'rgba(201,162,39,0.45)',
      textStyle: { color: '#e8e3d6', fontSize: 12 },
      axisPointer: { type: 'line', lineStyle: { color: 'rgba(201,162,39,0.4)' } },
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(201,162,39,0.28)' } },
      axisLabel: { color: '#7d776c', fontSize: 10, interval: 2 },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: '业务量',
        nameTextStyle: { color: '#7d776c', fontSize: 10 },
        axisLabel: { color: '#7d776c', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(201,162,39,0.08)' } },
      },
      {
        type: 'value',
        name: '日志',
        nameTextStyle: { color: '#7d776c', fontSize: 10 },
        axisLabel: { color: '#7d776c', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '新入亡魂',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        data: series.map((p) => p.new_soul),
        itemStyle: { color: '#4CE0C3' },
        lineStyle: { width: 2, shadowColor: 'rgba(76,224,195,0.55)', shadowBlur: 12 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(76,224,195,0.28)' },
            { offset: 1, color: 'rgba(76,224,195,0)' },
          ]),
        },
      },
      {
        name: '勾魂工单',
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: series.map((p) => p.summon_order),
        itemStyle: { color: '#C9A227' },
        lineStyle: { width: 1.6 },
      },
      {
        name: '审判',
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: series.map((p) => p.trial),
        itemStyle: { color: '#D4553F' },
        lineStyle: { width: 1.6 },
      },
      {
        name: '轮回',
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: series.map((p) => p.reincarnation),
        itemStyle: { color: '#79C5E8' },
        lineStyle: { width: 1.6 },
      },
      {
        name: '阴律日志',
        type: 'bar',
        yAxisIndex: 1,
        barWidth: 5,
        data: series.map((p) => p.audit),
        itemStyle: { color: 'rgba(201,162,39,0.22)' },
      },
    ],
  }
  chart.value.setOption(opt, true)
  chart.value.resize()
}

async function loadAll() {
  loading.value = true
  try {
    const [ov, tr, logs] = await Promise.all([
      fetchOverview(),
      fetchTrend(30),
      fetchAuditLogs({ page: 1, page_size: 6, level: '篡改告警' }),
    ])
    overview.value = ov
    trend.value = tr
    alerts.value = logs.items || []
    renderChart()
  } catch {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

function onResize() {
  chart.value?.resize()
}

onMounted(() => {
  loadAll()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart.value?.dispose()
  chart.value = null
})
</script>

<template>
  <div class="mv-page" v-loading="loading">
    <!-- 标题区 -->
    <div class="mv-hero mv-panel">
      <div class="mv-hero__main">
        <h2 class="mv-title">酆都城舆图</h2>
        <p class="mv-hero__desc">
          俯瞰九幽：亡魂在途、工单流转、十殿听讼、地狱刑期与轮回待办，一图尽揽。
        </p>
      </div>
      <div class="mv-hero__stats">
        <div class="mv-hero__stat">
          <span class="mv-hero__stat-label">近 30 日业务总量</span>
          <span class="mv-hero__stat-value">{{ trend?.total ? trend.total.new_soul + trend.total.summon_order + trend.total.trial + trend.total.reincarnation + trend.total.audit : '—' }}</span>
        </div>
        <div class="mv-hero__stat">
          <span class="mv-hero__stat-label">善业 / 恶业</span>
          <span class="mv-hero__stat-value">
            <em class="teal">{{ overview?.karma.good ?? '—' }}</em>
            <i>/</i>
            <em class="cinnabar">{{ overview?.karma.evil ?? '—' }}</em>
          </span>
        </div>
        <el-button class="mv-ghost-btn" @click="loadAll">刷新舆图</el-button>
      </div>
    </div>

    <!-- 八大板块 -->
    <div class="mv-metrics">
      <div v-for="m in metrics" :key="m.key" class="mv-metric" :class="`is-${m.accent}`">
        <div class="mv-metric__top">
          <span class="mv-metric__label">{{ m.label }}</span>
          <el-icon class="mv-metric__icon"><component :is="m.icon" /></el-icon>
        </div>
        <div class="mv-metric__value">
          {{ m.value }}<span class="mv-metric__unit">{{ m.unit }}</span>
        </div>
        <div class="mv-metric__sub">{{ m.sub }}</div>
      </div>
    </div>

    <div class="mv-dash-row">
      <!-- 趋势 -->
      <section class="mv-panel mv-panel--chart">
        <div class="mv-panel__head">
          <h3 class="mv-panel__title">
            <span class="mv-diamond" />
            三十日阴司气数
          </h3>
          <span class="mv-muted mv-hint">近 30 天 · 单位：件 / 条</span>
        </div>
        <div ref="chartRef" class="mv-chart" />
      </section>

      <!-- 告警 -->
      <section class="mv-panel mv-panel--alerts">
        <div class="mv-panel__head">
          <h3 class="mv-panel__title">
            <span class="mv-diamond is-cinnabar" />
            阴律告警
          </h3>
          <el-tag size="small" type="danger" effect="dark">{{ alerts.length }} 条</el-tag>
        </div>
        <ul v-if="alerts.length" class="mv-alerts">
          <li v-for="a in alerts" :key="a.id" class="mv-alerts__item">
            <div class="mv-alerts__head">
              <span class="mv-alerts__tag">篡改</span>
              <span class="mv-alerts__officer">{{ a.officer_name }}</span>
              <span class="mv-alerts__time">{{ formatDateTime(a.created_at) }}</span>
            </div>
            <p class="mv-alerts__detail">{{ a.detail }}</p>
          </li>
        </ul>
        <el-empty v-else description="阴律肃清，暂无告警" :image-size="70" />
      </section>
    </div>

    <!-- 五方鬼域 -->
    <section class="mv-panel">
      <div class="mv-panel__head">
        <h3 class="mv-panel__title">
          <span class="mv-diamond" />
          五方鬼域在册分布
        </h3>
        <span class="mv-muted mv-hint">按亡魂归属鬼域统计</span>
      </div>
      <div class="mv-regions">
        <div v-for="r in regions" :key="r.name" class="mv-regions__row">
          <span class="mv-regions__name">{{ r.name }}</span>
          <div class="mv-regions__track">
            <div class="mv-regions__fill" :style="{ width: `${r.percent}%` }" />
          </div>
          <span class="mv-regions__value">{{ r.value }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.mv-hero {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  background:
    radial-gradient(600px 200px at 8% 0%, rgba(76, 224, 195, 0.08), transparent 70%),
    linear-gradient(180deg, rgba(22, 30, 39, 0.96), rgba(15, 21, 27, 0.98));
}
.mv-hero__main {
  flex: 1 1 320px;
}
.mv-hero__main h2 {
  font-size: 24px;
}
.mv-hero__desc {
  margin: 8px 0 0;
  font-size: 12px;
  letter-spacing: 0.1em;
  color: var(--mv-paper-dim);
}
.mv-hero__stats {
  display: flex;
  align-items: center;
  gap: 20px;
}
.mv-hero__stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mv-hero__stat-label {
  font-size: 10px;
  letter-spacing: 0.2em;
  color: var(--mv-muted);
}
.mv-hero__stat-value {
  font-family: var(--mv-font-title);
  font-size: 22px;
  color: var(--mv-gold);
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.mv-hero__stat-value em {
  font-style: normal;
}
.mv-hero__stat-value i {
  font-style: normal;
  color: var(--mv-muted);
  font-size: 14px;
}
.teal {
  color: var(--mv-phosphor);
}
.cinnabar {
  color: #d4553f;
}

/* 指标卡 */
.mv-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.mv-metric {
  position: relative;
  padding: 14px 16px 12px;
  background: linear-gradient(180deg, rgba(22, 30, 39, 0.94), rgba(13, 18, 24, 0.98));
  border: 1px solid rgba(201, 162, 39, 0.16);
  border-radius: 2px;
  overflow: hidden;
  transition: border-color 0.18s ease, transform 0.18s ease;
}
.mv-metric::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 42%;
  height: 1px;
  background: linear-gradient(90deg, var(--mv-gold), transparent);
  opacity: 0.55;
}
.mv-metric:hover {
  border-color: rgba(201, 162, 39, 0.42);
  transform: translateY(-2px);
}
.mv-metric__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mv-metric__label {
  font-family: var(--mv-font-title);
  font-size: 13px;
  letter-spacing: 0.18em;
  color: var(--mv-paper-dim);
}
.mv-metric__icon {
  font-size: 15px;
  color: rgba(201, 162, 39, 0.55);
}
.mv-metric__value {
  margin-top: 8px;
  font-family: var(--mv-font-title);
  font-size: 30px;
  line-height: 1.1;
  color: var(--mv-paper);
  font-variant-numeric: tabular-nums;
}
.mv-metric__unit {
  margin-left: 4px;
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--mv-muted);
}
.mv-metric__sub {
  margin-top: 8px;
  font-size: 11px;
  color: var(--mv-muted);
  letter-spacing: 0.04em;
}
.mv-metric.is-teal .mv-metric__value {
  color: var(--mv-phosphor);
  text-shadow: 0 0 18px rgba(76, 224, 195, 0.35);
}
.mv-metric.is-gold .mv-metric__value {
  color: var(--mv-gold);
  text-shadow: 0 0 18px rgba(201, 162, 39, 0.3);
}
.mv-metric.is-cinnabar .mv-metric__value {
  color: #e0725f;
  text-shadow: 0 0 18px rgba(179, 38, 30, 0.45);
}
.mv-metric.is-paper .mv-metric__value {
  color: var(--mv-paper);
}

.mv-dash-row {
  display: grid;
  grid-template-columns: minmax(0, 1.62fr) minmax(0, 1fr);
  gap: 12px;
}
.mv-chart {
  width: 100%;
  height: 320px;
}
.mv-hint {
  font-size: 11px;
  letter-spacing: 0.08em;
}
.mv-diamond {
  width: 7px;
  height: 7px;
  transform: rotate(45deg);
  background: var(--mv-phosphor);
  box-shadow: 0 0 10px rgba(76, 224, 195, 0.7);
  display: inline-block;
}
.mv-diamond.is-cinnabar {
  background: var(--mv-cinnabar-lit);
  box-shadow: 0 0 10px rgba(179, 38, 30, 0.8);
}

.mv-alerts {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 9px;
  max-height: 320px;
  overflow-y: auto;
}
.mv-alerts__item {
  padding: 9px 10px;
  background: rgba(179, 38, 30, 0.06);
  border-left: 2px solid rgba(179, 38, 30, 0.55);
}
.mv-alerts__head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.mv-alerts__tag {
  padding: 1px 6px;
  font-family: var(--mv-font-title);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: #f6ece0;
  background: linear-gradient(180deg, #c8382d, #8b1712);
  border: 1px solid rgba(201, 162, 39, 0.4);
}
.mv-alerts__officer {
  color: var(--mv-paper-dim);
}
.mv-alerts__time {
  margin-left: auto;
  color: var(--mv-muted);
  font-variant-numeric: tabular-nums;
}
.mv-alerts__detail {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--mv-paper);
}

.mv-regions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px 26px;
}
.mv-regions__row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.mv-regions__name {
  width: 42px;
  flex: 0 0 42px;
  font-family: var(--mv-font-title);
  font-size: 12px;
  letter-spacing: 0.14em;
  color: var(--mv-gold);
}
.mv-regions__track {
  flex: 1;
  height: 6px;
  background: rgba(201, 162, 39, 0.08);
  border: 1px solid rgba(201, 162, 39, 0.12);
}
.mv-regions__fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(76, 224, 195, 0.5), rgba(76, 224, 195, 0.95));
  box-shadow: 0 0 12px rgba(76, 224, 195, 0.35);
}
.mv-regions__value {
  width: 34px;
  text-align: right;
  font-size: 12px;
  color: var(--mv-paper-dim);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1360px) {
  .mv-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .mv-dash-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
