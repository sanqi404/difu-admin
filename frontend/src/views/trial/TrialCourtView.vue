<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createTrial,
  fetchKarmaRecords,
  fetchSoul,
  fetchSoulTimeline,
  fetchTrial,
  handleTrial,
  verdictTrial,
} from '@/api'
import type { KarmaRecord, SoulItem, TrialRecord } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDate, formatDateTime, karmaStyle } from '@/utils/status'

const { hasPerm } = usePerms()
const route = useRoute()
const router = useRouter()

const COURT_NAMES = [
  '一殿秦广王', '二殿楚江王', '三殿宋帝王', '四殿仵官王', '五殿阎罗王',
  '六殿卞城王', '七殿泰山王', '八殿都市王', '九殿平等王', '十殿转轮王',
]
const HELL_NAMES = [
  '拔舌地狱', '剪刀地狱', '铁树地狱', '孽镜地狱', '蒸笼地狱', '铜柱地狱',
  '刀山地狱', '冰山地狱', '油锅地狱', '牛坑地狱', '石压地狱', '舂臼地狱',
  '血池地狱', '枉死地狱', '磔刑地狱', '火山地狱', '石磨地狱', '刀锯地狱',
]
const VERDICTS = ['有罪', '无罪', '打回重审', '还阳', '发配枉死城']

const canHandle = computed(() => hasPerm('trial:handle'))
const canVerdict = computed(() => hasPerm('trial:verdict'))
const canCreate = computed(() => hasPerm('trial:create'))

const trialId = computed(() => Number(route.query.id || 0))
const loading = ref(false)
const trial = ref<TrialRecord | null>(null)
const soul = ref<SoulItem | null>(null)
const karma = ref<KarmaRecord[]>([])
const timeline = ref<Array<{ id?: number; action?: string; detail?: string; operator_name?: string; created_at?: string }>>([])

const verdict = ref('有罪')
const verdictDetail = ref('')
const sentenceYears = ref(1)
const hellLevel = ref(1)
const nextCourtLevel = ref(0)
const submitting = ref(false)
const handling = ref(false)
const resultNote = ref('')
const resultSoulStatus = ref('')

/** 五殿复核项 */
const reviewChecked = ref(false)
const reviewComment = ref('')

const courtName = computed(() => {
  if (!trial.value) return '—'
  return (trial.value as unknown as { court_name?: string }).court_name
    || COURT_NAMES[trial.value.court_level - 1]
    || `第${trial.value.court_level}殿`
})

const isFifthCourt = computed(() => trial.value?.court_level === 5)
const canJudge = computed(() => !!trial.value && ['待审', '审理中'].includes(String(trial.value.status || '')))

const guiltText = computed(() => {
  if (!trial.value) return '卷宗未载'
  return trial.value.guilt_desc || '卷宗未载罪由'
})

const soulKarmaScore = computed(() => soul.value?.karma_score ?? trial.value?.karma_snapshot ?? 0)

const sinLevel = computed(() => soul.value?.sin_level || '—')

const goodKarma = computed(() => karma.value.filter((k) => k.score > 0).slice(0, 6))
const evilKarma = computed(() => karma.value.filter((k) => k.score < 0).slice(0, 6))

function statusStyle(status?: string | null) {
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

function sinText() {
  const s = soul.value?.sin_level || ''
  if (s.includes('极')) return '罪孽极重，宜下重狱'
  if (s.includes('重')) return '罪孽较重，宜入地狱'
  if (s.includes('中')) return '罪孽中等，可减等处置'
  if (s.includes('轻')) return '罪孽尚轻，宜从轻发落'
  return '孽镜无痕，可按功过裁量'
}

async function loadTrial() {
  if (!trialId.value) {
    trial.value = null
    return
  }
  loading.value = true
  try {
    const data = await fetchTrial(trialId.value)
    trial.value = data
    verdictDetail.value = data.verdict_detail || ''
    sentenceYears.value = data.sentence_years || 1
    hellLevel.value = data.hell_level || 1
    nextCourtLevel.value = 0
    if (data.soul_id) await loadSoul(data.soul_id)
  } catch {
    trial.value = null
  } finally {
    loading.value = false
  }
}

async function loadSoul(soulId: number) {
  try {
    soul.value = await fetchSoul(soulId)
  } catch {
    soul.value = null
  }
  try {
    const res = await fetchKarmaRecords({ soul_id: soulId, page: 1, page_size: 20 })
    karma.value = res.items || []
  } catch {
    karma.value = []
  }
  try {
    const res = await fetchSoulTimeline(soulId)
    timeline.value = (res as unknown as { items?: typeof timeline.value }).items || (res as unknown as typeof timeline.value) || []
  } catch {
    timeline.value = []
  }
}

async function startSession() {
  if (!trial.value) return
  handling.value = true
  try {
    await handleTrial(trial.value.id)
    ElMessage.success('惊堂木落，开堂审理')
    await loadTrial()
  } catch {
    await loadTrial()
  } finally {
    handling.value = false
  }
}

async function submitVerdict(preset?: string) {
  if (!trial.value) return
  const type = preset || verdict.value
  if (type === '有罪' || type === '发配枉死城') {
    if (sentenceYears.value <= 0) {
      ElMessage.warning('量刑年限须大于 0')
      return
    }
    if (hellLevel.value <= 0) {
      ElMessage.warning('请择定刑狱殿级')
      return
    }
  }
  if (isFifthCourt.value && ['有罪', '发配枉死城'].includes(type) && !reviewChecked.value) {
    ElMessage.warning('五殿判重罪须勾选复核项')
    return
  }
  try {
    await ElMessageBox.confirm(
      `宣读判词：「${type}」？${
        type === '有罪' && nextCourtLevel.value > trial.value.court_level
          ? `（案情重大，将移交${COURT_NAMES[nextCourtLevel.value - 1]}复核）`
          : ''
      }判决后不可更改。`,
      '落 判',
      { confirmButtonText: '落 判', cancelButtonText: '再斟酌' },
    )
  } catch {
    return
  }
  submitting.value = true
  try {
    const res = await verdictTrial(trial.value.id, {
      verdict: type,
      verdict_detail: verdictDetail.value.trim() || undefined,
      sentence_years: ['有罪', '发配枉死城'].includes(type) ? sentenceYears.value : 0,
      hell_level: type === '发配枉死城' ? 18 : ['有罪'].includes(type) ? hellLevel.value : 0,
      next_court_level: type === '有罪' ? nextCourtLevel.value : 0,
    })
    const data = res as unknown as { soul_status?: string; next_trial?: { trial_no?: string; court_level?: number } }
    resultSoulStatus.value = data.soul_status || ''
    resultNote.value = type === '有罪' && data.next_trial
      ? `已移交${COURT_NAMES[(data.next_trial.court_level || 1) - 1]}复核，新案卷 ${data.next_trial.trial_no || ''}`
      : type === '打回重审' && data.next_trial
        ? `已打回${COURT_NAMES[(data.next_trial.court_level || 1) - 1]}重审，新案卷 ${data.next_trial.trial_no || ''}`
        : '判词已落，案卷归档'
    ElMessage.success('判词已落，惊堂木再响')
    await loadTrial()
  } catch {
    await loadTrial()
  } finally {
    submitting.value = false
  }
}

async function reopen() {
  if (!trial.value) return
  const level = trial.value.next_court_level || trial.value.court_level
  try {
    await ElMessageBox.confirm(`就此案重新提审至「${COURT_NAMES[level - 1] || '一殿秦广王'}」？`, '重 新 提 审', {
      confirmButtonText: '提 审',
      cancelButtonText: '再看看',
    })
  } catch {
    return
  }
  try {
    const created = await createTrial({
      soul_id: trial.value.soul_id,
      court_level: level,
      guilt_desc: trial.value.guilt_desc || undefined,
    })
    const newId = (created as unknown as { id?: number }).id
    ElMessage.success('已重新立卷')
    if (newId) router.push({ path: '/trial/court', query: { id: String(newId) } })
    else await loadTrial()
  } catch {
    await loadTrial()
  }
}

function backToList() {
  router.push('/trial/list')
}

watch(
  () => route.query.id,
  () => {
    resultNote.value = ''
    resultSoulStatus.value = ''
    reviewChecked.value = false
    reviewComment.value = ''
    loadTrial()
  },
)

onMounted(() => {
  loadTrial()
})
</script>

<template>
  <div v-loading="loading" class="mv-page tc-page">
    <div class="mv-panel tc-head">
      <div class="tc-head__left">
        <el-button class="mv-ghost-btn" @click="backToList">返 回 卷 宗</el-button>
        <div class="tc-head__title">
          <span class="mv-title">{{ courtName }} · 审判台</span>
          <span v-if="trial" class="mv-mono mv-sub">{{ trial.trial_no }}</span>
        </div>
      </div>
      <div class="tc-head__right">
        <template v-if="trial">
          <span
            class="tc-badge"
            :style="{
              color: statusStyle(trial.status).color,
              background: statusStyle(trial.status).bg,
              borderColor: statusStyle(trial.status).border,
            }"
          >
            {{ trial.status }}
          </span>
          <span v-if="isFifthCourt" class="tc-fifth">五殿复核</span>
          <el-button v-if="canHandle && trial.status === '待审'" class="mv-seal-btn mv-seal-btn--sm" :loading="handling" @click="startSession">
            开 堂
          </el-button>
        </template>
      </div>
    </div>

    <div v-if="!trial" class="mv-panel tc-empty">
      <div class="tc-empty__text">未择案卷</div>
      <div class="mv-muted">请从卷宗列表点「审判台」入座</div>
      <el-button class="mv-seal-btn mv-seal-btn--sm" @click="backToList">前 往 卷 宗 库</el-button>
    </div>

    <div v-else class="tc-body">
      <!-- 左：卷宗 + 口供 + 孽镜台 -->
      <div class="tc-left">
        <div class="mv-panel tc-card">
          <div class="tc-card__head">
            <span class="mv-subtitle">卷 宗</span>
            <span class="mv-mono mv-sub">{{ trial.soul_name }}</span>
          </div>
          <div class="tc-soul">
            <div class="tc-soul__name">{{ trial.soul_name }}</div>
            <div class="tc-soul__meta">
              <span class="mv-mono">{{ soul?.soul_no || '—' }}</span>
              <span>{{ soul?.gender || '—' }} · {{ soul?.age ?? '—' }} 岁</span>
              <span>{{ soul?.native_place || '籍贯未载' }}</span>
            </div>
          </div>
          <el-descriptions :column="2" border size="small" class="tc-desc">
            <el-descriptions-item label="生卒">
              {{ formatDate(soul?.birth_date) }} 至 {{ formatDate(soul?.death_date) }}
            </el-descriptions-item>
            <el-descriptions-item label="死因">{{ soul?.death_type || trial.status || '—' }}</el-descriptions-item>
            <el-descriptions-item label="归属">{{ soul?.region || trial.region || '—' }}</el-descriptions-item>
            <el-descriptions-item label="亡魂状态">{{ soul?.status || '—' }}</el-descriptions-item>
            <el-descriptions-item label="生死簿号">{{ soul?.life_book_no || '—' }}</el-descriptions-item>
            <el-descriptions-item label="主审">{{ trial.judge_name || '未定' }}</el-descriptions-item>
            <el-descriptions-item label="立案时间">{{ formatDateTime(trial.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="开堂时间">{{ formatDateTime(trial.started_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="mv-panel tc-card">
          <div class="tc-card__head">
            <span class="mv-subtitle">口 供 · 罪 由</span>
          </div>
          <div class="tc-supply">
            <p>{{ guiltText }}</p>
            <p v-if="soul?.remark" class="tc-supply__remark">附注：{{ soul.remark }}</p>
            <p v-if="trial.verdict" class="tc-supply__verdict">
              已判：<strong>{{ trial.verdict }}</strong>
              <span v-if="trial.verdict_detail"> · {{ trial.verdict_detail }}</span>
            </p>
          </div>
        </div>

        <div class="mv-panel tc-card">
          <div class="tc-card__head">
            <span class="mv-subtitle">孽 镜 台</span>
            <span class="mv-muted">生前功过一览</span>
          </div>
          <div class="tc-mirror">
            <div class="tc-mirror__score">
              <span class="tc-mirror__value" :style="{ color: karmaStyle(soulKarmaScore).color }">{{ soulKarmaScore }}</span>
              <span class="tc-mirror__label">{{ karmaStyle(soulKarmaScore).label }}</span>
            </div>
            <div class="tc-mirror__meta">
              <span>罪孽层级：<em>{{ sinLevel }}</em></span>
              <span class="tc-mirror__hint">{{ sinText() }}</span>
            </div>
          </div>
          <div class="tc-karma">
            <div class="tc-karma__col">
              <div class="tc-karma__title">善 行</div>
              <div v-for="k in goodKarma" :key="k.id" class="tc-karma__item">
                <span class="tc-karma__cat">{{ k.category }}</span>
                <span class="tc-karma__score" :style="{ color: karmaStyle(k.score).color }">+{{ k.score }}</span>
              </div>
              <div v-if="!goodKarma.length" class="mv-sub">无载</div>
            </div>
            <div class="tc-karma__col">
              <div class="tc-karma__title">恶 行</div>
              <div v-for="k in evilKarma" :key="k.id" class="tc-karma__item">
                <span class="tc-karma__cat">{{ k.category }}</span>
                <span class="tc-karma__score" :style="{ color: karmaStyle(k.score).color }">{{ k.score }}</span>
              </div>
              <div v-if="!evilKarma.length" class="mv-sub">无载</div>
            </div>
          </div>
        </div>

        <div class="mv-panel tc-card">
          <div class="tc-card__head">
            <span class="mv-subtitle">会 审 记 录</span>
          </div>
          <div class="tc-log">
            <div v-for="(item, idx) in timeline.slice(0, 12)" :key="item.id || idx" class="tc-log__row">
              <span class="tc-log__dot" />
              <span class="tc-log__action">{{ item.action || '流转' }}</span>
              <span class="tc-log__detail">{{ item.detail || '—' }}</span>
              <span class="tc-log__time mv-mono">{{ formatDateTime(item.created_at) }}</span>
            </div>
            <div v-if="!timeline.length" class="mv-sub">尚无会审记录</div>
          </div>
        </div>
      </div>

      <!-- 右：判词 / 量刑 -->
      <div class="tc-right">
        <div class="mv-panel tc-card tc-verdict">
          <div class="tc-card__head">
            <span class="mv-subtitle">判 词 起 草</span>
            <span class="mv-muted">{{ courtName }}</span>
          </div>

          <div class="tc-field">
            <label>判决</label>
            <el-select v-model="verdict" class="tc-full" :disabled="!canJudge || !canVerdict">
              <el-option v-for="v in VERDICTS" :key="v" :label="v" :value="v" />
            </el-select>
          </div>

          <div class="tc-field">
            <label>判词</label>
            <el-input
              v-model="verdictDetail"
              type="textarea"
              :rows="5"
              maxlength="500"
              show-word-limit
              :disabled="!canJudge || !canVerdict"
              placeholder="例：生前忤逆不孝、欺压良善，罪证确凿，依阴律判入拔舌地狱，刑期三年"
            />
          </div>

          <div class="tc-field-row">
            <div class="tc-field">
              <label>量刑（年）</label>
              <el-input-number v-model="sentenceYears" :min="0" :max="9999" :disabled="!canJudge || !canVerdict" controls-position="right" />
            </div>
            <div class="tc-field">
              <label>刑狱殿级</label>
              <el-select v-model="hellLevel" :disabled="!canJudge || !canVerdict" class="tc-full">
                <el-option v-for="(name, idx) in HELL_NAMES" :key="name" :label="`${idx + 1} · ${name}`" :value="idx + 1" />
              </el-select>
            </div>
          </div>

          <div class="tc-field">
            <label>升殿复核（仅「有罪」可选，0 表示本殿结案）</label>
            <el-select v-model="nextCourtLevel" :disabled="!canJudge || !canVerdict" class="tc-full">
              <el-option label="本殿结案" :value="0" />
              <el-option
                v-for="level in 10"
                :key="level"
                :label="`移交 ${COURT_NAMES[level - 1]}`"
                :value="level"
                :disabled="level <= (trial.court_level || 0)"
              />
            </el-select>
          </div>

          <div class="tc-advice">
            <div class="tc-advice__title">量 刑 建 议</div>
            <div class="tc-advice__body">
              孽镜评分 <em :style="{ color: karmaStyle(soulKarmaScore).color }">{{ soulKarmaScore }}</em>，
              {{ sinText() }}。建议依《阴律》判处 <em>{{ sentenceYears }}</em> 年，
              刑狱 {{ HELL_NAMES[hellLevel - 1] || '未定' }}。
            </div>
          </div>

          <!-- 五殿额外复核项 -->
          <div v-if="isFifthCourt" class="tc-review">
            <div class="tc-review__title">五 殿 复 核 项</div>
            <el-input
              v-model="reviewComment"
              type="textarea"
              :rows="2"
              maxlength="200"
              placeholder="复核意见（随判词归档）"
              :disabled="!canJudge || !canVerdict"
            />
            <el-checkbox v-model="reviewChecked" :disabled="!canJudge || !canVerdict">
              五殿重案复核已核，准予落判
            </el-checkbox>
          </div>

          <div class="tc-actions">
            <el-button
              v-if="canVerdict"
              class="mv-seal-btn mv-seal-btn--sm"
              :loading="submitting"
              :disabled="!canJudge"
              @click="submitVerdict()"
            >
              落 判：{{ verdict }}
            </el-button>
            <el-button v-if="canVerdict" class="mv-ghost-btn" :disabled="!canJudge" :loading="submitting" @click="submitVerdict('打回重审')">
              打 回 重 审
            </el-button>
            <el-button v-if="canVerdict" class="mv-ghost-btn" :disabled="!canJudge" :loading="submitting" @click="submitVerdict('还阳')">
              认定冤案 · 还阳
            </el-button>
            <el-button v-if="canVerdict" class="mv-ghost-btn" :disabled="!canJudge" :loading="submitting" @click="submitVerdict('发配枉死城')">
              发 配 枉 死 城
            </el-button>
            <el-button v-if="canCreate && trial.verdict === '打回重审'" class="mv-ghost-btn" @click="reopen">重 新 提 审</el-button>
          </div>
          <div v-if="!canVerdict" class="tc-note">当前名籍无「trial:verdict」判词之权，仅可查阅卷宗。</div>

          <div v-if="resultNote" class="tc-result">
            <div class="tc-result__title">落 判 回 执</div>
            <div>{{ resultNote }}</div>
            <div v-if="resultSoulStatus" class="tc-result__status">亡魂状态流转为：<strong>{{ resultSoulStatus }}</strong></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tc-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.tc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  gap: 12px;
}
.tc-head__left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.tc-head__title {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.tc-head__right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tc-badge {
  padding: 2px 10px;
  font-size: 12px;
  border: 1px solid;
  border-radius: 2px;
}
.tc-fifth {
  padding: 2px 8px;
  font-size: 11px;
  color: var(--mv-gold);
  border: 1px solid rgba(201, 162, 39, 0.6);
  border-radius: 2px;
}
.tc-body {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.tc-left,
.tc-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.tc-card {
  padding: 14px 16px;
}
.tc-card__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}
.tc-soul {
  margin-bottom: 12px;
}
.tc-soul__name {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 22px;
  color: var(--mv-paper);
  letter-spacing: 0.14em;
}
.tc-soul__meta {
  display: flex;
  gap: 14px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--mv-muted);
}
.tc-desc :deep(.el-descriptions__label) {
  width: 88px;
}
.tc-supply p {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--mv-paper);
}
.tc-supply__remark {
  color: var(--mv-muted) !important;
}
.tc-supply__verdict {
  padding-top: 6px;
  border-top: 1px dashed rgba(232, 227, 214, 0.12);
  color: var(--mv-gold) !important;
}
.tc-mirror {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 10px 12px;
  background: radial-gradient(circle at 12% 50%, rgba(76, 224, 195, 0.1), transparent 60%);
  border: 1px solid rgba(76, 224, 195, 0.18);
  border-radius: 2px;
}
.tc-mirror__score {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.tc-mirror__value {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 30px;
  line-height: 1.1;
}
.tc-mirror__label {
  font-size: 11px;
  color: var(--mv-muted);
}
.tc-mirror__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--mv-paper);
}
.tc-mirror__meta em {
  font-style: normal;
  color: var(--mv-gold);
}
.tc-mirror__hint {
  color: var(--mv-muted);
}
.tc-karma {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 12px;
}
.tc-karma__title {
  margin-bottom: 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  color: var(--mv-muted);
}
.tc-karma__item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 12px;
  border-bottom: 1px dashed rgba(232, 227, 214, 0.08);
}
.tc-karma__cat {
  color: var(--mv-paper);
}
.tc-log {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 220px;
  overflow: auto;
}
.tc-log__row {
  display: grid;
  grid-template-columns: 8px 80px 1fr auto;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--mv-paper);
}
.tc-log__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--mv-gold);
  opacity: 0.7;
}
.tc-log__action {
  color: var(--mv-gold);
}
.tc-log__detail {
  color: var(--mv-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tc-log__time {
  color: var(--mv-muted);
}
.tc-verdict {
  position: sticky;
  top: 12px;
}
.tc-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}
.tc-field label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.1em;
}
.tc-field-row {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 14px;
}
.tc-full {
  width: 100%;
}
.tc-advice {
  margin-bottom: 14px;
  padding: 10px 12px;
  background: rgba(201, 162, 39, 0.06);
  border-left: 2px solid rgba(201, 162, 39, 0.6);
}
.tc-advice__title {
  margin-bottom: 4px;
  font-size: 12px;
  letter-spacing: 0.16em;
  color: var(--mv-gold);
}
.tc-advice__body {
  font-size: 12px;
  line-height: 1.8;
  color: var(--mv-paper);
}
.tc-advice__body em {
  font-style: normal;
  color: var(--mv-gold);
}
.tc-review {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
  padding: 10px 12px;
  border: 1px dashed rgba(201, 162, 39, 0.5);
  background: rgba(201, 162, 39, 0.05);
}
.tc-review__title {
  font-size: 12px;
  letter-spacing: 0.16em;
  color: var(--mv-gold);
}
.tc-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px dashed rgba(232, 227, 214, 0.12);
}
.tc-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--mv-muted);
}
.tc-result {
  margin-top: 14px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.8;
  color: var(--mv-paper);
  border: 1px solid rgba(76, 224, 195, 0.3);
  background: rgba(76, 224, 195, 0.06);
}
.tc-result__title {
  margin-bottom: 4px;
  letter-spacing: 0.16em;
  color: var(--mv-phosphor);
}
.tc-result__status strong {
  color: var(--mv-phosphor);
}
.tc-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 60px 0;
}
.tc-empty__text {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 20px;
  letter-spacing: 0.2em;
  color: var(--mv-paper);
}
@media (max-width: 1500px) {
  .tc-body {
    grid-template-columns: minmax(0, 1fr);
  }
  .tc-verdict {
    position: static;
  }
}
</style>
