<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createKarmaRecord,
  fetchKarmaRecords,
  fetchKarmaSummary,
  fetchSoulKarma,
  fetchSouls,
  scoreKarma,
} from '@/api'
import type { KarmaRecord, KarmaSummary, SoulItem } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime, karmaStyle, statusStyle } from '@/utils/status'

const { hasPerm } = usePerms()

/* ---------------- 常量 ---------------- */
const KARMA_TYPES = ['善', '恶', '中性'] as const
const EVIL_CATEGORIES = ['杀生', '偷盗', '邪淫', '妄语', '两舌', '恶口', '绮语', '贪欲', '嗔恚', '邪见']
const GOOD_CATEGORIES = ['布施', '持戒', '放生', '孝养', '救人', '修桥补路']
const SOURCES = ['孽镜台', '城隍上报', '生死簿核定', '人工录入']
const QUEUE_STATUSES = ['已过境', '待审', '已备案']

interface SoulKarmaProfile {
  soul_id: number
  soul_name: string
  current_score: number
  sin_level: string
  computed_score: number
  items: KarmaRecord[]
}

interface ScoreResult {
  soul_id: number
  soul_name: string
  before: { score: number; sin_level: string }
  after: { score: number; sin_level: string }
  record_count: number
}

/* ---------------- 权限 ---------------- */
const canScore = computed(() => hasPerm('karma:score'))
const canCreate = computed(() => hasPerm('karma:create'))

/* ---------------- 页签 ---------------- */
const tab = ref<'mirror' | 'ledger'>('mirror')

/* ---------------- 概览 ---------------- */
const summary = ref<KarmaSummary | null>(null)

function typeCount(type: string) {
  return summary.value?.by_type?.find((t) => t.type === type)?.count ?? 0
}

const topCategories = computed(() => {
  const list = summary.value?.by_category ?? []
  const max = list.reduce((acc, cur) => Math.max(acc, cur.count), 0)
  return list.slice(0, 6).map((c) => ({
    ...c,
    percent: max ? Math.round((c.count / max) * 100) : 0,
  }))
})

/* ---------------- 待照队列 ---------------- */
const queueLoading = ref(false)
const queue = ref<SoulItem[]>([])
const queueKeyword = ref('')
const queueStatus = ref('已过境')

const selectedId = ref<number | null>(null)
const profile = ref<SoulKarmaProfile | null>(null)
const profileLoading = ref(false)
const scoring = ref(false)

const selectedSoul = computed(() => queue.value.find((s) => s.id === selectedId.value) || null)

const diff = computed(() => {
  if (!profile.value) return 0
  return (profile.value.computed_score || 0) - (profile.value.current_score || 0)
})

const canMirrorScore = computed(
  () => canScore.value && !!profile.value && (profile.value.items?.length ?? 0) > 0 && !scoring.value,
)

async function loadQueue() {
  queueLoading.value = true
  try {
    const statuses = queueStatus.value ? [queueStatus.value] : QUEUE_STATUSES
    const results = await Promise.all(
      statuses.map((status) =>
        fetchSouls({ page: 1, page_size: 50, keyword: queueKeyword.value || undefined, status }),
      ),
    )
    const merged: SoulItem[] = []
    const seen = new Set<number>()
    results.forEach((res) => {
      ;(res?.items ?? []).forEach((item) => {
        if (seen.has(item.id)) return
        seen.add(item.id)
        merged.push(item)
      })
    })
    merged.sort((a, b) => (a.karma_score || 0) - (b.karma_score || 0))
    queue.value = merged
    if (selectedId.value && !merged.some((s) => s.id === selectedId.value)) {
      selectedId.value = null
      profile.value = null
    }
    if (!selectedId.value && merged.length) selectSoul(merged[0])
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '待照队列读取失败')
  } finally {
    queueLoading.value = false
  }
}

async function loadProfile(soulId: number) {
  profileLoading.value = true
  try {
    const res = await fetchSoulKarma(soulId)
    const raw = res as unknown as Partial<SoulKarmaProfile> & {
      soul?: { id: number; name: string; karma_score: number; sin_level: string }
      soul_name?: string
      current_score?: number
    }
    profile.value = {
      soul_id: soulId,
      soul_name: raw.soul_name || raw.soul?.name || '',
      current_score: raw.current_score ?? raw.soul?.karma_score ?? 0,
      sin_level: raw.sin_level || raw.soul?.sin_level || '无',
      computed_score: raw.computed_score ?? 0,
      items: (raw.items as KarmaRecord[]) || [],
    }
  } catch (err) {
    profile.value = null
    ElMessage.error((err as { message?: string })?.message || '孽镜照业失败')
  } finally {
    profileLoading.value = false
  }
}

function selectSoul(soul: SoulItem) {
  if (selectedId.value === soul.id) return
  selectedId.value = soul.id
  tab.value = 'mirror'
  loadProfile(soul.id)
}

/* ---------------- 照镜评分 ---------------- */
const scoreDialog = ref(false)
const scoreResult = ref<ScoreResult | null>(null)

async function doScore() {
  if (!profile.value) return
  const name = profile.value.soul_name || selectedSoul.value?.name || ''
  try {
    await ElMessageBox.confirm(
      `孽镜照业，将按该亡魂全部业力流水重算总分与罪孽等级：\n${name}　档案分 ${profile.value.current_score} → 镜像分 ${profile.value.computed_score}。\n\n重算将覆盖亡魂主档的业力分与罪孽等级，并写入评分流水与阴律日志。`,
      '孽镜台开镜',
      { confirmButtonText: '开镜照业', cancelButtonText: '再等等', type: 'warning' },
    )
  } catch {
    return
  }
  scoring.value = true
  try {
    const res = (await scoreKarma(profile.value.soul_id)) as unknown as ScoreResult
    scoreResult.value = res
    scoreDialog.value = true
    ElMessage.success('孽镜台评分完成')
    await Promise.all([loadProfile(profile.value.soul_id), loadQueue(), loadSummary()])
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '评分失败')
  } finally {
    scoring.value = false
  }
}

/* ---------------- 业力录入 ---------------- */
const createDialog = ref(false)
const creating = ref(false)
const form = reactive({
  soul_id: undefined as number | undefined,
  soul_name: '',
  karma_type: '恶' as string,
  category: '',
  score: 10,
  source: '人工录入',
  occurred_at: '',
  description: '',
})

const categoryOptions = computed(() => {
  if (form.karma_type === '善') return GOOD_CATEGORIES
  if (form.karma_type === '恶') return EVIL_CATEGORIES
  return []
})

watch(
  () => form.karma_type,
  () => {
    if (form.karma_type === '中性') form.category = ''
    else if (!categoryOptions.value.includes(form.category)) form.category = categoryOptions.value[0]
  },
)

function openCreate() {
  const soul = selectedSoul.value
  if (!soul) {
    ElMessage.warning('请先在左侧择一亡魂')
    return
  }
  form.soul_id = soul.id
  form.soul_name = soul.name
  form.karma_type = '恶'
  form.category = EVIL_CATEGORIES[0]
  form.score = 10
  form.source = '人工录入'
  form.occurred_at = ''
  form.description = ''
  createDialog.value = true
}

async function submitCreate() {
  if (!form.soul_id) return
  if (form.karma_type !== '中性' && !form.category) {
    ElMessage.warning('请选择业力类别')
    return
  }
  if (!form.score || form.score <= 0) {
    ElMessage.warning('分值需为大于 0 的整数')
    return
  }
  creating.value = true
  try {
    await createKarmaRecord({
      soul_id: form.soul_id,
      karma_type: form.karma_type,
      category: form.category,
      score: Math.abs(Math.round(form.score)),
      source: form.source,
      description: form.description || undefined,
      occurred_at: form.occurred_at || undefined,
    })
    ElMessage.success('业力已入流水，需照镜重算方会体现在总分')
    createDialog.value = false
    await Promise.all([loadProfile(form.soul_id), loadSummary(), loadLedger()])
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '业力录入失败')
  } finally {
    creating.value = false
  }
}

/* ---------------- 业力流水 ---------------- */
const ledgerLoading = ref(false)
const ledgerRows = ref<KarmaRecord[]>([])
const ledgerTotal = ref(0)
const ledgerQuery = reactive({ keyword: '', karma_type: '', page: 1, page_size: 10 })

async function loadLedger() {
  if (tab.value !== 'ledger') return
  ledgerLoading.value = true
  try {
    const res = await fetchKarmaRecords({
      keyword: ledgerQuery.keyword || undefined,
      page: ledgerQuery.page,
      page_size: ledgerQuery.page_size,
    })
    ledgerRows.value = res?.items ?? []
    ledgerTotal.value = res?.meta?.total ?? 0
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '业力流水读取失败')
  } finally {
    ledgerLoading.value = false
  }
}

const ledgerShown = computed(() => {
  const rows = ledgerRows.value
  if (!ledgerQuery.karma_type) return rows
  return rows.filter((r) => r.karma_type === ledgerQuery.karma_type)
})

watch(tab, (val) => {
  if (val === 'ledger' && !ledgerRows.value.length) loadLedger()
})

watch(
  () => [queueStatus.value, queueKeyword.value],
  () => loadQueue(),
)

/* ---------------- 初始化 ---------------- */
async function loadSummary() {
  try {
    summary.value = await fetchKarmaSummary()
  } catch {
    summary.value = null
  }
}

function signedScore(row: KarmaRecord) {
  if (row.karma_type === '善') return Math.abs(row.score)
  if (row.karma_type === '恶') return -Math.abs(row.score)
  return row.score
}

function scoreText(row: KarmaRecord) {
  const val = signedScore(row)
  return val > 0 ? `+${val}` : String(val)
}

function scoreColor(row: KarmaRecord) {
  const val = signedScore(row)
  if (val > 0) return 'color: #4ce0c3'
  if (val < 0) return 'color: #e05b45'
  return 'color: var(--mv-gold)'
}

onMounted(async () => {
  await Promise.all([loadSummary(), loadQueue()])
})
</script>

<template>
  <div class="km-page">
    <div class="mv-panel km-banner">
      <div class="km-banner__main">
        <h2 class="mv-title">孽镜台</h2>
        <p class="mv-subtitle">
          迷魂殿录供毕，押魂上镜。镜中照见前尘善恶，逐条清算业力流水，重定亡魂总分与罪孽等级。
        </p>
      </div>
      <div class="km-banner__stats">
        <div class="km-stat">
          <span class="km-stat__label">业力流水</span>
          <strong class="km-stat__value">{{ summary?.total ?? '—' }}</strong>
        </div>
        <div class="km-stat">
          <span class="km-stat__label">善业</span>
          <strong class="km-stat__value mv-teal">{{ typeCount('善') }}</strong>
        </div>
        <div class="km-stat">
          <span class="km-stat__label">恶业</span>
          <strong class="km-stat__value mv-cinnabar">{{ typeCount('恶') }}</strong>
        </div>
        <div class="km-stat">
          <span class="km-stat__label">中性</span>
          <strong class="km-stat__value mv-gold">{{ typeCount('中性') }}</strong>
        </div>
      </div>
      <div v-if="topCategories.length" class="km-cats">
        <span class="km-cats__title">业类</span>
        <div v-for="c in topCategories" :key="c.category" class="km-cat">
          <span class="km-cat__name">{{ c.category }}</span>
          <span class="km-cat__track"><i :style="{ width: `${Math.max(6, c.percent)}%` }"></i></span>
          <span class="km-cat__val">{{ c.count }}</span>
        </div>
      </div>
    </div>

    <div class="km-tabs">
      <button class="km-tab" :class="{ 'is-active': tab === 'mirror' }" @click="tab = 'mirror'">
        孽镜照业
      </button>
      <button class="km-tab" :class="{ 'is-active': tab === 'ledger' }" @click="tab = 'ledger'">
        业力流水<em class="km-tab__count">{{ summary?.total ?? 0 }}</em>
      </button>
    </div>

    <!-- 孽镜照业 -->
    <div v-show="tab === 'mirror'" class="km-grid">
      <section class="mv-panel km-queue">
        <div class="mv-panel__head">
          <span class="mv-panel__title">待照亡魂</span>
          <span class="mv-muted km-queue__count">{{ queue.length }} 魂</span>
        </div>
        <div class="km-queue__filters">
          <el-input
            v-model="queueKeyword"
            placeholder="姓名 / 亡魂编号"
            clearable
            size="small"
            class="km-queue__search"
          />
          <el-select v-model="queueStatus" size="small" class="km-queue__status" placeholder="全部阶段">
            <el-option label="已过境（待上镜）" value="已过境" />
            <el-option label="待审（可复照）" value="待审" />
            <el-option label="已备案" value="已备案" />
            <el-option label="全部阶段" value="" />
          </el-select>
        </div>
        <div v-loading="queueLoading" class="km-queue__list">
          <button
            v-for="soul in queue"
            :key="soul.id"
            class="km-soul"
            :class="{ 'is-active': soul.id === selectedId }"
            @click="selectSoul(soul)"
          >
            <div class="km-soul__top">
              <span class="km-soul__name">{{ soul.name }}</span>
              <span class="km-soul__score" :style="{ color: karmaStyle(soul.karma_score || 0).color }">
                {{ soul.karma_score ?? 0 }}
              </span>
            </div>
            <div class="km-soul__meta">
              <span class="km-soul__no">{{ soul.soul_no }}</span>
              <span class="km-soul__tag" :style="{
                color: statusStyle(soul.status).color,
                background: statusStyle(soul.status).bg,
                borderColor: statusStyle(soul.status).border,
              }">{{ soul.status }}</span>
            </div>
            <div class="km-soul__sub">
              <span>{{ soul.native_place || '籍贯不详' }}</span>
              <span>{{ soul.sin_level ? `罪孽·${soul.sin_level}` : '未定级' }}</span>
            </div>
          </button>
          <div v-if="!queueLoading && !queue.length" class="km-empty">镜前无魂，此阶段亡魂已尽数照过</div>
        </div>
      </section>

      <section class="mv-panel km-mirror">
        <template v-if="profile">
          <div class="mv-panel__head">
            <span class="mv-panel__title">{{ profile.soul_name }} · 镜中所见</span>
            <div class="km-mirror__actions">
              <el-button
                v-if="canCreate"
                class="mv-ghost-btn"
                size="small"
                @click="openCreate"
              >
                录入业力
              </el-button>
              <el-button
                v-if="canScore"
                class="mv-seal-btn"
                size="small"
                :disabled="!canMirrorScore"
                :loading="scoring"
                @click="doScore"
              >
                开镜照业
              </el-button>
            </div>
          </div>

          <div v-loading="profileLoading" class="km-mirror__body">
            <div class="km-glass">
              <div class="km-glass__aura"></div>
              <div class="km-glass__inner">
                <div class="km-glass__label">镜像业力分</div>
                <div class="km-glass__score" :style="{ color: karmaStyle(profile.computed_score).color }">
                  {{ profile.computed_score }}
                </div>
                <div class="km-glass__level">{{ karmaStyle(profile.computed_score).label }}</div>
              </div>
              <div class="km-glass__side">
                <div class="km-compare">
                  <span>档案分</span>
                  <strong>{{ profile.current_score }}</strong>
                </div>
                <div class="km-compare">
                  <span>罪孽等级</span>
                  <strong>{{ profile.sin_level || '无' }}</strong>
                </div>
                <div class="km-compare">
                  <span>差值</span>
                  <strong :class="diff > 0 ? 'km-up' : diff < 0 ? 'km-down' : ''">
                    {{ diff > 0 ? `+${diff}` : diff }}
                  </strong>
                </div>
                <div class="km-compare">
                  <span>流水条数</span>
                  <strong>{{ profile.items.length }}</strong>
                </div>
              </div>
            </div>

            <div v-if="diff !== 0" class="km-hint">
              镜像分与档案分不一致：该亡魂业力流水在末次评分后有增减，需开镜重算方可用于定罪量刑。
            </div>

            <div class="km-detail__head">
              <span>业力明细</span>
              <span class="mv-muted">共 {{ profile.items.length }} 条</span>
            </div>
            <el-table :data="profile.items" size="small" class="km-table" max-height="360">
              <el-table-column prop="karma_no" label="流水号" width="132" />
              <el-table-column label="善恶" width="72">
                <template #default="{ row }">
                  <span class="km-type" :class="`km-type--${row.karma_type === '善' ? 'good' : row.karma_type === '恶' ? 'evil' : 'neutral'}`">
                    {{ row.karma_type }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="category" label="类别" width="96">
                <template #default="{ row }">{{ row.category || '—' }}</template>
              </el-table-column>
              <el-table-column label="分值" width="76" align="right">
                <template #default="{ row }">
                  <span :style="scoreColor(row)">{{ scoreText(row) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="source" label="来源" width="106">
                <template #default="{ row }">{{ row.source || '—' }}</template>
              </el-table-column>
              <el-table-column label="发生时间" width="146">
                <template #default="{ row }">{{ formatDateTime(row.occurred_at) }}</template>
              </el-table-column>
              <el-table-column prop="recorder_name" label="录入" width="90">
                <template #default="{ row }">{{ row.recorder_name || '—' }}</template>
              </el-table-column>
              <el-table-column prop="description" label="事由" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">{{ row.description || row.describ || '—' }}</template>
              </el-table-column>
            </el-table>
            <div v-if="!profile.items.length" class="km-empty">
              该亡魂尚无业力流水，孽镜无法成像，请先录入业力
            </div>
          </div>
        </template>
        <div v-else class="km-empty km-empty--mirror">
          <div class="km-empty__title">孽镜未照</div>
          <div class="km-empty__sub">于左侧择一亡魂，上镜照见前尘善恶</div>
        </div>
      </section>
    </div>

    <!-- 业力流水 -->
    <section v-show="tab === 'ledger'" class="mv-panel km-ledger">
      <div class="mv-panel__head">
        <span class="mv-panel__title">业力流水</span>
        <div class="km-ledger__filters">
          <el-input
            v-model="ledgerQuery.keyword"
            placeholder="流水号 / 亡魂姓名"
            clearable
            size="small"
            class="km-w220"
            @keyup.enter="ledgerQuery.page = 1; loadLedger()"
            @clear="ledgerQuery.page = 1; loadLedger()"
          />
          <el-select v-model="ledgerQuery.karma_type" size="small" class="km-w130" placeholder="全部善恶">
            <el-option label="全部善恶" value="" />
            <el-option v-for="t in KARMA_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
          <el-button class="mv-ghost-btn" size="small" @click="ledgerQuery.page = 1; loadLedger()">
            查阅
          </el-button>
        </div>
      </div>
      <el-table v-loading="ledgerLoading" :data="ledgerShown" size="small" class="km-table">
        <el-table-column prop="karma_no" label="流水号" width="140" />
        <el-table-column prop="soul_name" label="亡魂" width="110" />
        <el-table-column prop="region" label="鬼域" width="96">
          <template #default="{ row }">{{ row.region || '中央' }}</template>
        </el-table-column>
        <el-table-column label="善恶" width="72">
          <template #default="{ row }">
            <span class="km-type" :class="`km-type--${row.karma_type === '善' ? 'good' : row.karma_type === '恶' ? 'evil' : 'neutral'}`">
              {{ row.karma_type }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类别" width="100">
          <template #default="{ row }">{{ row.category || '—' }}</template>
        </el-table-column>
        <el-table-column label="分值" width="80" align="right">
          <template #default="{ row }">
            <span :style="scoreColor(row)">{{ scoreText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="116">
          <template #default="{ row }">{{ row.source || '—' }}</template>
        </el-table-column>
        <el-table-column label="发生时间" width="150">
          <template #default="{ row }">{{ formatDateTime(row.occurred_at) }}</template>
        </el-table-column>
        <el-table-column prop="recorder_name" label="录入" width="96">
          <template #default="{ row }">{{ row.recorder_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="description" label="事由" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || row.describ || '—' }}</template>
        </el-table-column>
      </el-table>
      <div class="km-pager">
        <el-pagination
          v-model:current-page="ledgerQuery.page"
          :page-size="ledgerQuery.page_size"
          :total="ledgerTotal"
          layout="total, prev, pager, next"
          background
          small
          @current-change="loadLedger"
        />
      </div>
    </section>

    <!-- 评分结果 -->
    <el-dialog v-model="scoreDialog" title="孽镜台照业结果" width="520px">
      <div v-if="scoreResult" class="km-result">
        <div class="km-result__name">{{ scoreResult.soul_name }}</div>
        <div class="km-result__flow">
          <div class="km-result__col">
            <span>照业前</span>
            <strong :style="{ color: karmaStyle(scoreResult.before.score).color }">{{ scoreResult.before.score }}</strong>
            <em>罪孽 · {{ scoreResult.before.sin_level }}</em>
          </div>
          <div class="km-result__arrow">→</div>
          <div class="km-result__col">
            <span>照业后</span>
            <strong :style="{ color: karmaStyle(scoreResult.after.score).color }">{{ scoreResult.after.score }}</strong>
            <em>罪孽 · {{ scoreResult.after.sin_level }}</em>
          </div>
        </div>
        <div class="km-result__note">
          已据 {{ scoreResult.record_count }} 条业力流水重算，评分流水与阴律日志均已留痕。
        </div>
      </div>
      <template #footer>
        <el-button class="mv-seal-btn" size="small" @click="scoreDialog = false">闭镜</el-button>
      </template>
    </el-dialog>

    <!-- 业力录入 -->
    <el-dialog v-model="createDialog" title="录入业力" width="520px">
      <div class="km-form">
        <div class="km-form__row">
          <label>亡魂</label>
          <div class="km-form__soul">{{ form.soul_name }}</div>
        </div>
        <div class="km-form__row">
          <label>善恶</label>
          <el-select v-model="form.karma_type" size="small" class="km-full">
            <el-option v-for="t in KARMA_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
        </div>
        <div class="km-form__row">
          <label>类别</label>
          <el-select
            v-model="form.category"
            size="small"
            class="km-full"
            :disabled="form.karma_type === '中性'"
            placeholder="中性业力无类别"
          >
            <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </div>
        <div class="km-form__row">
          <label>分值</label>
          <el-input-number v-model="form.score" :min="1" :max="200" :step="5" size="small" class="km-full" />
        </div>
        <div class="km-form__row">
          <label>来源</label>
          <el-select v-model="form.source" size="small" class="km-full">
            <el-option v-for="s in SOURCES" :key="s" :label="s" :value="s" />
          </el-select>
        </div>
        <div class="km-form__row">
          <label>发生时间</label>
          <el-date-picker
            v-model="form.occurred_at"
            type="datetime"
            size="small"
            class="km-full"
            placeholder="留空取当前时刻"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </div>
        <div class="km-form__row">
          <label>事由</label>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            size="small"
            maxlength="200"
            show-word-limit
            placeholder="简述善恶行迹，供审判引据"
          />
        </div>
        <div class="km-note">
          录入仅新增流水，不自动重算亡魂总分；分值符号由善恶类型决定（善为正、恶为负）。
        </div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" size="small" @click="createDialog = false">取消</el-button>
        <el-button class="mv-seal-btn" size="small" :loading="creating" @click="submitCreate">入流水</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.km-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.km-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.km-banner__main {
  max-width: 620px;
}
.km-banner__main .mv-subtitle {
  margin-top: 8px;
  line-height: 1.75;
}
.km-banner__stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.km-cats {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed rgba(232, 227, 214, 0.12);
}
.km-cats__title {
  font-size: 11px;
  letter-spacing: 0.16em;
  color: var(--mv-muted);
}
.km-cat {
  display: grid;
  grid-template-columns: 62px 96px 28px;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.km-cat__name {
  color: var(--mv-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.km-cat__track {
  height: 5px;
  background: rgba(232, 227, 214, 0.07);
}
.km-cat__track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, rgba(201, 162, 39, 0.9), rgba(201, 162, 39, 0.25));
}
.km-cat__val {
  text-align: right;
  color: var(--mv-paper);
}
.km-stat {
  min-width: 88px;
  padding: 8px 12px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.km-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.km-stat__value {
  font-family: var(--mv-font-title);
  font-size: 22px;
  line-height: 1.1;
  color: var(--mv-paper);
}
.km-tabs {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid rgba(232, 227, 214, 0.08);
}
.km-tab {
  position: relative;
  padding: 10px 4px 12px;
  margin-right: 18px;
  background: transparent;
  border: none;
  color: var(--mv-muted);
  font-family: var(--mv-font-title);
  font-size: 14px;
  cursor: pointer;
}
.km-tab.is-active {
  color: var(--mv-gold);
}
.km-tab.is-active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  background: var(--mv-cinnabar);
}
.km-tab__count {
  font-style: normal;
  margin-left: 6px;
  font-size: 12px;
  color: var(--mv-gold);
}
.km-grid {
  display: grid;
  grid-template-columns: 336px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.km-queue {
  display: flex;
  flex-direction: column;
  min-height: 560px;
}
.km-queue__count {
  font-size: 12px;
}
.km-queue__filters {
  display: flex;
  gap: 8px;
  padding: 12px 16px 8px;
}
.km-queue__search {
  flex: 1;
}
.km-queue__status {
  width: 132px;
}
.km-queue__list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 12px 14px;
  max-height: 620px;
  overflow-y: auto;
}
.km-soul {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 9px 11px;
  background: rgba(232, 227, 214, 0.03);
  border: 1px solid rgba(232, 227, 214, 0.1);
  border-left: 2px solid transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: all 0.16s;
}
.km-soul:hover {
  border-color: rgba(201, 162, 39, 0.42);
}
.km-soul.is-active {
  border-left-color: var(--mv-cinnabar);
  background: rgba(179, 38, 30, 0.1);
}
.km-soul__top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.km-soul__name {
  font-family: var(--mv-font-title);
  font-size: 15px;
  color: var(--mv-paper);
}
.km-soul__score {
  font-family: var(--mv-font-title);
  font-size: 17px;
}
.km-soul__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--mv-muted);
}
.km-soul__no {
  letter-spacing: 0.04em;
}
.km-soul__tag {
  padding: 1px 7px;
  border: 1px solid transparent;
  border-radius: 2px;
  font-size: 11px;
}
.km-soul__sub {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: var(--mv-muted);
}
.km-mirror {
  min-height: 560px;
}
.km-mirror__actions {
  display: flex;
  gap: 8px;
}
.km-mirror__body {
  padding: 14px 18px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.km-glass {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 18px;
  padding: 20px 22px;
  overflow: hidden;
  border: 1px solid rgba(76, 224, 195, 0.22);
  background:
    radial-gradient(circle at 18% 24%, rgba(76, 224, 195, 0.1), transparent 58%),
    linear-gradient(135deg, rgba(18, 24, 31, 0.94), rgba(11, 11, 16, 0.94));
}
.km-glass__aura {
  position: absolute;
  inset: -40% -10% auto auto;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(76, 224, 195, 0.16), transparent 62%);
  filter: blur(6px);
  pointer-events: none;
}
.km-glass__inner {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.km-glass__label {
  font-size: 12px;
  letter-spacing: 0.16em;
  color: var(--mv-muted);
}
.km-glass__score {
  font-family: var(--mv-font-title);
  font-size: 56px;
  line-height: 1.05;
  letter-spacing: 0.02em;
  text-shadow: 0 0 22px currentColor;
}
.km-glass__level {
  font-family: var(--mv-font-title);
  font-size: 15px;
  color: var(--mv-gold);
  letter-spacing: 0.12em;
}
.km-glass__side {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-left: 18px;
  border-left: 1px solid rgba(232, 227, 214, 0.1);
}
.km-compare {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: var(--mv-muted);
}
.km-compare strong {
  font-family: var(--mv-font-title);
  font-size: 16px;
  color: var(--mv-paper);
  font-weight: 400;
}
.km-up {
  color: #4ce0c3 !important;
}
.km-down {
  color: #e05b45 !important;
}
.km-hint {
  padding: 9px 12px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--mv-gold);
  border: 1px solid rgba(201, 162, 39, 0.35);
  background: rgba(201, 162, 39, 0.06);
}
.km-detail__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 4px;
  font-family: var(--mv-font-title);
  font-size: 14px;
  color: var(--mv-paper);
}
.km-type {
  display: inline-block;
  padding: 1px 7px;
  font-size: 11px;
  border: 1px solid transparent;
  border-radius: 2px;
}
.km-type--good {
  color: #4ce0c3;
  border-color: rgba(76, 224, 195, 0.4);
  background: rgba(76, 224, 195, 0.1);
}
.km-type--evil {
  color: #e05b45;
  border-color: rgba(224, 91, 69, 0.42);
  background: rgba(179, 38, 30, 0.14);
}
.km-type--neutral {
  color: var(--mv-gold);
  border-color: rgba(201, 162, 39, 0.4);
  background: rgba(201, 162, 39, 0.1);
}
.km-ledger__filters {
  display: flex;
  gap: 8px;
  align-items: center;
}
.km-w220 {
  width: 220px;
}
.km-w130 {
  width: 130px;
}
.km-pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
}
.km-empty {
  padding: 28px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
  font-size: 13px;
}
.km-empty--mirror {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 460px;
}
.km-empty__title {
  font-size: 20px;
  color: rgba(232, 227, 214, 0.42);
  letter-spacing: 0.24em;
}
.km-empty__sub {
  font-size: 12px;
  color: var(--mv-muted);
}
.km-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.km-result__name {
  font-family: var(--mv-font-title);
  font-size: 18px;
  color: var(--mv-gold);
}
.km-result__flow {
  display: grid;
  grid-template-columns: 1fr 34px 1fr;
  align-items: center;
  gap: 8px;
  padding: 14px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
}
.km-result__col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.km-result__col span {
  font-size: 12px;
  color: var(--mv-muted);
}
.km-result__col strong {
  font-family: var(--mv-font-title);
  font-size: 30px;
  font-weight: 400;
}
.km-result__col em {
  font-style: normal;
  font-size: 12px;
  color: var(--mv-gold);
}
.km-result__arrow {
  text-align: center;
  color: var(--mv-muted);
}
.km-result__note {
  font-size: 12px;
  line-height: 1.7;
  color: var(--mv-muted);
}
.km-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.km-form__row {
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}
.km-form__row label {
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--mv-muted);
}
.km-form__soul {
  font-family: var(--mv-font-title);
  font-size: 15px;
  color: var(--mv-paper);
}
.km-full {
  width: 100%;
}
.km-note {
  padding: 9px 12px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--mv-muted);
  border: 1px solid rgba(232, 227, 214, 0.1);
  background: rgba(232, 227, 214, 0.03);
}
@media (max-width: 1360px) {
  .km-grid {
    grid-template-columns: 300px minmax(0, 1fr);
  }
  .km-glass {
    grid-template-columns: minmax(0, 1fr);
  }
  .km-glass__side {
    padding-left: 0;
    border-left: none;
    border-top: 1px solid rgba(232, 227, 214, 0.1);
    padding-top: 12px;
  }
}
</style>
