<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchAuditLogs, fetchAuditStatistics } from '@/api'
import type { AuditLogItem, AuditStatistics } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { getToken } from '@/api/http'
import { formatDateTime } from '@/utils/status'

const { hasPerm } = usePerms()
const canExport = computed(() => hasPerm('audit:export'))

const LEVELS = ['正常', '告警', '篡改告警']
const ACTIONS = ['login', 'logout', 'create', 'update', 'delete', 'assign', 'status', 'transition', 'verify', 'export']

const loading = ref(false)
const rows = ref<AuditLogItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const stats = ref<AuditStatistics | null>(null)
const exporting = ref(false)

const range = ref<[string, string] | null>(null)
const query = reactive({ keyword: '', module: '', level: '', action: '' })

function timeParams() {
  if (!range.value || range.value.length !== 2) return {}
  return { start: range.value[0], end: range.value[1] }
}

async function loadStats() {
  try {
    stats.value = await fetchAuditStatistics(timeParams())
  } catch {
    stats.value = null
  }
}

async function load() {
  loading.value = true
  try {
    const res = await fetchAuditLogs({
      keyword: query.keyword || undefined,
      module: query.module || undefined,
      level: query.level || undefined,
      action: query.action || undefined,
      ...timeParams(),
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = res.items || []
    total.value = res.meta?.total ?? rows.value.length
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '阴律日志读取失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.keyword = ''
  query.module = ''
  query.level = ''
  query.action = ''
  range.value = null
  page.value = 1
  loadStats()
  load()
}

function applyRange() {
  page.value = 1
  loadStats()
  load()
}

const statTotal = computed(() => (stats.value?.by_module || []).reduce((a, b) => a + b.count, 0))
const tamper = computed(() => stats.value?.tamper_count ?? 0)
const warnCount = computed(() => (stats.value?.by_level || []).find((l) => l.level === '告警')?.count ?? 0)
const levelColor = (lv: string) => (lv === '篡改告警' ? '#e05b45' : lv === '告警' ? '#c9a227' : 'rgba(232,227,214,0.55)')
const actionLabel = (a: string) => a || '—'

async function exportXlsx() {
  exporting.value = true
  try {
    const params = new URLSearchParams()
    if (query.module) params.set('module', query.module)
    if (query.level) params.set('level', query.level)
    if (query.action) params.set('action', query.action)
    const tp = timeParams() as { start?: string; end?: string }
    if (tp.start) params.set('start', tp.start)
    if (tp.end) params.set('end', tp.end)
    const res = await fetch(`/api/v1/audit-logs/export?${params.toString()}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) throw new Error(`导出失败（HTTP ${res.status}）`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `阴律日志_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已导出至下载目录')
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

const detail = ref<AuditLogItem | null>(null)
const drawer = ref(false)

function openDetail(row: AuditLogItem) {
  detail.value = row
  drawer.value = true
}

onMounted(() => {
  loadStats()
  load()
})
</script>

<template>
  <div class="au-page">
    <div class="mv-panel au-banner">
      <div>
        <h2 class="mv-title">阴律日志</h2>
        <p class="mv-subtitle">凡动必有痕。举凡登录、改动、授权、流转、导出，皆录于此，篡改者另标告警。</p>
      </div>
      <div class="au-banner__ops">
        <el-date-picker
          v-model="range"
          type="datetimerange"
          size="small"
          value-format="YYYY-MM-DDTHH:mm:ss"
          start-placeholder="起"
          end-placeholder="止"
          class="au-range"
          @change="applyRange"
        />
        <el-button v-if="canExport" class="mv-ghost-btn" size="small" :loading="exporting" @click="exportXlsx">导出 xlsx</el-button>
      </div>
    </div>

    <div class="au-stats">
      <div class="mv-panel au-stat">
        <span class="au-stat__label">日志总数</span>
        <strong class="au-stat__value">{{ statTotal }}</strong>
      </div>
      <div class="mv-panel au-stat">
        <span class="au-stat__label">告警</span>
        <strong class="au-stat__value mv-gold">{{ warnCount }}</strong>
      </div>
      <div class="mv-panel au-stat">
        <span class="au-stat__label">篡改告警</span>
        <strong class="au-stat__value" style="color: #e05b45">{{ tamper }}</strong>
      </div>
      <div class="mv-panel au-stat au-stat--wide">
        <span class="au-stat__label">模块分布</span>
        <div class="au-bars">
          <div v-for="m in (stats?.by_module || []).slice(0, 6)" :key="m.module" class="au-bar">
            <span class="au-bar__name">{{ m.module }}</span>
            <span class="au-bar__track">
              <i :style="{ width: `${Math.max(4, (m.count / Math.max(1, statTotal)) * 100)}%` }"></i>
            </span>
            <span class="au-bar__val">{{ m.count }}</span>
          </div>
          <span v-if="!stats?.by_module?.length" class="au-bar__none">暂无数据</span>
        </div>
      </div>
      <div class="mv-panel au-stat au-stat--wide">
        <span class="au-stat__label">高频动作</span>
        <div class="au-actions">
          <span v-for="a in (stats?.top_actions || []).slice(0, 8)" :key="a.action" class="au-action">
            {{ a.action }}<em>{{ a.count }}</em>
          </span>
          <span v-if="!stats?.top_actions?.length" class="au-bar__none">暂无数据</span>
        </div>
      </div>
    </div>

    <section class="mv-panel au-list">
      <div class="mv-panel__head">
        <span class="mv-panel__title">日志明细</span>
        <div class="au-filters">
          <el-input
            v-model="query.keyword"
            placeholder="详情 / 鬼差 / 资源"
            clearable
            size="small"
            class="au-w200"
            @keyup.enter="page = 1; load()"
            @clear="page = 1; load()"
          />
          <el-input v-model="query.module" placeholder="模块" clearable size="small" class="au-w120" @keyup.enter="page = 1; load()" />
          <el-select v-model="query.level" placeholder="等级" clearable size="small" class="au-w110" @change="page = 1; load()">
            <el-option v-for="l in LEVELS" :key="l" :label="l" :value="l" />
          </el-select>
          <el-select v-model="query.action" placeholder="动作" clearable size="small" class="au-w120" @change="page = 1; load()">
            <el-option v-for="a in ACTIONS" :key="a" :label="a" :value="a" />
          </el-select>
          <el-button class="mv-ghost-btn" size="small" @click="page = 1; load()">查阅</el-button>
          <el-button class="mv-ghost-btn" size="small" @click="resetQuery">重置</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" size="small" @row-click="openDetail">
        <el-table-column label="时间" width="150">
          <template #default="{ row }">
            <span class="au-time">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="officer_name" label="鬼差" width="100" />
        <el-table-column prop="role_name" label="角色" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="au-dim">{{ row.role_name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="动作" width="96">
          <template #default="{ row }">
            <span class="au-act">{{ actionLabel(row.action) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="110" />
        <el-table-column label="详情" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">{{ row.detail || '—' }}</template>
        </el-table-column>
        <el-table-column label="等级" width="96">
          <template #default="{ row }">
            <span class="au-level" :style="{ color: levelColor(row.level || '正常') }">{{ row.level || '正常' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="来源 IP" width="126">
          <template #default="{ row }">
            <span class="au-dim">{{ row.ip || '—' }}</span>
          </template>
        </el-table-column>
        <template #empty>
          <div class="au-empty">此条件下无日志</div>
        </template>
      </el-table>

      <div class="au-pager">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          @current-change="(p: number) => { page = p; load() }"
        />
      </div>
    </section>

    <el-drawer v-model="drawer" title="日志详情" size="440px">
      <div v-if="detail" class="au-detail">
        <div class="au-detail__row"><span>时间</span><strong>{{ formatDateTime(detail.created_at) }}</strong></div>
        <div class="au-detail__row"><span>经办</span><strong>{{ detail.officer_name }}（{{ detail.role_name || '—' }}）</strong></div>
        <div class="au-detail__row"><span>动作</span><strong>{{ detail.action }}</strong></div>
        <div class="au-detail__row"><span>模块</span><strong>{{ detail.module }}</strong></div>
        <div class="au-detail__row"><span>资源</span><strong>{{ detail.resource }} #{{ detail.resource_id || '—' }}</strong></div>
        <div class="au-detail__row"><span>等级</span><strong :style="{ color: levelColor(detail.level) }">{{ detail.level || '正常' }}</strong></div>
        <div class="au-detail__row"><span>来源 IP</span><strong>{{ detail.ip || '—' }}</strong></div>
        <div class="au-detail__block">
          <span>详情</span>
          <p>{{ detail.detail || '—' }}</p>
        </div>
        <div class="au-detail__block">
          <span>User-Agent</span>
          <p class="au-ua">{{ detail.user_agent || '—' }}</p>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.au-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.au-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.au-banner .mv-subtitle {
  margin-top: 8px;
  max-width: 520px;
}
.au-banner__ops {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.au-range {
  width: 340px;
}
.au-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr)) 2fr;
  gap: 10px;
}
.au-stat {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 78px;
}
.au-stat--wide {
  grid-column: span 2;
}
.au-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.au-stat__value {
  font-family: var(--mv-font-title);
  font-size: 24px;
  line-height: 1.1;
}
.au-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.au-bar {
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr) 34px;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.au-bar__name {
  color: var(--mv-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.au-bar__track {
  height: 5px;
  background: rgba(232, 227, 214, 0.07);
}
.au-bar__track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, rgba(201, 162, 39, 0.9), rgba(201, 162, 39, 0.3));
}
.au-bar__val {
  text-align: right;
  color: var(--mv-paper);
}
.au-bar__none {
  font-size: 11px;
  color: rgba(232, 227, 214, 0.3);
}
.au-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.au-action {
  font-size: 11px;
  padding: 2px 8px;
  color: var(--mv-muted);
  border: 1px solid rgba(232, 227, 214, 0.14);
}
.au-action em {
  margin-left: 5px;
  font-style: normal;
  color: var(--mv-gold);
}
.au-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.au-w200 {
  width: 200px;
}
.au-w120 {
  width: 120px;
}
.au-w110 {
  width: 110px;
}
.au-time {
  font-size: 12px;
  color: var(--mv-muted);
}
.au-dim {
  font-size: 12px;
  color: var(--mv-muted);
}
.au-act {
  font-size: 12px;
  color: var(--mv-gold);
  letter-spacing: 0.04em;
}
.au-level {
  font-size: 12px;
}
.au-empty {
  padding: 26px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
.au-pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px 6px;
}
.au-detail {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.au-detail__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(232, 227, 214, 0.1);
  font-size: 12px;
}
.au-detail__row span {
  color: var(--mv-muted);
}
.au-detail__row strong {
  font-weight: 500;
  color: var(--mv-paper);
}
.au-detail__block span {
  font-size: 12px;
  color: var(--mv-muted);
}
.au-detail__block p {
  margin: 6px 0 0;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--mv-paper);
  background: rgba(232, 227, 214, 0.03);
  border: 1px solid rgba(232, 227, 214, 0.1);
}
.au-ua {
  word-break: break-all;
}
@media (max-width: 1400px) {
  .au-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .au-stat--wide {
    grid-column: span 3;
  }
}
</style>
