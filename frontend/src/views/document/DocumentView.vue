<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createDocument,
  fetchDocuments,
  fetchSouls,
  issueDocument,
  verifyDocument,
  voidDocument,
} from '@/api'
import type { DocumentItem, SoulItem } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime } from '@/utils/status'

const { hasPerm } = usePerms()

const DOC_TYPES = ['路引', '拘票', '判决书', '轮回文书', '还阳令', '冻结令']
const DOC_STATUS = ['草稿', '已签发', '已核验', '已作废']
const DOC_PREFIX: Record<string, string> = {
  路引: 'LY',
  拘票: 'JP',
  判决书: 'PJ',
  轮回文书: 'LH',
  还阳令: 'HY',
  冻结令: 'DJ',
}

const canIssue = computed(() => hasPerm('doc:issue'))
const canVerify = computed(() => hasPerm('doc:verify'))
const canVoid = computed(() => hasPerm('doc:void'))

const loading = ref(false)
const rows = ref<DocumentItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const query = reactive({ keyword: '', doc_type: '', status: '' })

/** 类型/状态统计（独立取一页大样本） */
const statRows = ref<DocumentItem[]>([])

async function loadStats() {
  try {
    const res = await fetchDocuments({ page: 1, page_size: 200 })
    statRows.value = res.items || []
  } catch {
    statRows.value = []
  }
}

const typeStats = computed(() => {
  const map: Record<string, number> = {}
  DOC_TYPES.forEach((t) => (map[t] = 0))
  statRows.value.forEach((d) => (map[d.doc_type] = (map[d.doc_type] || 0) + 1))
  return DOC_TYPES.map((t) => ({ type: t, count: map[t] || 0, prefix: DOC_PREFIX[t] }))
})

const statusStats = computed(() => {
  const map: Record<string, number> = {}
  DOC_STATUS.forEach((s) => (map[s] = 0))
  statRows.value.forEach((d) => (map[d.status] = (map[d.status] || 0) + 1))
  return DOC_STATUS.map((s) => ({ status: s, count: map[s] || 0 }))
})

function statusStyle(status: string) {
  if (status === '已核验') return { color: '#4ce0c3', border: 'rgba(76,224,195,0.42)', bg: 'rgba(76,224,195,0.1)' }
  if (status === '已签发') return { color: '#c9a227', border: 'rgba(201,162,39,0.42)', bg: 'rgba(201,162,39,0.1)' }
  if (status === '已作废') return { color: '#e05b45', border: 'rgba(224,91,69,0.42)', bg: 'rgba(179,38,30,0.14)' }
  return { color: '#8fa3b8', border: 'rgba(143,163,184,0.4)', bg: 'rgba(143,163,184,0.12)' }
}

async function load() {
  loading.value = true
  try {
    const res = await fetchDocuments({
      keyword: query.keyword || undefined,
      doc_type: query.doc_type || undefined,
      status: query.status || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = res.items || []
    total.value = res.meta?.total ?? rows.value.length
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '文书台账读取失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.keyword = ''
  query.doc_type = ''
  query.status = ''
  page.value = 1
  load()
}

function pickType(type: string) {
  query.doc_type = query.doc_type === type ? '' : type
  page.value = 1
  load()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

/* ---------------- 起草 ---------------- */
const dialog = ref(false)
const saving = ref(false)
const soulLoading = ref(false)
const soulOptions = ref<SoulItem[]>([])
const form = reactive({
  doc_type: '路引',
  title: '',
  soul_id: undefined as number | undefined,
  content: '',
})

async function searchSouls(keyword: string) {
  soulLoading.value = true
  try {
    const res = await fetchSouls({ keyword: keyword || undefined, page: 1, page_size: 20 })
    soulOptions.value = res.items || []
  } catch {
    soulOptions.value = []
  } finally {
    soulLoading.value = false
  }
}

function openCreate(type?: string) {
  form.doc_type = type || (query.doc_type || '路引')
  form.title = ''
  form.soul_id = undefined
  form.content = ''
  soulOptions.value = []
  searchSouls('')
  dialog.value = true
}

async function submit() {
  saving.value = true
  try {
    await createDocument({
      doc_type: form.doc_type,
      title: form.title || undefined,
      soul_id: form.soul_id ?? null,
      content: form.content,
    })
    ElMessage.success('文书已起草')
    dialog.value = false
    page.value = 1
    await Promise.all([load(), loadStats()])
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '起草失败')
  } finally {
    saving.value = false
  }
}

/* ---------------- 状态操作 ---------------- */
async function doIssue(row: DocumentItem) {
  try {
    await issueDocument(row.id)
    ElMessage.success(`${row.doc_no} 已签发`)
    await Promise.all([load(), loadStats()])
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '签发失败')
  }
}

async function doVerify(row: DocumentItem) {
  try {
    await verifyDocument(row.id)
    ElMessage.success(`${row.doc_no} 已核验`)
    await Promise.all([load(), loadStats()])
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '核验失败')
  }
}

async function doVoid(row: DocumentItem) {
  try {
    await ElMessageBox.confirm(
      `确定作废文书「${row.doc_no} · ${row.title}」？作废后不可核验，操作将写入阴律日志（告警级）。`,
      '作废文书',
      { confirmButtonText: '作废', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await voidDocument(row.id)
    ElMessage.success(`${row.doc_no} 已作废`)
    await Promise.all([load(), loadStats()])
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '作废失败')
  }
}

/* ---------------- 详情 ---------------- */
const detail = ref<DocumentItem | null>(null)
const detailVisible = ref(false)

function openDetail(row: DocumentItem) {
  detail.value = row
  detailVisible.value = true
}

onMounted(() => {
  load()
  loadStats()
})
</script>

<template>
  <div class="dc-page">
    <div class="mv-panel dc-banner">
      <div class="dc-banner__main">
        <h2 class="mv-title">文书台账</h2>
        <p class="mv-subtitle">路引、拘票、判决书、轮回文书、还阳令、冻结令之起草、签发、核验与作废。</p>
      </div>
      <div class="dc-banner__stats">
        <div v-for="s in statusStats" :key="s.status" class="dc-stat">
          <span class="dc-stat__label">{{ s.status }}</span>
          <strong class="dc-stat__value" :style="{ color: statusStyle(s.status).color }">{{ s.count }}</strong>
        </div>
      </div>
    </div>

    <div class="dc-types">
      <button
        v-for="t in typeStats"
        :key="t.type"
        class="mv-panel dc-type"
        :class="{ 'is-active': query.doc_type === t.type }"
        @click="pickType(t.type)"
      >
        <span class="dc-type__prefix">{{ t.prefix }}</span>
        <span class="dc-type__name">{{ t.type }}</span>
        <strong class="dc-type__count">{{ t.count }}</strong>
      </button>
    </div>

    <section class="mv-panel dc-list">
      <div class="mv-panel__head">
        <span class="mv-panel__title">文书清单</span>
        <div class="dc-filters">
          <el-input
            v-model="query.keyword"
            placeholder="编号 / 标题 / 亡魂"
            clearable
            size="small"
            class="dc-w200"
            @keyup.enter="page = 1; load()"
            @clear="page = 1; load()"
          />
          <el-select v-model="query.status" placeholder="全部状态" clearable size="small" class="dc-w120" @change="page = 1; load()">
            <el-option v-for="s in DOC_STATUS" :key="s" :label="s" :value="s" />
          </el-select>
          <el-button class="mv-ghost-btn" size="small" @click="page = 1; load()">查阅</el-button>
          <el-button class="mv-ghost-btn" size="small" @click="resetQuery">重置</el-button>
          <el-button v-if="canIssue" class="mv-seal-btn" size="small" @click="openCreate()">起草文书</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" size="small">
        <el-table-column prop="doc_no" label="文书编号" width="128" />
        <el-table-column label="类型" width="106">
          <template #default="{ row }">
            <span class="dc-type-tag">{{ row.doc_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <button class="dc-title" @click="openDetail(row)">{{ row.title || '（无题）' }}</button>
          </template>
        </el-table-column>
        <el-table-column prop="soul_name" label="关联亡魂" width="110">
          <template #default="{ row }">{{ row.soul_name || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="92">
          <template #default="{ row }">
            <span
              class="dc-tag"
              :style="{
                color: statusStyle(row.status).color,
                borderColor: statusStyle(row.status).border,
                background: statusStyle(row.status).bg,
              }"
            >{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="签发" width="170">
          <template #default="{ row }">
            <div v-if="row.issued_at" class="dc-cell">
              <span>{{ row.issued_by || '—' }}</span>
              <span class="dc-cell__time">{{ formatDateTime(row.issued_at) }}</span>
            </div>
            <span v-else class="dc-dim">待签发</span>
          </template>
        </el-table-column>
        <el-table-column label="核验" width="170">
          <template #default="{ row }">
            <div v-if="row.verified_at" class="dc-cell">
              <span>{{ row.verified_by || '—' }}</span>
              <span class="dc-cell__time">{{ formatDateTime(row.verified_at) }}</span>
            </div>
            <span v-else class="dc-dim">未核验</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <div class="dc-actions">
              <el-button link class="dc-link" @click="openDetail(row)">详情</el-button>
              <el-button
                v-if="canIssue && row.status === '草稿'"
                link
                class="dc-link dc-link--gold"
                @click="doIssue(row)"
              >签发</el-button>
              <el-button
                v-if="canVerify && row.status === '已签发'"
                link
                class="dc-link dc-link--teal"
                @click="doVerify(row)"
              >核验</el-button>
              <el-button
                v-if="canVoid && row.status !== '已作废'"
                link
                class="dc-link dc-link--red"
                @click="doVoid(row)"
              >作废</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="dc-empty">此条件下无文书，案牍未立</div>
        </template>
      </el-table>

      <div class="dc-pager">
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

    <!-- 详情 -->
    <el-drawer v-model="detailVisible" title="文书详情" size="460px">
      <div v-if="detail" class="dc-detail">
        <div class="dc-detail__no">{{ detail.doc_no }}</div>
        <div class="dc-detail__title">{{ detail.title || '（无题）' }}</div>
        <div class="dc-detail__tags">
          <span class="dc-type-tag">{{ detail.doc_type }}</span>
          <span
            class="dc-tag"
            :style="{
              color: statusStyle(detail.status).color,
              borderColor: statusStyle(detail.status).border,
              background: statusStyle(detail.status).bg,
            }"
          >{{ detail.status }}</span>
        </div>
        <dl class="dc-detail__grid">
          <div><dt>关联亡魂</dt><dd>{{ detail.soul_name || '—' }}</dd></div>
          <div><dt>签发网点</dt><dd>{{ detail.city_god_id ?? '—' }}</dd></div>
          <div><dt>签发人</dt><dd>{{ detail.issued_by || '—' }}</dd></div>
          <div><dt>签发时间</dt><dd>{{ formatDateTime(detail.issued_at) }}</dd></div>
          <div><dt>核验人</dt><dd>{{ detail.verified_by || '—' }}</dd></div>
          <div><dt>核验时间</dt><dd>{{ formatDateTime(detail.verified_at) }}</dd></div>
        </dl>
        <div class="dc-detail__label">正文</div>
        <pre class="dc-detail__content">{{ detail.content || '（正文空白）' }}</pre>
        <div class="dc-detail__ops">
          <el-button
            v-if="canIssue && detail.status === '草稿'"
            class="mv-seal-btn"
            size="small"
            @click="detailVisible = false; doIssue(detail)"
          >签发</el-button>
          <el-button
            v-if="canVerify && detail.status === '已签发'"
            class="mv-seal-btn"
            size="small"
            @click="detailVisible = false; doVerify(detail)"
          >核验</el-button>
          <el-button
            v-if="canVoid && detail.status !== '已作废'"
            class="mv-ghost-btn"
            size="small"
            @click="detailVisible = false; doVoid(detail)"
          >作废</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 起草 -->
    <el-dialog v-model="dialog" title="起草文书" width="560px">
      <div class="dc-form">
        <div class="dc-form__row">
          <label>文书类型</label>
          <el-select v-model="form.doc_type" size="small" class="dc-full">
            <el-option v-for="t in DOC_TYPES" :key="t" :label="`${t}（${DOC_PREFIX[t]}）`" :value="t" />
          </el-select>
        </div>
        <div class="dc-form__row">
          <label>标题</label>
          <el-input v-model="form.title" size="small" placeholder="留空则按类型与亡魂自动生成" />
        </div>
        <div class="dc-form__row">
          <label>关联亡魂</label>
          <el-select
            v-model="form.soul_id"
            size="small"
            class="dc-full"
            filterable
            remote
            clearable
            reserve-keyword
            :remote-method="searchSouls"
            :loading="soulLoading"
            placeholder="输入姓名检索亡魂（可不关联）"
          >
            <el-option
              v-for="s in soulOptions"
              :key="s.id"
              :label="`${s.name} · ${s.soul_no} · ${s.status}`"
              :value="s.id"
            />
          </el-select>
        </div>
        <div class="dc-form__row dc-form__row--top">
          <label>正文</label>
          <el-input v-model="form.content" type="textarea" :rows="5" size="small" maxlength="2000" show-word-limit />
        </div>
        <div class="dc-note">文书起草后为「草稿」，需签发方可生效；路引须经鬼门关验引核验后才可放行。</div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" size="small" @click="dialog = false">取消</el-button>
        <el-button class="mv-seal-btn" size="small" :loading="saving" @click="submit">起草</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.dc-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dc-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.dc-banner__main {
  max-width: 520px;
}
.dc-banner__main .mv-subtitle {
  margin-top: 8px;
  line-height: 1.75;
}
.dc-banner__stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.dc-stat {
  min-width: 82px;
  padding: 8px 12px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dc-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.dc-stat__value {
  font-family: var(--mv-font-title);
  font-size: 22px;
  line-height: 1.1;
}
.dc-types {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}
.dc-type {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.18s;
}
.dc-type:hover {
  border-color: rgba(201, 162, 39, 0.42);
}
.dc-type.is-active {
  border-color: rgba(201, 162, 39, 0.75);
  box-shadow: inset 0 -2px 0 rgba(179, 38, 30, 0.6);
}
.dc-type__prefix {
  font-size: 11px;
  letter-spacing: 0.16em;
  color: var(--mv-muted);
}
.dc-type__name {
  font-family: var(--mv-font-title);
  font-size: 15px;
  color: var(--mv-paper);
}
.dc-type__count {
  font-size: 18px;
  color: var(--mv-gold);
}
.dc-list {
  padding-bottom: 6px;
}
.dc-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.dc-w200 {
  width: 200px;
}
.dc-w120 {
  width: 120px;
}
.dc-title {
  background: transparent;
  border: none;
  padding: 0;
  color: var(--mv-paper);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}
.dc-title:hover {
  color: var(--mv-gold);
}
.dc-type-tag {
  display: inline-block;
  padding: 1px 7px;
  font-size: 12px;
  border: 1px solid rgba(201, 162, 39, 0.36);
  color: var(--mv-gold);
  border-radius: 2px;
}
.dc-tag {
  display: inline-block;
  padding: 1px 8px;
  font-size: 12px;
  border: 1px solid transparent;
  border-radius: 2px;
}
.dc-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}
.dc-cell__time {
  color: var(--mv-muted);
}
.dc-dim {
  font-size: 12px;
  color: var(--mv-muted);
}
.dc-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.dc-link {
  color: var(--mv-muted);
  padding: 0;
  font-size: 12px;
}
.dc-link--gold {
  color: var(--mv-gold);
}
.dc-link--teal {
  color: var(--mv-phosphor, #4ce0c3);
}
.dc-link--red {
  color: #e05b45;
}
.dc-pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px 6px;
}
.dc-empty {
  padding: 26px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
.dc-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dc-detail__no {
  font-size: 12px;
  letter-spacing: 0.14em;
  color: var(--mv-muted);
}
.dc-detail__title {
  font-family: var(--mv-font-title);
  font-size: 19px;
  color: var(--mv-gold);
}
.dc-detail__tags {
  display: flex;
  gap: 8px;
}
.dc-detail__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}
.dc-detail__grid div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(232, 227, 214, 0.1);
}
.dc-detail__grid dt {
  font-size: 12px;
  color: var(--mv-muted);
}
.dc-detail__grid dd {
  margin: 0;
  font-size: 13px;
  color: var(--mv-paper);
}
.dc-detail__label {
  font-size: 12px;
  letter-spacing: 0.1em;
  color: var(--mv-muted);
}
.dc-detail__content {
  margin: 0;
  max-height: 300px;
  overflow: auto;
  padding: 12px 14px;
  font-family: var(--mv-font-title);
  font-size: 13px;
  line-height: 1.9;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--mv-paper);
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
}
.dc-detail__ops {
  display: flex;
  gap: 8px;
}
.dc-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dc-form__row {
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}
.dc-form__row--top {
  align-items: flex-start;
}
.dc-form__row label {
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--mv-muted);
}
.dc-full {
  width: 100%;
}
.dc-note {
  padding: 9px 12px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--mv-muted);
  border: 1px solid rgba(232, 227, 214, 0.1);
  background: rgba(232, 227, 214, 0.03);
}
@media (max-width: 1360px) {
  .dc-types {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
