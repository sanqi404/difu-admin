<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createTrial, fetchTrials, fetchTrialSummary, handleTrial } from '@/api'
import type { SoulItem, TrialRecord, TrialSummary } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime } from '@/utils/status'
import SoulPicker from '@/components/SoulPicker.vue'

const { hasPerm } = usePerms()
const router = useRouter()

const COURT_NAMES = [
  '一殿秦广王', '二殿楚江王', '三殿宋帝王', '四殿仵官王', '五殿阎罗王',
  '六殿卞城王', '七殿泰山王', '八殿都市王', '九殿平等王', '十殿转轮王',
]
const TRIAL_STATUS = ['待审', '审理中', '已结案', '打回重审']

const canCreate = computed(() => hasPerm('trial:create'))
const canHandle = computed(() => hasPerm('trial:handle'))
const canVerdict = computed(() => hasPerm('trial:verdict'))

type TabKey = 'queue' | 'hearing' | 'record' | 'appeal'

const tab = ref<TabKey>('queue')
const loading = ref(false)
const rows = ref<TrialRecord[]>([])
const total = ref(0)
const summary = ref<TrialSummary | null>(null)
const query = reactive({
  keyword: '',
  status: '',
  court_level: undefined as number | undefined,
  page: 1,
  page_size: 10,
})

const tabStatus = computed(() => {
  if (tab.value === 'queue') return '待审'
  if (tab.value === 'hearing') return '审理中'
  if (tab.value === 'record') return '已结案'
  return ''
})

const tabVerdict = computed(() => (tab.value === 'appeal' ? '打回重审' : ''))

const tabs = computed(() => [
  { key: 'queue' as TabKey, label: '待审队列', count: countStatus('待审') },
  { key: 'hearing' as TabKey, label: '开审中', count: countStatus('审理中') },
  { key: 'record' as TabKey, label: '会审记录', count: countStatus('已结案') },
  { key: 'appeal' as TabKey, label: '申诉异议', count: summary.value?.reopened ?? 0 },
])

function countStatus(status: string) {
  return summary.value?.by_status?.find((s) => s.status === status)?.count ?? 0
}

function courtCount(level: number) {
  return summary.value?.by_court?.find((c) => c.level === level)?.count ?? 0
}

function statusStyle(status: string) {
  switch (status) {
    case '审理中':
      return { color: '#4ce0c3', bg: 'rgba(76,224,195,0.12)', border: 'rgba(76,224,195,0.4)' }
    case '已结案':
      return { color: '#8f9a90', bg: 'rgba(143,154,144,0.12)', border: 'rgba(143,154,144,0.35)' }
    case '打回重审':
      return { color: '#d9a13b', bg: 'rgba(217,161,59,0.14)', border: 'rgba(217,161,59,0.45)' }
    default:
      return { color: '#c9a227', bg: 'rgba(201,162,39,0.12)', border: 'rgba(201,162,39,0.42)' }
  }
}

function verdictStyle(verdict: string) {
  if (verdict === '有罪') return { color: '#e05b45', border: 'rgba(224,91,69,0.5)' }
  if (verdict === '无罪' || verdict === '还阳') return { color: '#4ce0c3', border: 'rgba(76,224,195,0.45)' }
  if (verdict === '发配枉死城') return { color: '#c0763f', border: 'rgba(192,118,63,0.5)' }
  return { color: '#d9a13b', border: 'rgba(217,161,59,0.45)' }
}

async function loadSummary() {
  try {
    summary.value = await fetchTrialSummary()
  } catch {
    summary.value = null
  }
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchTrials({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      status: query.status || tabStatus.value || undefined,
      verdict: tabVerdict.value || undefined,
      court_level: query.court_level,
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
  query.status = ''
  query.page = 1
  loadList()
}

function pickCourt(level: number) {
  query.court_level = query.court_level === level ? undefined : level
  query.page = 1
  loadList()
}

function search() {
  query.page = 1
  loadList()
}

function resetQuery() {
  query.keyword = ''
  query.status = ''
  query.court_level = undefined
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

/* ---------------- 开堂 ---------------- */
const acting = ref<number | null>(null)

async function openCourt(row: TrialRecord) {
  acting.value = row.id
  try {
    await handleTrial(row.id)
    ElMessage.success('已开堂，惊堂木落')
    await refresh()
    goWorkbench(row.id)
  } catch {
    await refresh()
  } finally {
    acting.value = null
  }
}

function goWorkbench(id: number) {
  router.push({ path: '/trial/court', query: { id: String(id) } })
}

/* ---------------- 提审立案 ---------------- */
const createDialog = reactive({ open: false, submitting: false })
const createForm = reactive({
  soul_id: null as number | null,
  soul: null as SoulItem | null,
  court_level: 1,
  guilt_desc: '',
})

function openCreate(level?: number) {
  createForm.soul_id = null
  createForm.soul = null
  createForm.court_level = level || query.court_level || 1
  createForm.guilt_desc = ''
  createDialog.open = true
}

async function submitCreate() {
  if (!createForm.soul_id || !createForm.soul) {
    ElMessage.warning('请先检索并选定亡魂')
    return
  }
  createDialog.submitting = true
  try {
    await createTrial({
      soul_id: createForm.soul_id,
      court_level: createForm.court_level,
      guilt_desc: createForm.guilt_desc || undefined,
    })
    ElMessage.success('已立案送审，候堂')
    createDialog.open = false
    await refresh()
  } catch {
    await refresh()
  } finally {
    createDialog.submitting = false
  }
}

/* ---------------- 申诉异议：重新提审 ---------------- */
async function reopenTrial(row: TrialRecord) {
  const level = row.next_court_level || row.court_level
  try {
    await ElMessageBox.confirm(
      `就 ${row.soul_name} 之案（原判：打回重审）重新提审至「${COURT_NAMES[level - 1] || '一殿秦广王'}」？将新建审判记录。`,
      '重 新 提 审',
      { confirmButtonText: '提 审', cancelButtonText: '再看看' },
    )
  } catch {
    return
  }
  try {
    await createTrial({ soul_id: row.soul_id, court_level: level, guilt_desc: row.guilt_desc || undefined })
    ElMessage.success('已重新立卷')
    await refresh()
  } catch {
    await refresh()
  }
}

onMounted(async () => {
  await loadSummary()
  // 待审队列为空但有在审案卷时，直接落到「开审中」，避免开局空卷
  if (tab.value === 'queue' && countStatus('待审') === 0 && countStatus('审理中') > 0) {
    tab.value = 'hearing'
  }
  await loadList()
})
</script>

<template>
  <div class="mv-page">
    <!-- 概览 -->
    <div class="mv-panel tl-overview">
      <div class="tl-stats">
        <div class="tl-stat">
          <span class="tl-stat__label">在卷案件</span>
          <span class="tl-stat__value">{{ summary?.total ?? 0 }}</span>
        </div>
        <div class="tl-stat">
          <span class="tl-stat__label">待审</span>
          <span class="tl-stat__value tl-stat__value--gold">{{ countStatus('待审') }}</span>
        </div>
        <div class="tl-stat">
          <span class="tl-stat__label">审理中</span>
          <span class="tl-stat__value tl-stat__value--teal">{{ countStatus('审理中') }}</span>
        </div>
        <div class="tl-stat">
          <span class="tl-stat__label">已结案</span>
          <span class="tl-stat__value">{{ countStatus('已结案') }}</span>
        </div>
        <div class="tl-stat">
          <span class="tl-stat__label">申诉异议</span>
          <span class="tl-stat__value tl-stat__value--warn">{{ summary?.reopened ?? 0 }}</span>
        </div>
      </div>
      <div class="tl-actions">
        <el-button v-if="canCreate" class="mv-seal-btn mv-seal-btn--sm" @click="openCreate()">提 审 立 案</el-button>
        <el-button class="mv-ghost-btn" @click="refresh">刷 新 卷 宗</el-button>
      </div>
    </div>

    <!-- 十殿 -->
    <div class="mv-panel tl-courts">
      <div class="tl-courts__head">
        <span class="mv-subtitle">十殿次第</span>
        <span class="mv-muted">点选殿次筛阅该殿卷宗</span>
      </div>
      <div class="tl-courts__grid">
        <button
          v-for="level in 10"
          :key="level"
          type="button"
          class="tl-court"
          :class="{ 'is-active': query.court_level === level, 'is-fifth': level === 5 }"
          @click="pickCourt(level)"
        >
          <span class="tl-court__name">{{ COURT_NAMES[level - 1] }}</span>
          <span class="tl-court__count">{{ courtCount(level) }}</span>
        </button>
      </div>
    </div>

    <div class="mv-panel mv-panel--table">
      <div class="tl-tabs">
        <button
          v-for="item in tabs"
          :key="item.key"
          class="tl-tab"
          :class="{ 'is-active': tab === item.key }"
          type="button"
          @click="switchTab(item.key)"
        >
          {{ item.label }}
          <em class="tl-tab__count">{{ item.count }}</em>
        </button>
      </div>

      <div class="mv-toolbar tl-filters">
        <div class="mv-toolbar__left">
          <el-input
            v-model="query.keyword"
            class="tl-w220"
            placeholder="案卷号 / 亡魂姓名"
            clearable
            @keyup.enter="search"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="query.court_level" class="tl-w150" placeholder="殿次" clearable>
            <el-option v-for="level in 10" :key="level" :label="COURT_NAMES[level - 1]" :value="level" />
          </el-select>
          <el-select v-model="query.status" class="tl-w130" placeholder="审理状态" clearable>
            <el-option v-for="s in TRIAL_STATUS" :key="s" :label="s" :value="s" />
          </el-select>
          <el-button class="mv-seal-btn mv-seal-btn--sm" @click="search">查 阅</el-button>
          <el-button class="mv-ghost-btn" @click="resetQuery">重置</el-button>
        </div>
        <div class="mv-toolbar__right">
          <span class="mv-muted">共 <em class="mv-count">{{ total }}</em> 卷</span>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" row-key="id" class="mv-table tl-table" height="calc(100vh - 452px)">
        <el-table-column label="案卷号" width="150">
          <template #default="{ row }"><span class="mv-mono">{{ row.trial_no }}</span></template>
        </el-table-column>
        <el-table-column prop="soul_name" label="亡魂" width="100" />
        <el-table-column label="殿次" width="128">
          <template #default="{ row }">
            <span :class="row.court_level === 5 ? 'tl-court-tag tl-court-tag--fifth' : 'tl-court-tag'">
              {{ COURT_NAMES[row.court_level - 1] || `第${row.court_level}殿` }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <span
              class="tl-badge"
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
        <el-table-column label="判词" width="120">
          <template #default="{ row }">
            <span
              v-if="row.verdict"
              class="tl-verdict"
              :style="{ color: verdictStyle(row.verdict).color, borderColor: verdictStyle(row.verdict).border }"
            >
              {{ row.verdict }}
            </span>
            <span v-else class="mv-sub">未判</span>
          </template>
        </el-table-column>
        <el-table-column prop="guilt_desc" label="罪由" min-width="180" show-overflow-tooltip />
        <el-table-column prop="judge_name" label="主审" width="100" />
        <el-table-column label="开堂 / 结案" width="152">
          <template #default="{ row }">
            <div class="mv-mono mv-sub">{{ formatDateTime(row.started_at) }}</div>
            <div class="mv-mono mv-sub">{{ formatDateTime(row.closed_at) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <div class="tl-row-actions">
              <el-button v-if="canHandle && row.status === '待审'" link class="tl-link tl-link--ok" :loading="acting === row.id" @click="openCourt(row)">
                开堂
              </el-button>
              <el-button v-if="canVerdict && ['待审', '审理中'].includes(row.status)" link class="tl-link tl-link--gold" @click="goWorkbench(row.id)">
                审判台
              </el-button>
              <el-button v-if="canCreate && row.verdict === '打回重审'" link class="tl-link tl-link--warn" @click="reopenTrial(row)">
                重新提审
              </el-button>
              <el-button v-if="row.status === '已结案'" link class="tl-link" @click="goWorkbench(row.id)">查阅</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="tl-empty">殿前无案，静候亡魂</div>
        </template>
      </el-table>

      <div class="tl-pager">
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

    <!-- 提审立案 -->
    <el-dialog v-model="createDialog.open" title="判官司 · 提审立案" width="540px" destroy-on-close>
      <div class="tl-form">
        <div class="tl-field">
          <label>亡魂</label>
          <SoulPicker v-model="createForm.soul_id" @change="(s: SoulItem | null) => (createForm.soul = s)" />
        </div>
        <div class="tl-field">
          <label>送审殿次</label>
          <el-select v-model="createForm.court_level" class="tl-full">
            <el-option v-for="level in 10" :key="level" :label="COURT_NAMES[level - 1]" :value="level" />
          </el-select>
        </div>
        <div class="tl-field">
          <label>罪由</label>
          <el-input v-model="createForm.guilt_desc" type="textarea" :rows="3" maxlength="200" show-word-limit placeholder="略述亡魂生前功过" />
        </div>
        <div class="tl-note">立案后亡魂状态转为「审判中」，并生成「待审」案卷。</div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" @click="createDialog.open = false">取 消</el-button>
        <el-button class="mv-seal-btn mv-seal-btn--sm" :loading="createDialog.submitting" @click="submitCreate">立 案</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tl-overview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  flex-wrap: wrap;
}
.tl-stats {
  display: flex;
  gap: 26px;
  flex-wrap: wrap;
}
.tl-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.tl-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.1em;
}
.tl-stat__value {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 22px;
  color: var(--mv-paper);
}
.tl-stat__value--gold {
  color: var(--mv-gold);
}
.tl-stat__value--teal {
  color: var(--mv-phosphor);
}
.tl-stat__value--warn {
  color: #d9a13b;
}
.tl-actions {
  display: flex;
  gap: 8px;
}
.tl-courts {
  padding: 12px 18px 14px;
  margin-top: 12px;
}
.tl-courts__head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
}
.tl-courts__grid {
  display: grid;
  grid-template-columns: repeat(10, minmax(0, 1fr));
  gap: 8px;
}
.tl-court {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 6px;
  background: rgba(232, 227, 214, 0.03);
  border: 1px solid rgba(232, 227, 214, 0.12);
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.18s;
}
.tl-court:hover {
  border-color: rgba(201, 162, 39, 0.5);
}
.tl-court.is-active {
  border-color: var(--mv-cinnabar);
  background: rgba(179, 38, 30, 0.12);
}
.tl-court.is-fifth {
  box-shadow: inset 0 -2px 0 rgba(201, 162, 39, 0.35);
}
.tl-court__name {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 12px;
  color: var(--mv-paper);
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tl-court__count {
  font-size: 16px;
  color: var(--mv-gold);
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
}
.tl-tabs {
  display: flex;
  gap: 6px;
  padding: 4px 18px 0;
  border-bottom: 1px solid rgba(232, 227, 214, 0.08);
}
.tl-tab {
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
.tl-tab.is-active {
  color: var(--mv-gold);
}
.tl-tab.is-active::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: -1px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--mv-cinnabar), transparent);
}
.tl-tab__count {
  margin-left: 6px;
  font-size: 11px;
  font-style: normal;
  color: var(--mv-muted);
}
.tl-filters {
  border-bottom: none;
}
.tl-w220 {
  width: 220px;
}
.tl-w150 {
  width: 150px;
}
.tl-w130 {
  width: 130px;
}
.tl-full {
  width: 100%;
}
.tl-court-tag {
  font-size: 12px;
  color: var(--mv-paper);
}
.tl-court-tag--fifth {
  color: var(--mv-gold);
}
.tl-badge {
  padding: 1px 8px;
  font-size: 12px;
  border: 1px solid;
  border-radius: 2px;
}
.tl-verdict {
  padding: 1px 6px;
  font-size: 12px;
  border: 1px solid;
  border-radius: 2px;
}
.tl-row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tl-link {
  color: var(--mv-muted);
  font-size: 12px;
}
.tl-link--ok {
  color: var(--mv-phosphor);
}
.tl-link--gold {
  color: var(--mv-gold);
}
.tl-link--warn {
  color: #d9a13b;
}
.tl-pager {
  display: flex;
  justify-content: flex-end;
  padding: 10px 18px 4px;
}
.tl-empty {
  padding: 26px 0;
  color: var(--mv-muted);
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  letter-spacing: 0.16em;
}
.tl-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.tl-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tl-field label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.12em;
}
.tl-note {
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--mv-muted);
  border-left: 2px solid rgba(201, 162, 39, 0.5);
  background: rgba(201, 162, 39, 0.06);
}
@media (max-width: 1400px) {
  .tl-courts__grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}
</style>
