<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchSoul,
  fetchSoulStatusOptions,
  fetchSoulTimeline,
  fetchSouls,
  transitionSoul,
} from '@/api'
import type { AllowedAction, SoulItem, SoulTimeline } from '@/api/types'
import { formatDate, formatDateTime, karmaStyle, statusStyle } from '@/utils/status'

const REGIONS = ['中央', '东方', '南方', '西方', '北方']

const loading = ref(false)
const rows = ref<SoulItem[]>([])
const total = ref(0)
const statuses = ref<string[]>([])

const query = reactive({
  keyword: '',
  status: '',
  region: '',
  page: 1,
  page_size: 10,
})

const drawerOpen = ref(false)
const detailLoading = ref(false)
const detail = ref<SoulItem | null>(null)
const timeline = ref<SoulTimeline | null>(null)
const acting = ref('')

const allowedActions = computed<AllowedAction[]>(() => detail.value?.allowed_actions || [])

const summary = computed(() => {
  const counter: Record<string, number> = {}
  for (const r of rows.value) counter[r.status] = (counter[r.status] || 0) + 1
  return counter
})

async function loadList() {
  loading.value = true
  try {
    const data = await fetchSouls({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      status: query.status || undefined,
      region: query.region || undefined,
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

function search() {
  query.page = 1
  loadList()
}

function resetQuery() {
  query.keyword = ''
  query.status = ''
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

async function openDetail(row: SoulItem) {
  drawerOpen.value = true
  detailLoading.value = true
  detail.value = row
  timeline.value = null
  try {
    const [d, tl] = await Promise.all([fetchSoul(row.id), fetchSoulTimeline(row.id)])
    detail.value = d
    timeline.value = tl
  } catch {
    /* 拦截器已提示 */
  } finally {
    detailLoading.value = false
  }
}

async function reloadDetail() {
  if (!detail.value) return
  const id = detail.value.id
  detailLoading.value = true
  try {
    const [d, tl] = await Promise.all([fetchSoul(id), fetchSoulTimeline(id)])
    detail.value = d
    timeline.value = tl
  } finally {
    detailLoading.value = false
  }
}

async function runAction(action: AllowedAction) {
  if (!detail.value) return
  let reason = ''
  try {
    const res = await ElMessageBox.prompt(
      `确认对「${detail.value.name}」执行「${action.name}」？状态将变为「${action.to}」。请简述缘由（记入阴律日志）。`,
      '生死流转',
      {
        confirmButtonText: '准 予 执 行',
        cancelButtonText: '再议',
        inputPlaceholder: '如：孽镜所照，罪业已清',
        inputValidator: (v: string) => (v && v.trim().length >= 2 ? true : '缘由至少 2 字'),
      },
    )
    reason = res.value
  } catch {
    return
  }
  acting.value = action.action
  try {
    await transitionSoul(detail.value.id, { action: action.action, reason })
    ElMessage.success(`已执行「${action.name}」，亡魂转入「${action.to}」`)
    await reloadDetail()
    await loadList()
  } catch {
    /* 409 等由拦截器提示并回显可用动作 */
    await reloadDetail()
  } finally {
    acting.value = ''
  }
}

/* ---------------- 三生石时间轴 ---------------- */
interface StoneEvent {
  time: string
  label: string
  title: string
  desc: string
  color: string
}

const stoneEvents = computed<StoneEvent[]>(() => {
  const tl = timeline.value
  if (!tl) return []
  const events: StoneEvent[] = []

  for (const b of tl.life_books || []) {
    events.push({
      time: b.created_at || b.reviewed_at || '',
      label: '生死簿',
      title: `${b.book_no} · ${b.action}`,
      desc: `${b.diff_desc || ''}${b.is_tampered ? '（篡改告警）' : ''}${b.review_comment ? ` · ${b.review_comment}` : ''}`,
      color: b.is_tampered ? '#d4553f' : '#C9A227',
    })
  }
  for (const o of tl.summon_orders || []) {
    events.push({
      time: o.created_at || o.summon_at || '',
      label: '勾魂工单',
      title: `${o.order_no} · ${o.assignee_name || '待派'}`,
      desc: `${o.location || ''}${o.result ? ` · ${o.result}` : ''}${o.abnormal_reason ? ` · 异常：${o.abnormal_reason}` : ''}`,
      color: '#C9A227',
    })
  }
  for (const k of tl.karmas || []) {
    events.push({
      time: k.occurred_at || k.created_at || '',
      label: '孽镜照业',
      title: `${k.karma_no} · ${k.karma_type} ${k.category}`,
      desc: `业力 ${k.score > 0 ? '+' : ''}${k.score} 分 · ${k.description || ''}`,
      color: k.score >= 0 ? '#4CE0C3' : '#d4553f',
    })
  }
  for (const t of tl.trials || []) {
    events.push({
      time: t.started_at || t.created_at || '',
      label: '十殿审判',
      title: `第 ${t.court_level} 殿 · ${t.judge_name}`,
      desc: `${t.guilt_desc || ''}${t.verdict ? ` · 判：${t.verdict}` : ' · 待判'}${
        t.sentence_years ? ` · 刑期 ${t.sentence_years} 年` : ''
      }`,
      color: t.verdict ? '#e0725f' : '#8fa3b8',
    })
  }
  for (const pu of tl.punishments || []) {
    events.push({
      time: pu.start_at || pu.created_at || '',
      label: '刑期执行',
      title: `${pu.hell_name || ''} · ${pu.progress || pu.status || ''}`,
      desc: `判刑 ${pu.sentence_years || 0} 年 · 执刑 ${pu.executor_name || '待派'}${
        pu.end_at ? ` · 应满 ${formatDate(pu.end_at)}` : ''
      }`,
      color: '#cf7a48',
    })
  }
  for (const r of tl.reincarnations || []) {
    events.push({
      time: r.reincarnated_at || r.scheduled_at || r.created_at || '',
      label: '六道轮回',
      title: `${r.path || ''}${r.target_world ? ` · ${r.target_world}` : ''}`,
      desc: `${r.soup_confirmed ? '孟婆汤已饮' : '孟婆汤未饮'}${r.remark ? ` · ${r.remark}` : ''}`,
      color: '#4CE0C3',
    })
  }
  return events.sort((a, b) => (a.time < b.time ? 1 : -1))
})

onMounted(async () => {
  try {
    const opt = await fetchSoulStatusOptions()
    statuses.value = opt.statuses || []
  } catch {
    statuses.value = []
  }
  loadList()
})
</script>

<template>
  <div class="mv-page">
    <!-- 筛选 -->
    <div class="mv-panel mv-toolbar">
      <div class="mv-toolbar__left">
        <el-input
          v-model="query.keyword"
          class="mv-w-220"
          placeholder="姓名 / 亡魂编号 / 原籍"
          clearable
          @keyup.enter="search"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="query.status" class="mv-w-150" placeholder="亡魂状态" clearable>
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="query.region" class="mv-w-130" placeholder="归属鬼域" clearable>
          <el-option v-for="r in REGIONS" :key="r" :label="`${r}鬼域`" :value="r" />
        </el-select>
        <el-button class="mv-seal-btn mv-seal-btn--sm" @click="search">查 阅 卷 宗</el-button>
        <el-button class="mv-ghost-btn" @click="resetQuery">重置</el-button>
      </div>
      <div class="mv-toolbar__right">
        <span class="mv-muted">共 <em class="mv-count">{{ total }}</em> 魂在册</span>
        <span v-if="query.status" class="mv-muted">· 本页 {{ summary[query.status] || 0 }} 条匹配状态</span>
      </div>
    </div>

    <!-- 列表 -->
    <div class="mv-panel mv-panel--table">
      <div class="mv-panel__head">
        <h3 class="mv-panel__title">
          <span class="mv-diamond" />
          亡魂主档
        </h3>
        <span class="mv-muted mv-hint">点击行可开启三生石卷宗</span>
      </div>
      <el-table
        v-loading="loading"
        :data="rows"
        row-key="id"
        class="mv-table"
        height="calc(100vh - 300px)"
        @row-click="openDetail"
      >
        <el-table-column prop="soul_no" label="亡魂编号" width="132">
          <template #default="{ row }">
            <span class="mv-mono">{{ row.soul_no }}</span>
          </template>
        </el-table-column>
        <el-table-column label="姓名" width="150">
          <template #default="{ row }">
            <div class="mv-soul">
              <span class="mv-soul__name">{{ row.name }}</span>
              <span class="mv-soul__meta">{{ row.gender }} · {{ row.age }} 岁</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="死期" width="150">
          <template #default="{ row }">
            <span class="mv-mono">{{ formatDate(row.death_date) }}</span>
            <div class="mv-sub">{{ row.death_type }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="native_place" label="原籍" width="110" />
        <el-table-column label="鬼域" width="96">
          <template #default="{ row }">
            <span class="mv-region">{{ row.region }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="118">
          <template #default="{ row }">
            <span
              class="mv-status"
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
        <el-table-column label="业力" width="112">
          <template #default="{ row }">
            <span class="mv-karma" :style="{ color: karmaStyle(row.karma_score).color }">
              {{ row.karma_score > 0 ? '+' : '' }}{{ row.karma_score }}
            </span>
            <span class="mv-sub">{{ karmaStyle(row.karma_score).label }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="current_location" label="现处" width="120" show-overflow-tooltip />
        <el-table-column label="入册时间" width="150">
          <template #default="{ row }">
            <span class="mv-mono">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="96" fixed="right">
          <template #default="{ row }">
            <el-button class="mv-ghost-btn mv-ghost-btn--sm" @click.stop="openDetail(row)">卷宗</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <span class="mv-muted">阴司无此卷宗，或条件过严</span>
        </template>
      </el-table>

      <div class="mv-pager">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :current-page="query.page"
          :page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </div>

    <!-- 卷宗抽屉 -->
    <el-drawer
      v-model="drawerOpen"
      class="mv-drawer"
      size="640px"
      direction="rtl"
      :with-header="false"
      destroy-on-close
    >
      <div v-loading="detailLoading" class="mv-scroll">
        <template v-if="detail">
          <div class="mv-scroll__head">
            <div>
              <h3 class="mv-title">{{ detail.name }}</h3>
              <p class="mv-subtitle mv-mono">{{ detail.soul_no }} · {{ detail.life_book_no }}</p>
            </div>
            <span
              class="mv-status mv-status--lg"
              :style="{
                color: statusStyle(detail.status).color,
                background: statusStyle(detail.status).bg,
                borderColor: statusStyle(detail.status).border,
              }"
            >
              {{ detail.status }}
            </span>
          </div>
          <div class="mv-divider" />

          <el-descriptions :column="2" size="small" border class="mv-desc">
            <el-descriptions-item label="性别年龄">{{ detail.gender }} · {{ detail.age }} 岁</el-descriptions-item>
            <el-descriptions-item label="归属鬼域">{{ detail.region }}鬼域</el-descriptions-item>
            <el-descriptions-item label="生期">{{ formatDate(detail.birth_date) }}</el-descriptions-item>
            <el-descriptions-item label="死期">{{ formatDate(detail.death_date) }}</el-descriptions-item>
            <el-descriptions-item label="原籍">{{ detail.native_place }}</el-descriptions-item>
            <el-descriptions-item label="死因">{{ detail.death_type }}</el-descriptions-item>
            <el-descriptions-item label="业力评分">
              <span :style="{ color: karmaStyle(detail.karma_score).color }">
                {{ detail.karma_score > 0 ? '+' : '' }}{{ detail.karma_score }}（{{ karmaStyle(detail.karma_score).label }}）
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="罪业等级">{{ detail.sin_level }}</el-descriptions-item>
            <el-descriptions-item label="现处">{{ detail.current_location || '—' }}</el-descriptions-item>
            <el-descriptions-item label="入册">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="备注" :span="2">{{ detail.remark || '—' }}</el-descriptions-item>
          </el-descriptions>

          <div class="mv-section">
            <div class="mv-section__head">
              <h4 class="mv-section__title">流转法令</h4>
              <span class="mv-muted mv-hint">依当前状态与阴律授予</span>
            </div>
            <div v-if="allowedActions.length" class="mv-actions">
              <el-button
                v-for="a in allowedActions"
                :key="a.action"
                class="mv-seal-btn mv-seal-btn--sm"
                :loading="acting === a.action"
                @click="runAction(a)"
              >
                {{ a.name }}
                <span class="mv-actions__to">→ {{ a.to }}</span>
              </el-button>
            </div>
            <p v-else class="mv-muted">当前状态无可用法令（或本角色无此权限）。</p>
          </div>

          <div class="mv-section">
            <div class="mv-section__head">
              <h4 class="mv-section__title">三生石 · 生平纪事</h4>
              <span class="mv-muted mv-hint">{{ stoneEvents.length }} 条</span>
            </div>
            <el-timeline v-if="stoneEvents.length" class="mv-stone">
              <el-timeline-item
                v-for="(e, i) in stoneEvents"
                :key="i"
                :timestamp="formatDateTime(e.time)"
                placement="top"
                :color="e.color"
                size="normal"
              >
                <div class="mv-stone__card">
                  <div class="mv-stone__top">
                    <span class="mv-stone__label" :style="{ color: e.color, borderColor: e.color }">{{ e.label }}</span>
                    <span class="mv-stone__title">{{ e.title }}</span>
                  </div>
                  <p class="mv-stone__desc">{{ e.desc }}</p>
                </div>
              </el-timeline-item>
            </el-timeline>
            <p v-else class="mv-muted">此生尚无纪事。</p>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.mv-w-220 {
  width: 220px;
}
.mv-w-150 {
  width: 150px;
}
.mv-w-130 {
  width: 130px;
}
.mv-count {
  font-family: var(--mv-font-title);
  font-style: normal;
  font-size: 15px;
  color: var(--mv-gold);
}
.mv-mono {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: var(--mv-paper-dim);
  font-size: 12px;
}
.mv-sub {
  display: block;
  font-size: 10px;
  color: var(--mv-muted);
  margin-top: 2px;
}
.mv-soul__name {
  font-family: var(--mv-font-title);
  font-size: 14px;
  letter-spacing: 0.1em;
  color: var(--mv-paper);
}
.mv-soul__meta {
  display: block;
  font-size: 10px;
  color: var(--mv-muted);
}
.mv-region {
  font-family: var(--mv-font-title);
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--mv-gold);
}
.mv-status {
  display: inline-block;
  padding: 2px 9px;
  font-family: var(--mv-font-title);
  font-size: 12px;
  letter-spacing: 0.12em;
  border: 1px solid;
  border-radius: 2px;
}
.mv-status--lg {
  padding: 5px 14px;
  font-size: 14px;
}
.mv-karma {
  font-family: var(--mv-font-title);
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}
.mv-pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 4px 2px;
}

/* 抽屉 */
.mv-scroll {
  padding: 22px 24px 30px;
}
.mv-scroll__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.mv-scroll__head h3 {
  font-size: 22px;
  color: #f8f0de;
  text-shadow: 0 0 16px rgba(201, 162, 39, 0.3), 0 1px 3px rgba(0, 0, 0, 0.85);
}
.mv-scroll__head h3::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 15px;
  margin-right: 9px;
  vertical-align: -1px;
  background: linear-gradient(180deg, #c9a227, #b3261e);
}
.mv-desc {
  margin-top: 4px;
}
.mv-section {
  margin-top: 22px;
}
.mv-section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}
.mv-section__title {
  margin: 0;
  font-family: var(--mv-font-title);
  font-size: 14px;
  letter-spacing: 0.2em;
  color: var(--mv-gold);
}
.mv-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.mv-actions__to {
  margin-left: 6px;
  font-size: 10px;
  color: rgba(246, 236, 224, 0.7);
}
.mv-stone {
  padding-left: 4px;
}
.mv-stone__card {
  padding: 9px 12px;
  background: rgba(18, 24, 31, 0.72);
  border: 1px solid rgba(201, 162, 39, 0.16);
  border-left: 2px solid rgba(201, 162, 39, 0.45);
}
.mv-stone__top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mv-stone__label {
  padding: 1px 7px;
  font-family: var(--mv-font-title);
  font-size: 10px;
  letter-spacing: 0.14em;
  border: 1px solid;
  border-radius: 2px;
}
.mv-stone__title {
  font-size: 12px;
  color: var(--mv-paper);
  letter-spacing: 0.06em;
}
.mv-stone__desc {
  margin: 6px 0 0;
  font-size: 11px;
  line-height: 1.7;
  color: var(--mv-paper-dim);
}

:deep(.el-table__row) {
  cursor: pointer;
}
</style>
