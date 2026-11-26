<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchDocuments, fetchSoul, fetchSouls, transitionSoul } from '@/api'
import type { DocumentItem, SoulItem } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime, karmaStyle } from '@/utils/status'

const { hasPerm } = usePerms()
const canTransfer = computed(() => hasPerm('soul:transfer'))

const REGIONS = ['东方', '南方', '西方', '北方', '中央']

const loading = ref(false)
const queue = ref<SoulItem[]>([])
const total = ref(0)
const query = reactive({ keyword: '', region: '' })

const activeId = ref<number | null>(null)
const detail = ref<SoulItem | null>(null)
const detailLoading = ref(false)
const routeDoc = ref<DocumentItem | null>(null)

const confession = ref('')
const acting = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await fetchSouls({
      status: '已过境',
      keyword: query.keyword || undefined,
      region: query.region || undefined,
      page: 1,
      page_size: 50,
    })
    queue.value = res.items || []
    total.value = res.meta?.total ?? queue.value.length
    if (!queue.value.some((s) => s.id === activeId.value)) {
      activeId.value = queue.value.length ? queue.value[0].id : null
      await pick(activeId.value)
    }
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '待录供队列读取失败')
  } finally {
    loading.value = false
  }
}

async function pendingCount() {
  try {
    const res = await fetchSouls({ status: '待审', page: 1, page_size: 1 })
    return res.meta?.total ?? 0
  } catch {
    return 0
  }
}

const recorded = ref(0)

async function pick(id: number | null) {
  if (!id) {
    detail.value = null
    routeDoc.value = null
    return
  }
  activeId.value = id
  confession.value = ''
  detailLoading.value = true
  detail.value = null
  routeDoc.value = null
  try {
    detail.value = await fetchSoul(id)
    // 该魂的路引，用于核对过境凭证
    const docs = await fetchDocuments({ soul_id: id, doc_type: '路引', page: 1, page_size: 1 })
    routeDoc.value = docs.items?.[0] || null
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '亡魂档案读取失败')
  } finally {
    detailLoading.value = false
  }
}

async function submit() {
  if (!detail.value) return
  if (confession.value.trim().length < 10) {
    ElMessage.warning('供词过简，请详录亡魂自陈（不少于 10 字）')
    return
  }
  acting.value = true
  try {
    await transitionSoul(detail.value.id, {
      action: 'confess',
      reason: `迷魂殿录供：${confession.value.trim()}`,
    })
    ElMessage.success(`${detail.value.name} 已录供，转呈待审`)
    detail.value = null
    activeId.value = null
    await load()
    recorded.value = await pendingCount()
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '录供失败')
  } finally {
    acting.value = false
  }
}

const stats = computed(() => ({
  queue: total.value,
  shown: queue.value.length,
  highSin: queue.value.filter((s) => s.sin_level === '重' || s.sin_level === '极重').length,
}))

onMounted(async () => {
  await load()
  recorded.value = await pendingCount()
})
</script>

<template>
  <div class="lr-page">
    <div class="mv-panel lr-banner">
      <div class="lr-banner__main">
        <h2 class="mv-title">迷魂殿录供</h2>
        <p class="mv-subtitle">亡魂过鬼门关后入迷魂殿，录其生前自陈与死因情状，具供在案方可解赴审判。</p>
      </div>
      <div class="lr-banner__stats">
        <div class="lr-stat">
          <span class="lr-stat__label">待录供</span>
          <strong class="lr-stat__value mv-gold">{{ stats.queue }}</strong>
        </div>
        <div class="lr-stat">
          <span class="lr-stat__label">已转待审</span>
          <strong class="lr-stat__value mv-teal">{{ recorded }}</strong>
        </div>
        <div class="lr-stat">
          <span class="lr-stat__label">重罪待录</span>
          <strong class="lr-stat__value" style="color: #e05b45">{{ stats.highSin }}</strong>
        </div>
      </div>
    </div>

    <div class="lr-body">
      <section class="mv-panel lr-left">
        <div class="lr-search">
          <el-input
            v-model="query.keyword"
            placeholder="姓名 / 亡魂编号"
            clearable
            size="small"
            @keyup.enter="load"
            @clear="load"
          />
          <el-select v-model="query.region" placeholder="鬼域" clearable size="small" class="lr-w100" @change="load">
            <el-option v-for="r in REGIONS" :key="r" :label="r" :value="r" />
          </el-select>
        </div>

        <div v-loading="loading" class="lr-list">
          <button
            v-for="s in queue"
            :key="s.id"
            class="lr-item"
            :class="{ 'is-active': activeId === s.id }"
            @click="pick(s.id)"
          >
            <div class="lr-item__head">
              <span class="lr-item__name">{{ s.name }}</span>
              <span class="lr-item__sin" :style="{ color: karmaStyle(s.karma_score || 0).color }">{{ s.sin_level }}</span>
            </div>
            <div class="lr-item__meta">{{ s.soul_no }} · {{ s.region }} · {{ s.death_type }}</div>
            <div class="lr-item__loc">{{ s.current_location || '位置未记' }}</div>
          </button>
          <div v-if="!loading && !queue.length" class="lr-empty">迷魂殿当前无待录之魂</div>
        </div>
      </section>

      <section v-loading="detailLoading" class="mv-panel lr-right">
        <template v-if="detail">
          <div class="lr-soul">
            <div class="lr-soul__head">
              <div>
                <div class="lr-soul__name">{{ detail.name }}</div>
                <div class="lr-soul__no">{{ detail.soul_no }} · {{ detail.gender }} · 卒年 {{ detail.age }}</div>
              </div>
              <div class="lr-soul__karma">
                <span class="lr-soul__karma-val" :style="{ color: karmaStyle(detail.karma_score || 0).color }">
                  {{ detail.karma_score }}
                </span>
                <span class="lr-soul__karma-label">业力 · {{ detail.sin_level }}</span>
              </div>
            </div>
            <dl class="lr-grid">
              <div><dt>籍贯</dt><dd>{{ detail.native_place || '—' }}</dd></div>
              <div><dt>鬼域</dt><dd>{{ detail.region }}</dd></div>
              <div><dt>死因类别</dt><dd>{{ detail.death_type }}</dd></div>
              <div><dt>死亡时间</dt><dd>{{ formatDateTime(detail.death_date) }}</dd></div>
              <div><dt>生死簿编号</dt><dd>{{ detail.life_book_no || '—' }}</dd></div>
              <div><dt>现处</dt><dd>{{ detail.current_location || '—' }}</dd></div>
            </dl>
            <div class="lr-doc">
              <span class="lr-doc__label">过境路引</span>
              <template v-if="routeDoc">
                <span class="lr-doc__no">{{ routeDoc.doc_no }}</span>
                <span class="lr-doc__status">{{ routeDoc.status }}</span>
                <span class="lr-doc__time">{{ formatDateTime(routeDoc.verified_at || routeDoc.issued_at) }}</span>
              </template>
              <span v-else class="lr-doc__none">未查到路引记录</span>
            </div>
          </div>

          <div class="lr-confess">
            <div class="lr-confess__title">供词录入</div>
            <el-input
              v-model="confession"
              type="textarea"
              :rows="7"
              size="small"
              maxlength="800"
              show-word-limit
              placeholder="录亡魂自陈：生前所为、临终情状、有无冤抑、是否认罪……"
            />
            <div class="lr-hint">录供后亡魂状态将流转为「待审」，供词一并写入阴律日志，不可撤回。</div>
            <div class="lr-ops">
              <el-button
                v-if="canTransfer"
                class="mv-seal-btn"
                size="small"
                :loading="acting"
                @click="submit"
              >录供具结</el-button>
              <span v-else class="lr-dim">当前账号无亡魂流转权限，仅可查阅</span>
            </div>
          </div>
        </template>
        <div v-else-if="!detailLoading" class="lr-placeholder">
          <div class="lr-placeholder__title">迷魂殿</div>
          <div class="lr-placeholder__text">左侧择一亡魂，录其供词</div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.lr-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.lr-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.lr-banner__main {
  max-width: 540px;
}
.lr-banner__main .mv-subtitle {
  margin-top: 8px;
  line-height: 1.75;
}
.lr-banner__stats {
  display: flex;
  gap: 10px;
}
.lr-stat {
  min-width: 92px;
  padding: 8px 12px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.lr-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.lr-stat__value {
  font-family: var(--mv-font-title);
  font-size: 22px;
  line-height: 1.1;
}
.lr-body {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.lr-left {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
}
.lr-search {
  display: flex;
  gap: 8px;
}
.lr-w100 {
  width: 100px;
}
.lr-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 640px;
  overflow: auto;
}
.lr-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  background: rgba(232, 227, 214, 0.02);
  border: 1px solid rgba(232, 227, 214, 0.1);
  transition: all 0.16s;
}
.lr-item:hover {
  border-color: rgba(201, 162, 39, 0.4);
}
.lr-item.is-active {
  border-color: rgba(201, 162, 39, 0.8);
  background: rgba(201, 162, 39, 0.07);
}
.lr-item__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.lr-item__name {
  font-family: var(--mv-font-title);
  font-size: 15px;
  color: var(--mv-paper);
}
.lr-item__sin {
  font-size: 12px;
}
.lr-item__meta {
  font-size: 11px;
  color: var(--mv-muted);
}
.lr-item__loc {
  font-size: 11px;
  color: rgba(232, 227, 214, 0.45);
}
.lr-empty {
  padding: 30px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
.lr-right {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 20px;
  min-height: 480px;
}
.lr-soul {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 18px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.02);
}
.lr-soul__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.lr-soul__name {
  font-family: var(--mv-font-title);
  font-size: 22px;
  color: var(--mv-gold);
  letter-spacing: 0.1em;
}
.lr-soul__no {
  margin-top: 4px;
  font-size: 12px;
  color: var(--mv-muted);
}
.lr-soul__karma {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.lr-soul__karma-val {
  font-family: var(--mv-font-title);
  font-size: 26px;
  line-height: 1;
}
.lr-soul__karma-label {
  font-size: 11px;
  color: var(--mv-muted);
}
.lr-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}
.lr-grid div {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-bottom: 7px;
  border-bottom: 1px dashed rgba(232, 227, 214, 0.1);
}
.lr-grid dt {
  font-size: 11px;
  color: var(--mv-muted);
}
.lr-grid dd {
  margin: 0;
  font-size: 13px;
  color: var(--mv-paper);
}
.lr-doc {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  font-size: 12px;
  border: 1px dashed rgba(201, 162, 39, 0.32);
  background: rgba(201, 162, 39, 0.05);
}
.lr-doc__label {
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.lr-doc__no {
  color: var(--mv-gold);
  letter-spacing: 0.08em;
}
.lr-doc__status {
  color: var(--mv-phosphor, #4ce0c3);
}
.lr-doc__time {
  margin-left: auto;
  color: var(--mv-muted);
}
.lr-doc__none {
  color: var(--mv-muted);
}
.lr-confess {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.lr-confess__title {
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--mv-muted);
}
.lr-hint {
  font-size: 12px;
  line-height: 1.7;
  color: var(--mv-muted);
}
.lr-ops {
  display: flex;
  align-items: center;
  gap: 10px;
}
.lr-dim {
  font-size: 12px;
  color: var(--mv-muted);
}
.lr-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.lr-placeholder__title {
  font-family: var(--mv-font-title);
  font-size: 40px;
  letter-spacing: 0.3em;
  color: rgba(201, 162, 39, 0.26);
}
.lr-placeholder__text {
  font-size: 12px;
  color: var(--mv-muted);
}
@media (max-width: 1200px) {
  .lr-body {
    grid-template-columns: minmax(0, 1fr);
  }
  .lr-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
