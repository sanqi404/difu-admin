<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  confirmReincarnation,
  confirmSoup,
  fetchReincarnationSummary,
  fetchReincarnations,
} from '@/api'
import { onConflict } from '@/api/http'
import type { ReincarnationRecord, ReincarnationSummary } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, karmaStyle } from '@/utils/status'

const { hasPerm } = usePerms()
const auth = useAuthStore()

const PATHS: string[] = ['天道', '人道', '阿修罗道', '畜生道', '饿鬼道', '地狱道']
const PATH_META: Record<string, { alias: string; note: string }> = {
  天道: { alias: '天界', note: '福报最厚，享天福而少苦' },
  人道: { alias: '人间', note: '苦乐参半，最宜修行' },
  阿修罗道: { alias: '修罗', note: '嗔斗不休，福大业重' },
  畜生道: { alias: '傍生', note: '愚痴偿债，任人驱使' },
  饿鬼道: { alias: '饿鬼', note: '饥火焚身，喉细腹大' },
  地狱道: { alias: '地狱', note: '极恶受报，苦无间断' },
}
const QUOTA: Record<string, number> = {
  天道: 6,
  人道: 30,
  阿修罗道: 12,
  畜生道: 18,
  饿鬼道: 15,
  地狱道: 9,
}
const BATCH_SIZE = 6
const QUEUE_STATUS = ['待办理', '待投胎']
const OCCUPY_STATUS = ['待办理', '待投胎', '已投胎']
const SHICHEN = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

type Row = ReincarnationRecord & {
  reinc_no: string
  path: string
  status: string
  soup_confirmed: boolean
  karma_score: number
}

function normalize(r: ReincarnationRecord): Row {
  return {
    ...r,
    reinc_no: r.reinc_no || `LH${r.id}`,
    path: r.path || '人道',
    status: r.status || '待办理',
    soup_confirmed: !!r.soup_confirmed,
    karma_score: r.karma_score ?? 0,
  }
}

interface CertData {
  no: string
  soulName: string
  soulCode: string
  path: string
  targetWorld: string
  karma: number
  issuer: string
  stamp: string
  shichen: string
}

const canSoup = computed(() => hasPerm('reincarnation:soup'))
const canIssue = computed(() => hasPerm('reincarnation:confirm'))

const records = ref<Row[]>([])
const summary = ref<ReincarnationSummary | null>(null)
const loading = ref(false)
const acting = ref(0)
const filter = reactive({ path: '', keyword: '' })
const page = ref(1)
const pageSize = ref(10)
const certOpen = ref(false)
const cert = ref<CertData | null>(null)

async function load() {
  loading.value = true
  try {
    const [pageData, sum] = await Promise.all([
      fetchReincarnations({ page: 1, page_size: 200 }),
      fetchReincarnationSummary(),
    ])
    records.value = (pageData?.items || []).map(normalize)
    summary.value = sum || null
  } catch {
    /* 401/403/409 由全局拦截器统一提示 */
  } finally {
    loading.value = false
  }
}

const queued = computed(() =>
  records.value
    .filter((r) => QUEUE_STATUS.includes(r.status))
    .slice()
    .sort((a, b) => (b.karma_score ?? 0) - (a.karma_score ?? 0) || a.id - b.id),
)

const rankMap = computed(() => {
  const map = new Map<number, number>()
  queued.value.forEach((r, i) => map.set(r.id, i + 1))
  return map
})

const quotaCards = computed(() =>
  PATHS.map((path) => {
    const cap = QUOTA[path] ?? 0
    const used = records.value.filter((r) => r.path === path && OCCUPY_STATUS.includes(r.status)).length
    return {
      path,
      alias: PATH_META[path].alias,
      note: PATH_META[path].note,
      cap,
      used,
      left: Math.max(0, cap - used),
      queued: queued.value.filter((r) => r.path === path).length,
      full: used >= cap,
      percent: cap > 0 ? Math.min(100, Math.round((used / cap) * 100)) : 100,
    }
  }),
)

const quotaTotal = computed(() => quotaCards.value.reduce((a, c) => a + c.cap, 0))
const quotaUsed = computed(() => quotaCards.value.reduce((a, c) => a + c.used, 0))
const quotaLeft = computed(() => Math.max(0, quotaTotal.value - quotaUsed.value))
const soupPending = computed(
  () =>
    summary.value?.soup_pending ??
    records.value.filter((r) => !r.soup_confirmed && QUEUE_STATUS.includes(r.status)).length,
)
const issuedToday = computed(() => {
  const today = new Date().toDateString()
  return records.value.filter((r) => r.reincarnated_at && new Date(r.reincarnated_at).toDateString() === today)
    .length
})
const fullPaths = computed(() => quotaCards.value.filter((c) => c.full).map((c) => c.path))

function isFull(path: string): boolean {
  return fullPaths.value.includes(path)
}

const filteredRows = computed(() => {
  const kw = filter.keyword.trim().toLowerCase()
  return queued.value.filter((row) => {
    if (filter.path && row.path !== filter.path) return false
    if (!kw) return true
    return `${row.soul_name} ${row.reinc_no} ${row.target_world || ''} ${row.path}`.toLowerCase().includes(kw)
  })
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

watch(
  () => [filter.path, filter.keyword, pageSize.value],
  () => {
    page.value = 1
  },
)

function rankOf(row: Row): number | null {
  return rankMap.value.get(row.id) ?? null
}

function batchOf(row: Row): string {
  const rank = rankOf(row)
  if (!rank) return '—'
  return `第 ${Math.floor((rank - 1) / BATCH_SIZE) + 1} 批`
}

function waitText(row: Row): string {
  if (!row.created_at) return '—'
  const start = new Date(row.created_at).getTime()
  if (Number.isNaN(start)) return '—'
  const mins = Math.max(0, Math.floor((Date.now() - start) / 60000))
  const days = Math.floor(mins / 1440)
  const hours = Math.floor((mins % 1440) / 60)
  if (days > 0) return `${days} 天 ${hours} 时辰`
  if (hours > 0) return `${hours} 时辰 ${mins % 60} 分`
  return `${mins} 分`
}

function soupText(row: Row): string {
  if (!row.soup_confirmed) return '未饮'
  return row.soup_operator ? `已饮 · ${row.soup_operator}` : '已饮'
}

function issueReady(row: Row): boolean {
  return row.status === '待投胎' && row.soup_confirmed && !isFull(row.path)
}

function issueTip(row: Row): string {
  if (!row.soup_confirmed) return '未饮孟婆汤，不得投胎'
  if (isFull(row.path)) return `${row.path}名额已满，暂缓签发`
  if (row.status !== '待投胎') return '当前状态不可签发凭证'
  return ''
}

function togglePath(path: string) {
  filter.path = filter.path === path ? '' : path
}

function resetFilter() {
  filter.path = ''
  filter.keyword = ''
}

function statusTone(status: string): string {
  if (status === '待投胎') return '#c9a227'
  if (status === '已投胎') return '#4ce0c3'
  if (status === '已撤销') return '#d4553f'
  return '#a9a294'
}

async function doSoup(row: Row) {
  try {
    await ElMessageBox.confirm(
      `确认为「${row.soul_name}」（${row.reinc_no}）灌饮孟婆汤？饮罢前尘尽忘，档案转入待投胎，六道归属 ${row.path} 不再更改。`,
      '孟婆汤确认',
      { type: 'warning', confirmButtonText: '确认灌汤', cancelButtonText: '再想想' },
    )
  } catch {
    return
  }
  acting.value = row.id
  try {
    await confirmSoup(row.id)
    ElMessage.success(`孟婆汤已确认：${row.soul_name} 前尘尽忘`)
  } catch {
    /* 409 等冲突由全局提示，随后刷新同步状态 */
  } finally {
    acting.value = 0
    await load()
  }
}

async function doIssue(row: Row) {
  if (!row.soup_confirmed) {
    ElMessage.warning('未饮孟婆汤，不得投胎')
    return
  }
  if (isFull(row.path)) {
    ElMessage.warning(`${row.path}名额已满，暂缓签发`)
    return
  }
  const previewNo = certNoOf(row, new Date())
  try {
    await ElMessageBox.confirm(
      `为「${row.soul_name}」（${row.reinc_no}）签发投胎凭证？凭证号 ${previewNo}，六道归属 ${row.path}，目标世界 ${row.target_world || '待定'}。签发后亡魂即刻入轮回，不可撤回。`,
      '投胎凭证签发',
      { type: 'warning', confirmButtonText: '用印签发', cancelButtonText: '暂缓' },
    )
  } catch {
    return
  }
  acting.value = row.id
  try {
    const res = (await confirmReincarnation(row.id)) as unknown as
      | ReincarnationRecord
      | { reincarnation: ReincarnationRecord }
    const record = (res as { reincarnation?: ReincarnationRecord }).reincarnation || (res as ReincarnationRecord)
    cert.value = buildCert(normalize(record || row))
    certOpen.value = true
    ElMessage.success('投胎凭证已签发，轮回门开')
  } catch {
    /* 409 等冲突由全局提示，随后刷新同步状态 */
  } finally {
    acting.value = 0
    await load()
  }
}

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

function certNoOf(row: Row, at: Date): string {
  const dateCode = `${at.getFullYear()}${pad2(at.getMonth() + 1)}${pad2(at.getDate())}`
  const code = (row.reinc_no || `LH${row.id}`).replace(/^LH/, '')
  return `PT-${dateCode}-${code}`
}

function buildCert(row: Row): CertData {
  const at = new Date(row.reincarnated_at || row.soup_at || Date.now())
  const hod = at.getHours()
  return {
    no: certNoOf(row, at),
    soulName: row.soul_name,
    soulCode: row.reinc_no,
    path: row.path,
    targetWorld: row.target_world || '待定',
    karma: row.karma_score ?? 0,
    issuer: auth.profile?.real_name || auth.profile?.username || '轮回司值司',
    stamp: `${at.getFullYear()}年${pad2(at.getMonth() + 1)}月${pad2(at.getDate())}日 ${pad2(hod)}:${pad2(at.getMinutes())}`,
    shichen: `${SHICHEN[Math.floor(((hod + 1) % 24) / 2)]}时`,
  }
}

function printCert() {
  window.print()
}

let offConflict: (() => void) | null = null

onMounted(() => {
  load()
  offConflict = onConflict(() => {
    load()
  })
})

onBeforeUnmount(() => {
  offConflict?.()
})
</script>

<template>
  <div class="mv-page rc-page">
    <div class="mv-panel rc-hero">
      <div class="rc-hero__main">
        <h2 class="rc-title">轮回司 · 六道投胎</h2>
        <p class="mv-sub">掌六道配额、亡魂投胎排队、孟婆汤确认与投胎凭证签发</p>
      </div>
      <div class="rc-hero__stats">
        <div class="rc-stat">
          <span class="rc-stat__label">六道在册</span>
          <span class="rc-stat__value mv-mono">{{ quotaUsed }} / {{ quotaTotal }}</span>
        </div>
        <div class="rc-stat">
          <span class="rc-stat__label">剩余名额</span>
          <span class="rc-stat__value mv-mono">{{ quotaLeft }}</span>
        </div>
        <div class="rc-stat">
          <span class="rc-stat__label">待饮孟婆汤</span>
          <span class="rc-stat__value rc-warn mv-mono">{{ soupPending }}</span>
        </div>
        <div class="rc-stat">
          <span class="rc-stat__label">今日已投胎</span>
          <span class="rc-stat__value mv-mono">{{ issuedToday }}</span>
        </div>
      </div>
    </div>

    <div class="mv-panel">
      <div class="rc-panel__head">
        <h3>六道配额</h3>
        <span class="mv-sub">点击道名筛选排队列表；满额一道封门，不再签发凭证</span>
      </div>
      <div class="rc-quota-grid">
        <div
          v-for="c in quotaCards"
          :key="c.path"
          class="rc-quota"
          :class="{ 'is-active': filter.path === c.path, 'is-full': c.full }"
          @click="togglePath(c.path)"
        >
          <el-progress
            type="circle"
            :percentage="c.percent"
            :width="78"
            :stroke-width="7"
            :color="c.full ? '#d4553f' : '#c9a227'"
          >
            <template #default>
              <span class="rc-quota__pct mv-mono">{{ c.percent }}%</span>
            </template>
          </el-progress>
          <div class="rc-quota__body">
            <div class="rc-quota__name">
              {{ c.path }}<em>{{ c.alias }}</em>
              <span v-if="c.full" class="rc-quota__tag">名额已满</span>
            </div>
            <div class="rc-quota__nums mv-mono">已用 {{ c.used }} / 上限 {{ c.cap }}</div>
            <div class="rc-quota__left" :class="{ 'is-full': c.full }">剩余 {{ c.left }} 名 · 排队 {{ c.queued }} 魂</div>
            <div class="rc-quota__note">{{ c.note }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="mv-panel mv-panel--table">
      <div class="rc-panel__head">
        <h3>投胎排队</h3>
        <span class="mv-sub">按业力分由高至低排位，每 {{ BATCH_SIZE }} 魂一批受理</span>
      </div>
      <div class="mv-toolbar rc-toolbar">
        <el-select v-model="filter.path" placeholder="全部六道" clearable style="width: 152px">
          <el-option v-for="p in PATHS" :key="p" :label="isFull(p) ? p + '（满）' : p" :value="p" />
        </el-select>
        <el-input v-model="filter.keyword" placeholder="搜魂号 / 姓名 / 目标世界" clearable style="width: 232px" />
        <button class="mv-ghost-btn" @click="resetFilter">重置</button>
        <div class="mv-spacer" />
        <span class="mv-count">共 {{ filteredRows.length }} 魂待签</span>
        <button class="mv-ghost-btn" :disabled="loading" @click="load">刷新</button>
      </div>
      <el-table
        v-loading="loading"
        :data="pagedRows"
        row-key="id"
        class="rc-table"
        empty-text="轮回司门前无魂候签"
      >
        <el-table-column label="排位" width="72">
          <template #default="{ row }">
            <span class="rc-rank mv-mono">{{ rankOf(row) ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="魂号 / 姓名" min-width="158">
          <template #default="{ row }">
            <span class="mv-mono">{{ row.reinc_no }}</span>
            <div class="rc-soul">{{ row.soul_name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="目标道" width="126">
          <template #default="{ row }">
            <span class="rc-path">{{ row.path }}</span>
            <div class="mv-sub">{{ row.target_world || '待定' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="业力" width="92">
          <template #default="{ row }">
            <span class="mv-mono" :style="{ color: karmaStyle(row.karma_score).color }">{{ row.karma_score }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="rc-status" :style="{ color: statusTone(row.status), borderColor: statusTone(row.status) }">
              {{ row.status }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="排队时长" width="124">
          <template #default="{ row }">
            <span class="mv-sub">{{ waitText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="预计批次" width="98">
          <template #default="{ row }">
            <span class="mv-mono">{{ batchOf(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="孟婆汤" width="150">
          <template #default="{ row }">
            <span :class="row.soup_confirmed ? 'rc-soup is-done' : 'rc-soup'">{{ soupText(row) }}</span>
            <div v-if="row.soup_at" class="mv-sub">{{ formatDateTime(row.soup_at) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="212" fixed="right">
          <template #default="{ row }">
            <div class="rc-ops">
              <el-tooltip v-if="canSoup && !row.soup_confirmed" content="灌饮孟婆汤，前尘尽忘后方可投胎" placement="top">
                <button class="mv-seal-btn" :disabled="acting === row.id" @click="doSoup(row)">孟婆汤确认</button>
              </el-tooltip>
              <span v-else-if="row.soup_confirmed" class="mv-sub rc-soup-done">汤已饮</span>
              <el-tooltip v-else content="无孟婆汤办理权限" placement="top">
                <button class="mv-ghost-btn" disabled>孟婆汤确认</button>
              </el-tooltip>
              <el-tooltip :content="issueTip(row) || '签发投胎凭证并打印'" placement="top">
                <span class="rc-issue-wrap">
                  <button
                    class="mv-seal-btn"
                    :disabled="!canIssue || !issueReady(row) || acting === row.id"
                    @click="doIssue(row)"
                  >
                    签发凭证
                  </button>
                </span>
              </el-tooltip>
            </div>
            <div v-if="issueTip(row)" class="rc-tip">{{ issueTip(row) }}</div>
          </template>
        </el-table-column>
      </el-table>
      <div class="rc-pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          background
          :total="filteredRows.length"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
        />
      </div>
    </div>

    <el-dialog v-model="certOpen" title="投胎凭证 · 预览" width="528px" class="rc-cert-dialog" append-to-body>
      <div v-if="cert" class="rc-cert">
        <div class="rc-cert__head">
          <span class="rc-cert__office">酆都轮回司</span>
          <h4>投 胎 凭 证</h4>
          <span class="rc-cert__no mv-mono">凭证号　{{ cert.no }}</span>
        </div>
        <table class="rc-cert__table">
          <tbody>
            <tr>
              <th>亡魂姓名</th>
              <td>{{ cert.soulName }}</td>
              <th>魂号</th>
              <td class="mv-mono">{{ cert.soulCode }}</td>
            </tr>
            <tr>
              <th>六道归属</th>
              <td class="rc-cert__path">{{ cert.path }}</td>
              <th>目标世界</th>
              <td>{{ cert.targetWorld }}</td>
            </tr>
            <tr>
              <th>业力分</th>
              <td class="mv-mono">{{ cert.karma }}</td>
              <th>签发时辰</th>
              <td>{{ cert.stamp }}（{{ cert.shichen }}）</td>
            </tr>
            <tr>
              <th>签发人</th>
              <td>{{ cert.issuer }}</td>
              <th>孟婆汤</th>
              <td>已饮 · 前尘尽忘</td>
            </tr>
          </tbody>
        </table>
        <p class="rc-cert__text">
          兹准亡魂 {{ cert.soulName }} 循 {{ cert.path }} 入轮回，投往{{ cert.targetWorld }}。持此凭证过奈何桥，不得阻滞、不得回望。
        </p>
        <div class="rc-cert__foot">
          <div class="rc-cert__seal">轮回司印</div>
          <div class="rc-cert__sign">
            <span>签发：{{ cert.issuer }}</span>
            <span class="mv-mono">{{ cert.stamp }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="mv-ghost-btn" @click="certOpen = false">关闭</button>
        <button class="mv-seal-btn" @click="printCert">打印凭证</button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.rc-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.rc-hero {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 16px 20px;
  border-left: 3px solid var(--mv-cinnabar);
}

.rc-hero__main {
  min-width: 220px;
}

.rc-title {
  margin: 0 0 4px;
  font-family: var(--mv-font-title);
  font-size: 20px;
  letter-spacing: 2px;
  color: var(--mv-ink);
}

.rc-hero__stats {
  margin-left: auto;
  display: flex;
  gap: 26px;
}

.rc-stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 92px;
}

.rc-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 1px;
}

.rc-stat__value {
  font-size: 20px;
  color: var(--mv-gold);
}

.rc-stat__value.rc-warn {
  color: var(--mv-cinnabar);
}

.rc-panel__head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 14px 20px 4px;
}

.rc-panel__head h3 {
  margin: 0;
  font-family: var(--mv-font-title);
  font-size: 15px;
  letter-spacing: 1px;
  color: var(--mv-ink);
}

.rc-quota-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(268px, 1fr));
  gap: 12px;
  padding: 12px 20px 18px;
}

.rc-quota {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid rgba(201, 162, 39, 0.22);
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.16);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.rc-quota:hover {
  border-color: rgba(201, 162, 39, 0.5);
}

.rc-quota.is-active {
  border-color: var(--mv-phosphor);
  background: rgba(76, 224, 195, 0.08);
}

.rc-quota.is-full {
  border-color: rgba(212, 85, 63, 0.45);
  background: rgba(212, 85, 63, 0.06);
}

.rc-quota__pct {
  font-size: 13px;
  color: var(--mv-paper);
}

.rc-quota__body {
  flex: 1;
  min-width: 0;
}

.rc-quota__name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--mv-font-title);
  font-size: 15px;
  color: var(--mv-ink);
}

.rc-quota__name em {
  font-style: normal;
  font-size: 11px;
  color: var(--mv-muted);
}

.rc-quota__tag {
  margin-left: auto;
  padding: 1px 6px;
  font-size: 11px;
  color: #f0c9c3;
  border: 1px solid rgba(212, 85, 63, 0.6);
  border-radius: 2px;
  background: rgba(212, 85, 63, 0.18);
}

.rc-quota__nums {
  margin-top: 4px;
  font-size: 13px;
  color: var(--mv-gold);
}

.rc-quota__left {
  font-size: 12px;
  color: var(--mv-phosphor);
}

.rc-quota__left.is-full {
  color: #d4553f;
}

.rc-quota__note {
  margin-top: 3px;
  font-size: 11px;
  color: var(--mv-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rc-toolbar {
  padding: 10px 20px;
}

.rc-rank {
  display: inline-block;
  min-width: 24px;
  padding: 0 4px;
  text-align: center;
  font-size: 13px;
  color: var(--mv-gold);
  border-bottom: 1px solid rgba(201, 162, 39, 0.35);
}

.rc-soul {
  margin-top: 2px;
  font-family: var(--mv-font-title);
  font-size: 14px;
  color: var(--mv-ink);
}

.rc-path {
  font-size: 13px;
  color: var(--mv-ink);
}

.rc-status {
  display: inline-block;
  padding: 1px 7px;
  font-size: 12px;
  border: 1px solid;
  border-radius: 2px;
}

.rc-soup {
  font-size: 12px;
  color: var(--mv-cinnabar);
}

.rc-soup.is-done,
.rc-soup-done {
  color: var(--mv-phosphor);
  font-size: 12px;
}

.rc-ops {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rc-issue-wrap {
  display: inline-block;
}

.rc-tip {
  margin-top: 4px;
  font-size: 11px;
  color: var(--mv-muted);
}

.rc-pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 20px 16px;
}

.rc-cert {
  padding: 18px 20px 22px;
  color: #2b2419;
  background: #efe8d6;
  background-image: radial-gradient(rgba(120, 96, 48, 0.12) 1px, transparent 1px);
  background-size: 9px 9px;
  border: 1px solid #b9a97f;
}

.rc-cert__head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-bottom: 10px;
  border-bottom: 2px double #8c1f16;
}

.rc-cert__office {
  font-size: 12px;
  letter-spacing: 6px;
  color: #8c1f16;
}

.rc-cert__head h4 {
  margin: 2px 0;
  font-family: var(--mv-font-title);
  font-size: 22px;
  letter-spacing: 8px;
}

.rc-cert__no {
  font-size: 12px;
  color: #6b5b3a;
}

.rc-cert__table {
  width: 100%;
  margin-top: 12px;
  border-collapse: collapse;
  font-size: 13px;
}

.rc-cert__table th,
.rc-cert__table td {
  padding: 6px 8px;
  border: 1px solid #b9a97f;
  text-align: left;
}

.rc-cert__table th {
  width: 20%;
  font-weight: normal;
  color: #6b5b3a;
  background: rgba(140, 31, 22, 0.05);
}

.rc-cert__path {
  font-family: var(--mv-font-title);
  color: #8c1f16;
}

.rc-cert__text {
  margin: 12px 0;
  font-size: 13px;
  line-height: 1.9;
  text-indent: 2em;
}

.rc-cert__foot {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: 16px;
}

.rc-cert__seal {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 84px;
  height: 84px;
  font-family: var(--mv-font-title);
  font-size: 13px;
  letter-spacing: 2px;
  color: #8c1f16;
  border: 2px solid #8c1f16;
  border-radius: 50%;
  transform: rotate(-12deg);
  opacity: 0.86;
}

.rc-cert__sign {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #4a3f2a;
  text-align: right;
}

@media print {
  body * {
    visibility: hidden !important;
  }

  .rc-cert,
  .rc-cert * {
    visibility: visible !important;
  }

  .rc-cert {
    position: fixed;
    left: 0;
    top: 0;
    width: 100%;
    border: none;
    background: #fff;
  }
}
</style>
