<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createLifeBook,
  fetchLifeBook,
  fetchLifeBooks,
  fetchLifeBookSummary,
  rejectLifeBook,
  reviewLifeBook,
} from '@/api'
import type { LifeBookRecord, LifeBookSummary, SoulItem } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime } from '@/utils/status'
import SoulPicker from '@/components/SoulPicker.vue'

const { hasPerm } = usePerms()
const route = useRoute()

const REGIONS = ['中央', '东方', '南方', '西方', '北方']
const ACTIONS = ['录入', '修改', '复核', '驳回', '注销']

const canCreate = computed(() => hasPerm('lifebook:create'))
const canReview = computed(() => hasPerm('lifebook:review'))
const canReject = computed(() => hasPerm('lifebook:reject'))

type TabKey = 'ledger' | 'review' | 'diff'

const tab = ref<TabKey>('ledger')
const loading = ref(false)
const rows = ref<LifeBookRecord[]>([])
const total = ref(0)
const summary = ref<LifeBookSummary | null>(null)
const query = reactive({
  keyword: '',
  action: '',
  region: '',
  tampered: false,
  page: 1,
  page_size: 10,
})

const tabs = computed(() =>
  [
    { key: 'ledger' as TabKey, label: '生死簿流水', count: summary.value?.total ?? 0 },
    { key: 'review' as TabKey, label: '待我复核', count: summary.value?.pending ?? 0, hidden: !canReview.value },
    { key: 'diff' as TabKey, label: '变更流水', count: summary.value?.tampered ?? 0 },
  ].filter((t) => !t.hidden),
)

const effectiveReviewStatus = computed(() => (tab.value === 'review' ? '待复核' : ''))

function reviewStyle(status: string) {
  if (status === '已复核') return { color: '#4ce0c3', bg: 'rgba(76,224,195,0.12)', border: 'rgba(76,224,195,0.4)' }
  if (status === '已驳回') return { color: '#d4553f', bg: 'rgba(179,38,30,0.18)', border: 'rgba(212,85,63,0.5)' }
  return { color: '#e0b86a', bg: 'rgba(224,184,106,0.12)', border: 'rgba(224,184,106,0.42)' }
}

function actionStyle(action: string) {
  if (action === '注销') return { color: '#d4553f', border: 'rgba(212,85,63,0.5)' }
  if (action === '修改') return { color: '#c9a227', border: 'rgba(201,162,39,0.5)' }
  return { color: '#a9a294', border: 'rgba(169,162,148,0.35)' }
}

async function loadSummary() {
  try {
    summary.value = await fetchLifeBookSummary()
  } catch {
    summary.value = null
  }
}

async function loadList() {
  loading.value = true
  try {
    const data = await fetchLifeBooks({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      action: query.action || undefined,
      region: query.region || undefined,
      review_status: effectiveReviewStatus.value || undefined,
      is_tampered: query.tampered ? 1 : undefined,
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
  query.page = 1
  loadList()
}

function search() {
  query.page = 1
  loadList()
}

function resetQuery() {
  query.keyword = ''
  query.action = ''
  query.region = ''
  query.tampered = false
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

/* ---------------- 详情 ---------------- */
const drawerOpen = ref(false)
const detailLoading = ref(false)
const detail = ref<LifeBookRecord | null>(null)

async function openDetail(row: LifeBookRecord) {
  drawerOpen.value = true
  detailLoading.value = true
  detail.value = row
  try {
    detail.value = await fetchLifeBook(row.id)
  } catch {
    /* 拦截器已提示 */
  } finally {
    detailLoading.value = false
  }
}

/* ---------------- 复核 ---------------- */
const acting = ref<number | null>(null)

async function passReview(row: LifeBookRecord) {
  let comment = ''
  try {
    const res = await ElMessageBox.prompt('复核意见（可留空，默认「复核无误」）', `复核通过 · ${row.book_no}`, {
      confirmButtonText: '准 予 复 核',
      cancelButtonText: '取消',
      inputPlaceholder: '复核无误',
      inputValue: '',
      inputType: 'textarea',
    })
    comment = (res as { value: string }).value || ''
  } catch {
    return
  }
  acting.value = row.id
  try {
    await reviewLifeBook(row.id, comment || '复核无误')
    ElMessage.success('复核已落印，生死簿生效')
    await refresh()
    if (detail.value?.id === row.id) detail.value = await fetchLifeBook(row.id)
  } catch {
    await refresh()
  } finally {
    acting.value = null
  }
}

async function rejectReview(row: LifeBookRecord) {
  let comment = ''
  try {
    const res = await ElMessageBox.prompt('驳回缘由（必填，不少于 2 字）', `驳回 · ${row.book_no}`, {
      confirmButtonText: '驳 回',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputValidator: (v: string) => (v && v.trim().length >= 2 ? true : '驳回缘由不得少于 2 个字'),
    })
    comment = (res as { value: string }).value.trim()
  } catch {
    return
  }
  acting.value = row.id
  try {
    await rejectLifeBook(row.id, comment)
    ElMessage.warning('已驳回，原簿恢复')
    await refresh()
    if (detail.value?.id === row.id) detail.value = await fetchLifeBook(row.id)
  } catch {
    await refresh()
  } finally {
    acting.value = null
  }
}

/* ---------------- 添寿 / 勾销 ---------------- */
const editDialog = reactive({
  open: false,
  mode: 'extend' as 'extend' | 'erase',
})

const editForm = reactive({
  soul_id: null as number | null,
  soul: null as SoulItem | null,
  base: 60,
  amount: 5,
  reason: '',
})
const baseLoading = ref(false)
const submitting = ref(false)

const resultLifespan = computed(() => {
  const next = editDialog.mode === 'extend' ? editForm.base + editForm.amount : editForm.base - editForm.amount
  return Math.max(0, Math.min(999, next))
})

function openEdit(mode: 'extend' | 'erase') {
  editDialog.mode = mode
  editDialog.open = true
  editForm.soul_id = null
  editForm.soul = null
  editForm.base = 60
  editForm.amount = mode === 'extend' ? 5 : 5
  editForm.reason = ''
}

async function onSoulChange(soul: SoulItem | null) {
  editForm.soul = soul
  editForm.base = soul?.age ?? 60
  if (!soul) return
  baseLoading.value = true
  try {
    const data = await fetchLifeBooks({ keyword: soul.name, page_size: 20 })
    const hit = (data.items || []).find((item) => item.soul_id === soul.id)
    if (hit) editForm.base = hit.lifespan_years
  } catch {
    /* 沿用亡魂年岁作为基准 */
  } finally {
    baseLoading.value = false
  }
}

async function submitEdit() {
  const modeText = editDialog.mode === 'extend' ? '添寿' : '勾销阳寿'
  if (!editForm.soul_id || !editForm.soul) {
    ElMessage.warning('请先检索并选定亡魂')
    return
  }
  if (editForm.amount <= 0) {
    ElMessage.warning('数额需大于 0')
    return
  }
  if (editDialog.mode === 'erase' && editForm.amount > editForm.base) {
    ElMessage.warning(`勾销数额不得超过原定阳寿 ${editForm.base} 年`)
    return
  }
  if (editForm.reason.trim().length < 2) {
    ElMessage.warning('请填写缘由（不少于 2 字）')
    return
  }
  submitting.value = true
  try {
    await createLifeBook({
      soul_id: editForm.soul_id,
      soul_name: editForm.soul.name,
      action: editDialog.mode === 'extend' ? '修改' : '注销',
      lifespan_years: resultLifespan.value,
      before_content: `原定阳寿 ${editForm.base} 年`,
      after_content: `新定阳寿 ${resultLifespan.value} 年`,
      diff_desc: `${modeText} ${editForm.amount} 年 · 缘由：${editForm.reason.trim()}`,
    })
    ElMessage.success('已录入，等待复核')
    editDialog.open = false
    await refresh()
  } catch {
    await refresh()
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  const wanted = String(route.query.tab || '')
  if ((wanted === 'review' && canReview.value) || wanted === 'diff') {
    tab.value = wanted as TabKey
  } else if (/\/review\/?$/.test(route.path) && canReview.value) {
    tab.value = 'review'
  }
  refresh()
})
</script>

<template>
  <div class="mv-page">
    <!-- 概览 -->
    <div class="mv-panel lb-overview">
      <div class="lb-stats">
        <div class="lb-stat">
          <span class="lb-stat__label">在册流水</span>
          <span class="lb-stat__value">{{ summary?.total ?? 0 }}</span>
        </div>
        <div class="lb-stat">
          <span class="lb-stat__label">待复核</span>
          <span class="lb-stat__value lb-stat__value--gold">{{ summary?.pending ?? 0 }}</span>
        </div>
        <div class="lb-stat">
          <span class="lb-stat__label">已涂改</span>
          <span class="lb-stat__value lb-stat__value--red">{{ summary?.tampered ?? 0 }}</span>
        </div>
        <div class="lb-stat" v-for="item in summary?.by_review_status || []" :key="item.status">
          <span class="lb-stat__label">{{ item.status }}</span>
          <span class="lb-stat__value" :style="{ color: reviewStyle(item.status).color }">{{ item.count }}</span>
        </div>
      </div>
      <div class="lb-actions">
        <el-button v-if="canCreate" class="mv-seal-btn mv-seal-btn--sm" @click="openEdit('extend')">
          添 寿
        </el-button>
        <el-button v-if="canCreate" class="mv-ghost-btn" @click="openEdit('erase')">勾 销 阳 寿</el-button>
        <el-button class="mv-ghost-btn" @click="refresh">刷 新 簿 册</el-button>
      </div>
    </div>

    <!-- 页签 + 列表 -->
    <div class="mv-panel mv-panel--table">
      <div class="lb-tabs">
        <button
          v-for="item in tabs"
          :key="item.key"
          class="lb-tab"
          :class="{ 'is-active': tab === item.key }"
          type="button"
          @click="switchTab(item.key)"
        >
          {{ item.label }}
          <em class="lb-tab__count">{{ item.count }}</em>
        </button>
      </div>

      <div class="mv-toolbar lb-filters">
        <div class="mv-toolbar__left">
          <el-input
            v-model="query.keyword"
            class="lb-w220"
            placeholder="亡魂姓名 / 生死簿编号"
            clearable
            @keyup.enter="search"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="query.action" class="lb-w140" placeholder="操作类型" clearable>
            <el-option v-for="a in ACTIONS" :key="a" :label="a" :value="a" />
          </el-select>
          <el-select v-model="query.region" class="lb-w130" placeholder="归属鬼域" clearable>
            <el-option v-for="r in REGIONS" :key="r" :label="`${r}鬼域`" :value="r" />
          </el-select>
          <el-checkbox v-model="query.tampered" class="lb-check">仅看涂改</el-checkbox>
          <el-button class="mv-seal-btn mv-seal-btn--sm" @click="search">查 阅</el-button>
          <el-button class="mv-ghost-btn" @click="resetQuery">重置</el-button>
        </div>
        <div class="mv-toolbar__right">
          <span class="mv-muted">共 <em class="mv-count">{{ total }}</em> 条记录</span>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        row-key="id"
        class="mv-table"
        height="calc(100vh - 372px)"
        @row-click="openDetail"
      >
        <el-table-column label="簿号" width="150">
          <template #default="{ row }">
            <span class="mv-mono">{{ row.book_no }}</span>
            <span v-if="row.is_tampered" class="lb-flag">涂改</span>
          </template>
        </el-table-column>
        <el-table-column prop="soul_name" label="亡魂" width="110" />
        <el-table-column label="操作" width="92">
          <template #default="{ row }">
            <span class="lb-action" :style="{ color: actionStyle(row.action).color, borderColor: actionStyle(row.action).border }">
              {{ row.action }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="阳寿" width="96" align="right">
          <template #default="{ row }">
            <span class="lb-lifespan">{{ row.lifespan_years }}</span>
            <span class="mv-sub">年</span>
          </template>
        </el-table-column>

        <template v-if="tab === 'diff'">
          <el-table-column prop="before_content" label="变更前" min-width="150" show-overflow-tooltip />
          <el-table-column prop="after_content" label="变更后" min-width="150" show-overflow-tooltip />
        </template>

        <el-table-column prop="diff_desc" label="变更说明" min-width="200" show-overflow-tooltip />
        <el-table-column label="复核状态" width="112">
          <template #default="{ row }">
            <span
              class="lb-badge"
              :style="{
                color: reviewStyle(row.review_status).color,
                background: reviewStyle(row.review_status).bg,
                borderColor: reviewStyle(row.review_status).border,
              }"
            >
              {{ row.review_status }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="录入人" width="106" />
        <el-table-column label="复核人" width="116">
          <template #default="{ row }">
            <span>{{ row.reviewer_name || '—' }}</span>
            <div class="mv-sub">{{ row.reviewed_at ? formatDateTime(row.reviewed_at) : '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="录入时间" width="144">
          <template #default="{ row }">
            <span class="mv-mono">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" :width="tab === 'review' ? 150 : 80" fixed="right">
          <template #default="{ row }">
            <div class="lb-row-actions" @click.stop>
              <el-button link class="lb-link" @click="openDetail(row)">详情</el-button>
              <template v-if="row.review_status === '待复核' && tab === 'review'">
                <el-button v-if="canReview" link class="lb-link lb-link--ok" :loading="acting === row.id" @click="passReview(row)">
                  通过
                </el-button>
                <el-button v-if="canReject" link class="lb-link lb-link--bad" :loading="acting === row.id" @click="rejectReview(row)">
                  驳回
                </el-button>
              </template>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="lb-empty">簿册空空，或条件过严</div>
        </template>
      </el-table>

      <div class="lb-pager">
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

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerOpen" title="生死簿 · 卷宗" size="560px" destroy-on-close>
      <div v-loading="detailLoading" class="mv-drawer">
        <template v-if="detail">
          <div class="lb-drawer-head">
            <div>
              <div class="lb-drawer-title">{{ detail.soul_name }}</div>
              <div class="mv-mono lb-drawer-sub">{{ detail.book_no }}</div>
            </div>
            <span
              class="lb-badge"
              :style="{
                color: reviewStyle(detail.review_status).color,
                background: reviewStyle(detail.review_status).bg,
                borderColor: reviewStyle(detail.review_status).border,
              }"
            >
              {{ detail.review_status }}
            </span>
          </div>

          <el-descriptions :column="2" border size="small" class="lb-desc">
            <el-descriptions-item label="操作类型">{{ detail.action }}</el-descriptions-item>
            <el-descriptions-item label="定寿">{{ detail.lifespan_years }} 年</el-descriptions-item>
            <el-descriptions-item label="录入人">{{ detail.operator_name }}</el-descriptions-item>
            <el-descriptions-item label="复核人">{{ detail.reviewer_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="录入时间">{{ formatDateTime(detail.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="复核时间">{{ formatDateTime(detail.reviewed_at) }}</el-descriptions-item>
            <el-descriptions-item label="变更说明" :span="2">{{ detail.diff_desc || '—' }}</el-descriptions-item>
            <el-descriptions-item label="复核意见" :span="2">{{ detail.review_comment || '—' }}</el-descriptions-item>
          </el-descriptions>

          <div class="lb-diff">
            <div class="lb-diff__col">
              <span class="lb-diff__label">变更前</span>
              <p>{{ detail.before_content || '（无）' }}</p>
            </div>
            <div class="lb-diff__arrow">→</div>
            <div class="lb-diff__col">
              <span class="lb-diff__label">变更后</span>
              <p>{{ detail.after_content || '（无）' }}</p>
            </div>
          </div>

          <div v-if="detail.review_status === '待复核'" class="lb-drawer-actions">
            <el-button v-if="canReview" class="mv-seal-btn mv-seal-btn--sm" @click="passReview(detail)">准 予 复 核</el-button>
            <el-button v-if="canReject" class="mv-ghost-btn" @click="rejectReview(detail)">驳 回</el-button>
          </div>
        </template>
      </div>
    </el-drawer>

    <!-- 添寿 / 勾销 -->
    <el-dialog
      v-model="editDialog.open"
      :title="editDialog.mode === 'extend' ? '生死簿 · 添寿' : '生死簿 · 勾销阳寿'"
      width="520px"
      destroy-on-close
    >
      <div class="lb-form">
        <div class="lb-field">
          <label>亡魂</label>
          <SoulPicker v-model="editForm.soul_id" @change="onSoulChange" />
        </div>
        <div class="lb-field lb-field--row">
          <div>
            <label>原定阳寿</label>
            <div class="lb-static">
              <span v-loading="baseLoading">{{ editForm.base }}</span> 年
            </div>
          </div>
          <div>
            <label>{{ editDialog.mode === 'extend' ? '增寿数额' : '勾销数额' }}</label>
            <el-input-number v-model="editForm.amount" :min="1" :max="999" controls-position="right" />
          </div>
          <div>
            <label>新定阳寿</label>
            <div class="lb-static lb-static--gold">{{ resultLifespan }} 年</div>
          </div>
        </div>
        <div class="lb-field">
          <label>缘由</label>
          <el-input
            v-model="editForm.reason"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
            placeholder="例：阳世积德行善，准添寿五年 / 寿数已尽，依律勾销"
          />
        </div>
        <div class="lb-tip">
          录入后生成「待复核」单，须由复核判官核准方生效；复核前可再次修改。
        </div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" @click="editDialog.open = false">取 消</el-button>
        <el-button class="mv-seal-btn mv-seal-btn--sm" :loading="submitting" @click="submitEdit">
          录 入 待 复 核
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.lb-overview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  flex-wrap: wrap;
}
.lb-stats {
  display: flex;
  gap: 26px;
  flex-wrap: wrap;
}
.lb-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.lb-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.1em;
}
.lb-stat__value {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 22px;
  color: var(--mv-paper);
}
.lb-stat__value--gold {
  color: var(--mv-gold);
}
.lb-stat__value--red {
  color: #d4553f;
}
.lb-actions {
  display: flex;
  gap: 8px;
}
.lb-tabs {
  display: flex;
  gap: 6px;
  padding: 4px 18px 0;
  border-bottom: 1px solid rgba(232, 227, 214, 0.08);
}
.lb-tab {
  position: relative;
  padding: 10px 16px;
  background: transparent;
  border: none;
  color: var(--mv-muted);
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 15px;
  letter-spacing: 0.14em;
  cursor: pointer;
  transition: color 0.2s;
}
.lb-tab:hover {
  color: var(--mv-paper);
}
.lb-tab.is-active {
  color: var(--mv-gold);
}
.lb-tab.is-active::after {
  content: '';
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: -1px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--mv-cinnabar), transparent);
}
.lb-tab__count {
  margin-left: 6px;
  font-size: 11px;
  font-style: normal;
  color: var(--mv-muted);
}
.lb-filters {
  border-bottom: none;
}
.lb-w220 {
  width: 220px;
}
.lb-w140 {
  width: 140px;
}
.lb-w130 {
  width: 130px;
}
.lb-check :deep(.el-checkbox__label) {
  color: var(--mv-muted);
  font-size: 12px;
}
.mv-table :deep(.el-table__row) {
  cursor: pointer;
}
.lb-flag {
  margin-left: 6px;
  padding: 0 4px;
  font-size: 10px;
  color: #d4553f;
  border: 1px solid rgba(212, 85, 63, 0.5);
  border-radius: 2px;
}
.lb-action {
  padding: 1px 6px;
  font-size: 12px;
  border: 1px solid;
  border-radius: 2px;
}
.lb-lifespan {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 16px;
  color: var(--mv-paper);
  margin-right: 2px;
}
.lb-badge {
  padding: 1px 8px;
  font-size: 12px;
  border: 1px solid;
  border-radius: 2px;
}
.lb-row-actions {
  display: flex;
  gap: 8px;
}
.lb-link {
  color: var(--mv-muted);
  font-size: 12px;
}
.lb-link--ok {
  color: var(--mv-phosphor);
}
.lb-link--bad {
  color: #d4553f;
}
.lb-pager {
  display: flex;
  justify-content: flex-end;
  padding: 10px 18px 4px;
}
.lb-empty {
  padding: 26px 0;
  color: var(--mv-muted);
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  letter-spacing: 0.16em;
}
.lb-drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}
.lb-drawer-title {
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
  font-size: 20px;
  color: var(--mv-paper);
  letter-spacing: 0.12em;
}
.lb-drawer-sub {
  font-size: 12px;
  color: var(--mv-muted);
}
.lb-desc :deep(.el-descriptions__label) {
  width: 92px;
}
.lb-diff {
  display: flex;
  align-items: stretch;
  gap: 10px;
  margin-top: 16px;
}
.lb-diff__col {
  flex: 1;
  padding: 10px 12px;
  background: rgba(232, 227, 214, 0.04);
  border: 1px solid rgba(232, 227, 214, 0.12);
  border-radius: 2px;
}
.lb-diff__label {
  font-size: 11px;
  color: var(--mv-muted);
  letter-spacing: 0.12em;
}
.lb-diff__col p {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--mv-paper);
  line-height: 1.6;
}
.lb-diff__arrow {
  align-self: center;
  color: var(--mv-gold);
}
.lb-drawer-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}
.lb-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.lb-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.lb-field label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.12em;
}
.lb-field--row {
  flex-direction: row;
  gap: 18px;
}
.lb-field--row > div {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.lb-static {
  height: 32px;
  line-height: 32px;
  padding: 0 10px;
  color: var(--mv-paper);
  background: rgba(232, 227, 214, 0.05);
  border: 1px solid rgba(232, 227, 214, 0.14);
  border-radius: 2px;
  font-family: var(--mv-font-title, 'Kaiti SC', serif);
}
.lb-static--gold {
  color: var(--mv-gold);
}
.lb-tip {
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--mv-muted);
  border-left: 2px solid rgba(201, 162, 39, 0.5);
  background: rgba(201, 162, 39, 0.06);
}
</style>
