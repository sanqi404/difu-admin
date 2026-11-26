<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchDocuments, fetchSoul, transitionSoul, verifyDocument } from '@/api'
import type { DocumentItem, SoulItem } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime, statusStyle } from '@/utils/status'

const { hasPerm } = usePerms()

const canVerify = computed(() => hasPerm('doc:verify'))
const canTransfer = computed(() => hasPerm('soul:transfer'))

const keyword = ref('')
const scope = ref<'pending' | 'all'>('pending')
const loading = ref(false)
const docs = ref<DocumentItem[]>([])
const active = ref<DocumentItem | null>(null)
const soul = ref<SoulItem | null>(null)
const soulLoading = ref(false)
const acting = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await fetchDocuments({
      keyword: keyword.value || undefined,
      doc_type: '路引',
      status: scope.value === 'pending' ? '已签发' : undefined,
      page: 1,
      page_size: 30,
    })
    docs.value = res.items || []
    if (docs.value.length) {
      await select(docs.value[0])
    } else {
      active.value = null
      soul.value = null
    }
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '路引检索失败')
  } finally {
    loading.value = false
  }
}

async function select(doc: DocumentItem) {
  active.value = doc
  soul.value = null
  if (doc.soul_id) {
    soulLoading.value = true
    try {
      soul.value = await fetchSoul(doc.soul_id)
    } catch {
      soul.value = null
    } finally {
      soulLoading.value = false
    }
  }
}

/* ---------------- 验引判定 ---------------- */
const checks = computed(() => {
  const doc = active.value
  const s = soul.value
  return [
    {
      key: 'issued',
      label: '路引已签发',
      pass: !!doc && (doc.status === '已签发' || doc.status === '已核验'),
      hint: doc ? `当前「${doc.status}」` : '未选定文书',
    },
    {
      key: 'valid',
      label: '文书未作废',
      pass: !!doc && doc.status !== '已作废',
      hint: doc && doc.status === '已作废' ? '已作废，禁止通行' : '有效',
    },
    {
      key: 'soul',
      label: '亡魂在押且已备案',
      pass: s?.status === '已备案' || s?.status === '已过境',
      hint: s ? `当前「${s.status}」` : doc?.soul_id ? '亡魂读取失败' : '文书未关联亡魂',
    },
  ]
})

const verdict = computed(() => {
  const ok = checks.value.every((c) => c.pass)
  const crossed = soul.value?.status === '已过境'
  if (ok && crossed) {
    return { ok: true, title: '已过此关', desc: '路引已核验，亡魂已过境，可前往迷魂殿录供。' }
  }
  if (ok) {
    return { ok: true, title: '准予过境', desc: '三关核查通过，核验路引后即可放行亡魂过境。' }
  }
  return {
    ok: false,
    title: '禁止通行',
    desc: checks.value.filter((c) => !c.pass).map((c) => `${c.label}（${c.hint}）`).join('；'),
  }
})

/** 是否还允许执行 cross 动作 */
const canCross = computed(
  () => soul.value?.status === '已备案' && (soul.value?.allowed_actions || []).some((a) => a.action === 'cross'),
)

async function doVerify() {
  if (!active.value) return
  acting.value = true
  try {
    const updated = await verifyDocument(active.value.id)
    ElMessage.success(`${updated.doc_no} 已核验`)
    const idx = docs.value.findIndex((d) => d.id === updated.id)
    if (idx >= 0) docs.value[idx] = updated
    active.value = updated
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '核验失败')
  } finally {
    acting.value = false
  }
}

async function doCross() {
  if (!soul.value) return
  acting.value = true
  try {
    await transitionSoul(soul.value.id, { action: 'cross', reason: '鬼门关验引放行' })
    ElMessage.success(`${soul.value.name} 已过鬼门关`)
    await select(active.value!)
    await load()
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '放行失败')
  } finally {
    acting.value = false
  }
}

const stats = computed(() => {
  const list = docs.value
  return {
    total: list.length,
    issued: list.filter((d) => d.status === '已签发').length,
    verified: list.filter((d) => d.status === '已核验').length,
  }
})

onMounted(load)
</script>

<template>
  <div class="gv-page">
    <div class="mv-panel gv-banner">
      <div class="gv-banner__main">
        <h2 class="mv-title">鬼门关验引</h2>
        <p class="mv-subtitle">亡魂过境须持城隍签发之路引，验引无误方可放行入酆都。</p>
      </div>
      <div class="gv-banner__stats">
        <div class="gv-stat">
          <span class="gv-stat__label">待验</span>
          <strong class="gv-stat__value mv-gold">{{ stats.issued }}</strong>
        </div>
        <div class="gv-stat">
          <span class="gv-stat__label">已验</span>
          <strong class="gv-stat__value mv-teal">{{ stats.verified }}</strong>
        </div>
        <div class="gv-stat">
          <span class="gv-stat__label">本屏合计</span>
          <strong class="gv-stat__value">{{ stats.total }}</strong>
        </div>
      </div>
    </div>

    <div class="gv-body">
      <!-- 左：路引检索 -->
      <section class="mv-panel gv-left">
        <div class="gv-search">
          <el-input
            v-model="keyword"
            placeholder="路引编号 / 亡魂姓名 / 文书标题"
            clearable
            size="small"
            @keyup.enter="load"
            @clear="load"
          />
          <el-button class="mv-seal-btn" size="small" @click="load">验引</el-button>
        </div>
        <div class="gv-scope">
          <button
            class="gv-scope__btn"
            :class="{ 'is-active': scope === 'pending' }"
            @click="scope = 'pending'; load()"
          >待核验路引</button>
          <button
            class="gv-scope__btn"
            :class="{ 'is-active': scope === 'all' }"
            @click="scope = 'all'; load()"
          >全部路引</button>
        </div>

        <div v-loading="loading" class="gv-list">
          <button
            v-for="doc in docs"
            :key="doc.id"
            class="gv-item"
            :class="{ 'is-active': active?.id === doc.id }"
            @click="select(doc)"
          >
            <div class="gv-item__head">
              <span class="gv-item__no">{{ doc.doc_no }}</span>
              <span
                class="gv-tag"
                :style="{
                  color: statusStyle(doc.status).color,
                  borderColor: statusStyle(doc.status).border,
                  background: statusStyle(doc.status).bg,
                }"
              >{{ doc.status }}</span>
            </div>
            <div class="gv-item__soul">{{ doc.soul_name || '未关联亡魂' }}</div>
            <div class="gv-item__time">{{ doc.issued_at ? formatDateTime(doc.issued_at) : '未签发' }}</div>
          </button>
          <div v-if="!loading && !docs.length" class="gv-empty">此条件下无路引，关口清静</div>
        </div>
      </section>

      <!-- 右：验引台 -->
      <section class="mv-panel gv-right">
        <template v-if="active">
          <div class="gv-verdict" :class="verdict.ok ? 'is-pass' : 'is-block'">
            <div class="gv-verdict__badge">{{ verdict.ok ? '放行' : '拦下' }}</div>
            <div>
              <div class="gv-verdict__title">{{ verdict.title }}</div>
              <div class="gv-verdict__desc">{{ verdict.desc }}</div>
            </div>
          </div>

          <div class="gv-doc">
            <div class="gv-doc__no">{{ active.doc_no }}</div>
            <div class="gv-doc__title">{{ active.title || '（无题）' }}</div>
            <dl class="gv-doc__grid">
              <div><dt>关联亡魂</dt><dd>{{ active.soul_name || '—' }}</dd></div>
              <div><dt>文书状态</dt><dd>{{ active.status }}</dd></div>
              <div><dt>签发人</dt><dd>{{ active.issued_by || '—' }}</dd></div>
              <div><dt>签发时间</dt><dd>{{ formatDateTime(active.issued_at) }}</dd></div>
            </dl>
            <div class="gv-doc__content">{{ active.content || '（正文空白）' }}</div>
          </div>

          <div class="gv-block">
            <div class="gv-block__title">过境核查</div>
            <div v-for="c in checks" :key="c.key" class="gv-check" :class="{ 'is-pass': c.pass }">
              <span class="gv-check__dot"></span>
              <span class="gv-check__label">{{ c.label }}</span>
              <span class="gv-check__hint">{{ c.hint }}</span>
            </div>
          </div>

          <div v-loading="soulLoading" class="gv-soul">
            <template v-if="soul">
              <div class="gv-block__title">在押亡魂</div>
              <dl class="gv-doc__grid">
                <div><dt>姓名</dt><dd>{{ soul.name }}</dd></div>
                <div><dt>亡魂编号</dt><dd>{{ soul.soul_no }}</dd></div>
                <div><dt>当前状态</dt><dd class="mv-teal">{{ soul.status }}</dd></div>
                <div><dt>死因类型</dt><dd>{{ soul.death_type || '—' }}</dd></div>
              </dl>
            </template>
            <div v-else-if="!soulLoading" class="gv-dim">该路引未关联亡魂，无法核对亡魂状态</div>
          </div>

          <div class="gv-ops">
            <el-button
              v-if="canVerify && active.status === '已签发'"
              class="mv-seal-btn"
              size="small"
              :loading="acting"
              @click="doVerify"
            >核验路引</el-button>
            <el-button
              v-if="canTransfer && canCross"
              class="mv-seal-btn"
              size="small"
              :loading="acting"
              @click="doCross"
            >放行过境</el-button>
            <span v-if="active.status === '已核验'" class="gv-dim">路引已核验，印章在册</span>
            <span v-if="!canVerify && !canTransfer" class="gv-dim">当前账号无验引或放行权限</span>
          </div>
        </template>
        <div v-else class="gv-placeholder">
          <div class="gv-placeholder__gate">鬼门关</div>
          <div class="gv-placeholder__text">左侧择一路引，以验引鉴核之</div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.gv-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.gv-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.gv-banner__main {
  max-width: 520px;
}
.gv-banner__main .mv-subtitle {
  margin-top: 8px;
  line-height: 1.75;
}
.gv-banner__stats {
  display: flex;
  gap: 10px;
}
.gv-stat {
  min-width: 88px;
  padding: 8px 12px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.gv-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.gv-stat__value {
  font-family: var(--mv-font-title);
  font-size: 22px;
  line-height: 1.1;
}
.gv-body {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.gv-left {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
}
.gv-search {
  display: flex;
  gap: 8px;
}
.gv-scope {
  display: flex;
  gap: 6px;
}
.gv-scope__btn {
  flex: 1;
  padding: 6px 0;
  font-size: 12px;
  color: var(--mv-muted);
  background: transparent;
  border: 1px solid rgba(232, 227, 214, 0.12);
  cursor: pointer;
  transition: all 0.18s;
}
.gv-scope__btn.is-active {
  color: var(--mv-gold);
  border-color: rgba(201, 162, 39, 0.6);
  background: rgba(201, 162, 39, 0.08);
}
.gv-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 620px;
  overflow: auto;
}
.gv-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 12px;
  text-align: left;
  background: rgba(232, 227, 214, 0.02);
  border: 1px solid rgba(232, 227, 214, 0.1);
  cursor: pointer;
  transition: all 0.16s;
}
.gv-item:hover {
  border-color: rgba(201, 162, 39, 0.4);
}
.gv-item.is-active {
  border-color: rgba(201, 162, 39, 0.8);
  background: rgba(201, 162, 39, 0.07);
}
.gv-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.gv-item__no {
  font-size: 12px;
  letter-spacing: 0.1em;
  color: var(--mv-paper);
}
.gv-item__soul {
  font-family: var(--mv-font-title);
  font-size: 15px;
  color: var(--mv-paper);
}
.gv-item__time {
  font-size: 11px;
  color: var(--mv-muted);
}
.gv-tag {
  padding: 1px 7px;
  font-size: 11px;
  border: 1px solid transparent;
  border-radius: 2px;
}
.gv-empty {
  padding: 30px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
.gv-right {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 20px;
  min-height: 480px;
}
.gv-verdict {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(232, 227, 214, 0.14);
}
.gv-verdict.is-pass {
  border-color: rgba(76, 224, 195, 0.5);
  background: rgba(76, 224, 195, 0.07);
}
.gv-verdict.is-block {
  border-color: rgba(224, 91, 69, 0.5);
  background: rgba(179, 38, 30, 0.1);
}
.gv-verdict__badge {
  font-family: var(--mv-font-title);
  font-size: 20px;
  padding: 6px 14px;
  letter-spacing: 0.2em;
  border: 1px solid currentColor;
}
.gv-verdict.is-pass .gv-verdict__badge {
  color: #4ce0c3;
}
.gv-verdict.is-block .gv-verdict__badge {
  color: #e05b45;
}
.gv-verdict__title {
  font-family: var(--mv-font-title);
  font-size: 17px;
  color: var(--mv-paper);
}
.gv-verdict__desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--mv-muted);
}
.gv-doc {
  padding: 14px 16px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.02);
}
.gv-doc__no {
  font-size: 12px;
  letter-spacing: 0.14em;
  color: var(--mv-muted);
}
.gv-doc__title {
  margin: 4px 0 10px;
  font-family: var(--mv-font-title);
  font-size: 18px;
  color: var(--mv-gold);
}
.gv-doc__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0 0 12px;
}
.gv-doc__grid div {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(232, 227, 214, 0.1);
}
.gv-doc__grid dt {
  font-size: 12px;
  color: var(--mv-muted);
}
.gv-doc__grid dd {
  margin: 0;
  font-size: 13px;
  color: var(--mv-paper);
}
.gv-doc__content {
  max-height: 140px;
  overflow: auto;
  padding: 10px 12px;
  font-family: var(--mv-font-title);
  font-size: 13px;
  line-height: 1.85;
  white-space: pre-wrap;
  color: var(--mv-paper);
  border: 1px solid rgba(232, 227, 214, 0.1);
  background: rgba(11, 11, 16, 0.45);
}
.gv-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.gv-block__title {
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--mv-muted);
}
.gv-check {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-left: 2px solid rgba(224, 91, 69, 0.7);
  background: rgba(179, 38, 30, 0.07);
}
.gv-check.is-pass {
  border-left-color: rgba(76, 224, 195, 0.8);
  background: rgba(76, 224, 195, 0.06);
}
.gv-check__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #e05b45;
}
.gv-check.is-pass .gv-check__dot {
  background: #4ce0c3;
}
.gv-check__label {
  font-size: 13px;
  color: var(--mv-paper);
}
.gv-check__hint {
  margin-left: auto;
  font-size: 12px;
  color: var(--mv-muted);
}
.gv-soul {
  min-height: 60px;
}
.gv-ops {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 4px;
}
.gv-dim {
  font-size: 12px;
  color: var(--mv-muted);
}
.gv-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.gv-placeholder__gate {
  font-family: var(--mv-font-title);
  font-size: 40px;
  letter-spacing: 0.3em;
  color: rgba(201, 162, 39, 0.28);
}
.gv-placeholder__text {
  font-size: 12px;
  color: var(--mv-muted);
}
@media (max-width: 1200px) {
  .gv-body {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
