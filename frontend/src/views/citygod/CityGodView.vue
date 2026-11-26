<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createCityGod, fetchCityGods, updateCityGod } from '@/api'
import type { CityGodNode } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime } from '@/utils/status'

const { hasPerm } = usePerms()

const REGIONS = ['东方', '南方', '西方', '北方', '中央']
const LEVELS = ['都城隍', '府城隍', '州城隍', '县城隍']
const STATUS = ['在职', '停用', '冻结']

const canCreate = computed(() => hasPerm('citygod:create'))
const canUpdate = computed(() => hasPerm('citygod:update'))

const loading = ref(false)
const rows = ref<CityGodNode[]>([])
const query = reactive({ keyword: '', region: '', level: '', status: '' })

async function load() {
  loading.value = true
  try {
    const res = await fetchCityGods({
      keyword: query.keyword || undefined,
      region: query.region || undefined,
      level: query.level || undefined,
      status: query.status || undefined,
    })
    rows.value = Array.isArray(res) ? res : []
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '城隍网点读取失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.keyword = ''
  query.region = ''
  query.level = ''
  query.status = ''
  load()
}

/* ---------------- 概览 ---------------- */
const overall = computed(() => {
  const list = rows.value
  const capacity = list.reduce((acc, r) => acc + (r.soul_capacity || 0), 0)
  const souls = list.reduce((acc, r) => acc + (r.soul_count || 0), 0)
  return {
    total: list.length,
    active: list.filter((r) => r.status === '在职').length,
    inactive: list.filter((r) => r.status !== '在职').length,
    capacity,
    souls,
    used: capacity ? Math.round((souls / capacity) * 100) : 0,
    full: list.filter((r) => (r.soul_count || 0) >= (r.soul_capacity || 0)).length,
  }
})

const levelUnits = computed(() =>
  LEVELS.map((level) => {
    const list = rows.value.filter((r) => r.level === level)
    const souls = list.reduce((acc, r) => acc + (r.soul_count || 0), 0)
    const capacity = list.reduce((acc, r) => acc + (r.soul_capacity || 0), 0)
    return {
      level,
      count: list.length,
      souls,
      capacity,
      percent: capacity ? Math.min(100, Math.round((souls / capacity) * 100)) : 0,
    }
  }),
)

function usageRatio(row: CityGodNode) {
  const cap = row.soul_capacity || 0
  if (!cap) return 0
  return Math.min(100, Math.round(((row.soul_count || 0) / cap) * 100))
}

function usageColor(percent: number) {
  if (percent >= 100) return '#d4553f'
  if (percent >= 85) return '#cf7a48'
  if (percent >= 60) return '#c9a227'
  return '#4ce0c3'
}

function statusStyle(status: string) {
  if (status === '在职') return { color: '#4ce0c3', border: 'rgba(76,224,195,0.4)', bg: 'rgba(76,224,195,0.1)' }
  if (status === '冻结') return { color: '#e05b45', border: 'rgba(224,91,69,0.42)', bg: 'rgba(179,38,30,0.14)' }
  return { color: '#8fa3b8', border: 'rgba(143,163,184,0.4)', bg: 'rgba(143,163,184,0.12)' }
}

function pickLevel(level: string) {
  query.level = query.level === level ? '' : level
  load()
}

/* ---------------- 上级网点 ---------------- */
const parentOptions = computed(() =>
  rows.value.filter((r) => r.level !== '县城隍').map((r) => ({ id: r.id, label: `${r.name}（${r.level}）` })),
)

/* ---------------- 新增 / 编辑 ---------------- */
const dialog = ref(false)
const saving = ref(false)
const editing = ref<CityGodNode | null>(null)
const form = reactive({
  code: '',
  name: '',
  region: '中央',
  level: '县城隍',
  parent_id: undefined as number | undefined,
  city_god_name: '',
  address: '',
  contact: '',
  soul_capacity: 1000,
  status: '在职',
  remark: '',
})

function openCreate() {
  editing.value = null
  Object.assign(form, {
    code: '',
    name: '',
    region: query.region || '中央',
    level: query.level || '县城隍',
    parent_id: undefined,
    city_god_name: '',
    address: '',
    contact: '',
    soul_capacity: 1000,
    status: '在职',
    remark: '',
  })
  dialog.value = true
}

function openEdit(row: CityGodNode) {
  editing.value = row
  Object.assign(form, {
    code: row.code,
    name: row.name,
    region: row.region || '中央',
    level: row.level || '县城隍',
    parent_id: row.parent_id ?? undefined,
    city_god_name: row.city_god_name || '',
    address: row.address || '',
    contact: row.contact || '',
    soul_capacity: row.soul_capacity || 1000,
    status: row.status || '在职',
    remark: row.remark || '',
  })
  dialog.value = true
}

async function submit() {
  if (!form.code.trim()) {
    ElMessage.warning('请填写网点编码')
    return
  }
  if (!form.name.trim()) {
    ElMessage.warning('请填写网点名称')
    return
  }
  if (!form.city_god_name.trim()) {
    ElMessage.warning('请填写城隍神姓名')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateCityGod(editing.value.id, {
        name: form.name,
        region: form.region,
        level: form.level,
        city_god_name: form.city_god_name,
        address: form.address,
        contact: form.contact,
        soul_capacity: form.soul_capacity,
        status: form.status,
        remark: form.remark,
      })
      ElMessage.success('网点已保存')
    } else {
      await createCityGod({
        code: form.code,
        name: form.name,
        region: form.region,
        level: form.level,
        parent_id: form.parent_id ?? null,
        city_god_name: form.city_god_name,
        address: form.address,
        contact: form.contact,
        soul_capacity: form.soul_capacity,
        status: form.status,
        remark: form.remark,
      })
      ElMessage.success('网点已设立')
    }
    dialog.value = false
    await load()
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

/* ---------------- 详情 ---------------- */
const detail = ref<CityGodNode | null>(null)
const detailVisible = ref(false)

function openDetail(row: CityGodNode) {
  detail.value = row
  detailVisible.value = true
}

onMounted(load)
</script>

<template>
  <div class="cg-page">
    <div class="mv-panel cg-banner">
      <div class="cg-banner__main">
        <h2 class="mv-title">城隍网点</h2>
        <p class="mv-subtitle">
          城隍司辖下网点，司阳间备案、签押路引、上报善恶。网点点位与容量决定亡魂押解走向。
        </p>
      </div>
      <div class="cg-banner__stats">
        <div class="cg-stat">
          <span class="cg-stat__label">网点总数</span>
          <strong class="cg-stat__value">{{ overall.total }}</strong>
        </div>
        <div class="cg-stat">
          <span class="cg-stat__label">在职</span>
          <strong class="cg-stat__value mv-teal">{{ overall.active }}</strong>
        </div>
        <div class="cg-stat">
          <span class="cg-stat__label">停用 / 冻结</span>
          <strong class="cg-stat__value mv-muted">{{ overall.inactive }}</strong>
        </div>
        <div class="cg-stat">
          <span class="cg-stat__label">在册亡魂</span>
          <strong class="cg-stat__value mv-gold">{{ overall.souls }}</strong>
        </div>
        <div class="cg-stat">
          <span class="cg-stat__label">总容量占用</span>
          <strong class="cg-stat__value" :style="{ color: usageColor(overall.used) }">{{ overall.used }}%</strong>
        </div>
        <div class="cg-stat">
          <span class="cg-stat__label">满载网点</span>
          <strong class="cg-stat__value" :style="{ color: overall.full ? '#e05b45' : 'var(--mv-paper)' }">
            {{ overall.full }}
          </strong>
        </div>
      </div>
    </div>

    <div class="cg-levels">
      <button
        v-for="unit in levelUnits"
        :key="unit.level"
        class="mv-panel cg-level"
        :class="{ 'is-active': query.level === unit.level }"
        @click="pickLevel(unit.level)"
      >
        <div class="cg-level__head">
          <span class="cg-level__name">{{ unit.level }}</span>
          <span class="cg-level__count">{{ unit.count }} 处</span>
        </div>
        <div class="cg-level__bar">
          <i :style="{ width: `${unit.percent}%`, background: usageColor(unit.percent) }"></i>
        </div>
        <div class="cg-level__foot">
          <span>在册 {{ unit.souls }}</span>
          <span>容量 {{ unit.capacity }}</span>
        </div>
      </button>
    </div>

    <section class="mv-panel cg-list">
      <div class="mv-panel__head">
        <span class="mv-panel__title">网点点位</span>
        <div class="cg-filters">
          <el-input
            v-model="query.keyword"
            placeholder="网点编码 / 名称"
            clearable
            size="small"
            class="cg-w200"
            @keyup.enter="load"
            @clear="load"
          />
          <el-select v-model="query.region" placeholder="全部鬼域" clearable size="small" class="cg-w120" @change="load">
            <el-option v-for="r in REGIONS" :key="r" :label="r" :value="r" />
          </el-select>
          <el-select v-model="query.level" placeholder="全部级别" clearable size="small" class="cg-w120" @change="load">
            <el-option v-for="l in LEVELS" :key="l" :label="l" :value="l" />
          </el-select>
          <el-select v-model="query.status" placeholder="全部状态" clearable size="small" class="cg-w110" @change="load">
            <el-option v-for="s in STATUS" :key="s" :label="s" :value="s" />
          </el-select>
          <el-button class="mv-ghost-btn" size="small" @click="load">查阅</el-button>
          <el-button class="mv-ghost-btn" size="small" @click="resetQuery">重置</el-button>
          <el-button v-if="canCreate" class="mv-seal-btn" size="small" @click="openCreate">设立网点</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" size="small" class="cg-table">
        <el-table-column prop="code" label="编码" width="120" />
        <el-table-column label="网点名称" min-width="180">
          <template #default="{ row }">
            <button class="cg-name" @click="openDetail(row)">{{ row.name }}</button>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="级别" width="100">
          <template #default="{ row }">
            <span class="cg-level-tag">{{ row.level }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="region" label="鬼域" width="88" />
        <el-table-column prop="city_god_name" label="城隍神" width="110" />
        <el-table-column prop="address" label="辖境" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.address || '—' }}</template>
        </el-table-column>
        <el-table-column label="在册 / 容量" width="176">
          <template #default="{ row }">
            <div class="cg-usage">
              <div class="cg-usage__bar">
                <i
                  :style="{ width: `${usageRatio(row)}%`, background: usageColor(usageRatio(row)) }"
                ></i>
              </div>
              <span class="cg-usage__text">
                {{ row.soul_count ?? 0 }} / {{ row.soul_capacity ?? 0 }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="86">
          <template #default="{ row }">
            <span
              class="cg-tag"
              :style="{
                color: statusStyle(row.status).color,
                borderColor: statusStyle(row.status).border,
                background: statusStyle(row.status).bg,
              }"
            >{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="contact" label="联络" width="130">
          <template #default="{ row }">{{ row.contact || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="112" fixed="right">
          <template #default="{ row }">
            <div class="cg-actions">
              <el-button link class="cg-link" @click="openDetail(row)">详情</el-button>
              <el-button v-if="canUpdate" link class="cg-link cg-link--gold" @click="openEdit(row)">编辑</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="cg-empty">此条件下无网点，幽冥辖境未及此处</div>
        </template>
      </el-table>
    </section>

    <!-- 网点详情 -->
    <el-drawer v-model="detailVisible" title="网点详情" size="420px">
      <div v-if="detail" class="cg-detail">
        <div class="cg-detail__title">{{ detail.name }}</div>
        <div class="cg-detail__sub">{{ detail.code }} · {{ detail.level }} · {{ detail.region }}</div>
        <div class="cg-detail__usage">
          <div class="cg-usage__bar">
            <i :style="{ width: `${usageRatio(detail)}%`, background: usageColor(usageRatio(detail)) }"></i>
          </div>
          <span class="cg-usage__text">
            在册 {{ detail.soul_count ?? 0 }} / 容量 {{ detail.soul_capacity ?? 0 }}（{{ usageRatio(detail) }}%）
          </span>
        </div>
        <dl class="cg-detail__grid">
          <div><dt>城隍神</dt><dd>{{ detail.city_god_name }}</dd></div>
          <div><dt>状态</dt><dd>{{ detail.status }}</dd></div>
          <div><dt>辖境</dt><dd>{{ detail.address || '—' }}</dd></div>
          <div><dt>联络</dt><dd>{{ detail.contact || '—' }}</dd></div>
          <div><dt>上级网点</dt><dd>{{ rows.find((r) => r.id === detail?.parent_id)?.name || '无' }}</dd></div>
          <div><dt>更新时间</dt><dd>{{ formatDateTime(detail.updated_at) }}</dd></div>
        </dl>
        <div class="cg-detail__remark">{{ detail.remark || '无备注' }}</div>
        <el-button v-if="canUpdate" class="mv-seal-btn cg-detail__btn" size="small" @click="detailVisible = false; openEdit(detail)">
          编辑网点
        </el-button>
      </div>
    </el-drawer>

    <!-- 新增 / 编辑 -->
    <el-dialog v-model="dialog" :title="editing ? '编辑网点' : '设立网点'" width="560px">
      <div class="cg-form">
        <div class="cg-form__row">
          <label>网点编码</label>
          <el-input v-model="form.code" size="small" :disabled="!!editing" placeholder="如 CG-BJ-001" />
        </div>
        <div class="cg-form__row">
          <label>网点名称</label>
          <el-input v-model="form.name" size="small" placeholder="如 京城城隍庙" />
        </div>
        <div class="cg-form__row">
          <label>城隍神</label>
          <el-input v-model="form.city_god_name" size="small" placeholder="坐镇城隍姓名" />
        </div>
        <div class="cg-form__row">
          <label>级别</label>
          <el-select v-model="form.level" size="small" class="cg-full">
            <el-option v-for="l in LEVELS" :key="l" :label="l" :value="l" />
          </el-select>
        </div>
        <div class="cg-form__row">
          <label>鬼域</label>
          <el-select v-model="form.region" size="small" class="cg-full">
            <el-option v-for="r in REGIONS" :key="r" :label="r" :value="r" />
          </el-select>
        </div>
        <div class="cg-form__row">
          <label>上级网点</label>
          <el-select
            v-if="!editing"
            v-model="form.parent_id"
            size="small"
            class="cg-full"
            clearable
            placeholder="可不设（直属城隍司）"
          >
            <el-option v-for="p in parentOptions" :key="p.id" :label="p.label" :value="p.id" />
          </el-select>
          <div v-else class="cg-form__static">上级关系设立后不可改</div>
        </div>
        <div class="cg-form__row">
          <label>亡魂容量</label>
          <el-input-number v-model="form.soul_capacity" :min="1" :max="1000000" :step="100" size="small" class="cg-full" />
        </div>
        <div class="cg-form__row">
          <label>状态</label>
          <el-select v-model="form.status" size="small" class="cg-full">
            <el-option v-for="s in STATUS" :key="s" :label="s" :value="s" />
          </el-select>
        </div>
        <div class="cg-form__row">
          <label>辖境地址</label>
          <el-input v-model="form.address" size="small" placeholder="阳间对应辖境" />
        </div>
        <div class="cg-form__row">
          <label>联络方式</label>
          <el-input v-model="form.contact" size="small" placeholder="香火 / 传讯方式" />
        </div>
        <div class="cg-form__row">
          <label>备注</label>
          <el-input v-model="form.remark" type="textarea" :rows="2" size="small" maxlength="200" show-word-limit />
        </div>
        <div class="cg-note">
          变更将写入阴律日志。停用网点不再受理备案与路引签押，已押解亡魂需另行指派。
        </div>
      </div>
      <template #footer>
        <el-button class="mv-ghost-btn" size="small" @click="dialog = false">取消</el-button>
        <el-button class="mv-seal-btn" size="small" :loading="saving" @click="submit">
          {{ editing ? '保存' : '设立' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.cg-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.cg-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.cg-banner__main {
  max-width: 560px;
}
.cg-banner__main .mv-subtitle {
  margin-top: 8px;
  line-height: 1.75;
}
.cg-banner__stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.cg-stat {
  min-width: 88px;
  padding: 8px 12px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cg-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.cg-stat__value {
  font-family: var(--mv-font-title);
  font-size: 22px;
  line-height: 1.1;
  color: var(--mv-paper);
}
.cg-levels {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.cg-level {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  text-align: left;
  cursor: pointer;
  transition: all 0.18s;
}
.cg-level:hover {
  border-color: rgba(201, 162, 39, 0.42);
}
.cg-level.is-active {
  border-color: rgba(201, 162, 39, 0.72);
  box-shadow: inset 0 -2px 0 rgba(179, 38, 30, 0.6);
}
.cg-level__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.cg-level__name {
  font-family: var(--mv-font-title);
  font-size: 16px;
  color: var(--mv-gold);
  letter-spacing: 0.1em;
}
.cg-level__count {
  font-size: 12px;
  color: var(--mv-muted);
}
.cg-level__bar,
.cg-usage__bar {
  position: relative;
  height: 6px;
  background: rgba(232, 227, 214, 0.08);
  overflow: hidden;
}
.cg-level__bar i,
.cg-usage__bar i {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  display: block;
  transition: width 0.3s;
}
.cg-level__foot {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--mv-muted);
}
.cg-list {
  padding-bottom: 6px;
}
.cg-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.cg-w200 {
  width: 200px;
}
.cg-w120 {
  width: 120px;
}
.cg-w110 {
  width: 110px;
}
.cg-name {
  background: transparent;
  border: none;
  padding: 0;
  color: var(--mv-paper);
  font-family: var(--mv-font-title);
  font-size: 14px;
  cursor: pointer;
}
.cg-name:hover {
  color: var(--mv-gold);
}
.cg-level-tag {
  font-size: 12px;
  padding: 1px 7px;
  border: 1px solid rgba(201, 162, 39, 0.36);
  color: var(--mv-gold);
  border-radius: 2px;
}
.cg-usage {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.cg-usage__text {
  font-size: 12px;
  color: var(--mv-muted);
}
.cg-tag {
  display: inline-block;
  padding: 1px 8px;
  font-size: 12px;
  border: 1px solid transparent;
  border-radius: 2px;
}
.cg-actions {
  display: flex;
  gap: 10px;
}
.cg-link {
  color: var(--mv-muted);
  padding: 0;
  font-size: 12px;
}
.cg-link--gold {
  color: var(--mv-gold);
}
.cg-empty {
  padding: 26px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
.cg-detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.cg-detail__title {
  font-family: var(--mv-font-title);
  font-size: 20px;
  color: var(--mv-gold);
}
.cg-detail__sub {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.cg-detail__usage {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.cg-detail__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}
.cg-detail__grid div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(232, 227, 214, 0.1);
}
.cg-detail__grid dt {
  font-size: 12px;
  color: var(--mv-muted);
}
.cg-detail__grid dd {
  margin: 0;
  font-size: 13px;
  color: var(--mv-paper);
}
.cg-detail__remark {
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--mv-muted);
  border: 1px solid rgba(232, 227, 214, 0.1);
  background: rgba(232, 227, 214, 0.03);
}
.cg-detail__btn {
  align-self: flex-start;
}
.cg-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.cg-form__row {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}
.cg-form__row label {
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--mv-muted);
}
.cg-form__static {
  font-size: 12px;
  color: var(--mv-muted);
}
.cg-full {
  width: 100%;
}
.cg-note {
  padding: 9px 12px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--mv-muted);
  border: 1px solid rgba(232, 227, 214, 0.1);
  background: rgba(232, 227, 214, 0.03);
}
@media (max-width: 1360px) {
  .cg-levels {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
