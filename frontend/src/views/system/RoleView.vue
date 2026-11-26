<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { assignRolePermissions, createRole, fetchPermissionGroups, fetchRoles, updateRole } from '@/api'
import type { PermissionItem, RoleItem } from '@/api/types'
import { usePerms } from '@/composables/usePerms'

const { hasPerm } = usePerms()
const canCreate = computed(() => hasPerm('role:create'))
const canUpdate = computed(() => hasPerm('role:update'))
const canAssign = computed(() => hasPerm('role:assign'))

const SCOPES = [
  { value: 'ALL', label: '全域' },
  { value: 'REGION', label: '本域' },
  { value: 'SELF', label: '自辖' },
]
const TYPE_ORDER = ['菜单', '按钮', '接口']

const loading = ref(false)
const roles = ref<RoleItem[]>([])
const permsFlat = ref<PermissionItem[]>([])
const permsByModule = ref<{ module: string; items: PermissionItem[] }[]>([])
const activeId = ref<number | null>(null)

const active = computed(() => roles.value.find((r) => r.id === activeId.value) || null)

const checkedIds = ref<number[]>([])
const draftSet = ref<Set<number>>(new Set())
const saving = ref(false)

const isSuper = computed(() => active.value?.code === 'SUPER_ADMIN')

async function loadPerms() {
  try {
    const res = await fetchPermissionGroups()
    permsFlat.value = res.flat || []
    permsByModule.value = res.modules || []
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '权限点读取失败')
  }
}

async function load() {
  loading.value = true
  try {
    roles.value = await fetchRoles()
    if (!roles.value.some((r) => r.id === activeId.value)) {
      activeId.value = roles.value.length ? roles.value[0].id : null
    }
    syncChecked()
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '角色读取失败')
  } finally {
    loading.value = false
  }
}

function syncChecked() {
  const codes = new Set(active.value?.permissions || [])
  const ids = permsFlat.value.filter((p) => codes.has(p.code)).map((p) => p.id)
  checkedIds.value = ids
  draftSet.value = new Set(ids)
}

function pickRole(id: number) {
  activeId.value = id
  syncChecked()
}

function isChecked(id: number) {
  return draftSet.value.has(id)
}

function togglePerm(id: number) {
  if (isSuper.value || !canAssign.value) return
  const next = new Set(draftSet.value)
  next.has(id) ? next.delete(id) : next.add(id)
  draftSet.value = next
}

function moduleChecked(items: PermissionItem[]) {
  return items.length > 0 && items.every((p) => draftSet.value.has(p.id))
}

function toggleModule(items: PermissionItem[]) {
  if (isSuper.value || !canAssign.value) return
  const all = moduleChecked(items)
  const next = new Set(draftSet.value)
  items.forEach((p) => (all ? next.delete(p.id) : next.add(p.id)))
  draftSet.value = next
}

const dirty = computed(() => {
  const a = checkedIds.value
  const b = draftSet.value
  if (a.length !== b.size) return true
  return a.some((id) => !b.has(id))
})

async function submitPerms() {
  if (!active.value) return
  saving.value = true
  try {
    const res = await assignRolePermissions(active.value.id, Array.from(draftSet.value))
    ElMessage.success(`「${active.value.name}」授权已更新，共 ${res.permission_count} 个权限点`)
    await load()
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '授权失败')
  } finally {
    saving.value = false
  }
}

function resetDraft() {
  draftSet.value = new Set(checkedIds.value)
}

/* ---------------- 新增 / 编辑角色 ---------------- */
const dialog = ref(false)
const editMode = ref(false)
const form = reactive({ code: '', name: '', description: '', data_scope: 'REGION', sort: 0, status: '在职' })

function openCreate() {
  editMode.value = false
  Object.assign(form, { code: '', name: '', description: '', data_scope: 'REGION', sort: 0, status: '在职' })
  dialog.value = true
}

function openEdit() {
  if (!active.value) return
  editMode.value = true
  Object.assign(form, {
    code: active.value.code,
    name: active.value.name,
    description: active.value.description || '',
    data_scope: active.value.data_scope || 'REGION',
    sort: active.value.sort ?? 0,
    status: active.value.status || '在职',
  })
  dialog.value = true
}

async function submitRole() {
  if (!form.name.trim()) return ElMessage.warning('请填写角色名')
  saving.value = true
  try {
    if (editMode.value && active.value) {
      await updateRole(active.value.id, {
        name: form.name,
        description: form.description,
        data_scope: form.data_scope,
        sort: form.sort,
        status: form.status,
      })
      ElMessage.success('角色已更新')
    } else {
      if (form.code.trim().length < 2) return ElMessage.warning('角色编码不得少于 2 位')
      await createRole({
        code: form.code.trim().toUpperCase(),
        name: form.name,
        description: form.description,
        data_scope: form.data_scope,
        sort: form.sort,
      })
      ElMessage.success('角色已创建')
    }
    dialog.value = false
    await load()
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function confirmSuper() {
  await ElMessageBox.alert('酆都大帝（SUPER_ADMIN）角色内建拥有全部权限，不可编辑授权。', '内建角色', {
    confirmButtonText: '知道了',
  })
}

const moduleGroups = computed(() =>
  permsByModule.value.map((g) => ({
    module: g.module,
    items: [...g.items].sort(
      (a, b) => (TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type)) || a.code.localeCompare(b.code),
    ),
    count: g.items.length,
    granted: g.items.filter((p) => draftSet.value.has(p.id)).length,
  })),
)

const scopeLabel = (v: string) => SCOPES.find((s) => s.value === v)?.label || v || '—'

onMounted(async () => {
  await loadPerms()
  await load()
})
</script>

<template>
  <div class="rl-page">
    <div class="mv-panel rl-banner">
      <div>
        <h2 class="mv-title">角色权限</h2>
        <p class="mv-subtitle">角色者，权柄之集合。授受之间以覆盖为准，保存即生效，一并记入阴律日志。</p>
      </div>
      <div class="rl-banner__ops">
        <el-button v-if="canCreate" class="mv-seal-btn" size="small" @click="openCreate">新增角色</el-button>
      </div>
    </div>

    <div class="rl-body" v-loading="loading">
      <section class="mv-panel rl-left">
        <div class="mv-panel__head">
          <span class="mv-panel__title">角色名录</span>
          <span class="rl-count">{{ roles.length }}</span>
        </div>
        <div class="rl-roles">
          <button
            v-for="r in roles"
            :key="r.id"
            class="rl-role"
            :class="{ 'is-active': activeId === r.id }"
            @click="pickRole(r.id)"
          >
            <div class="rl-role__head">
              <span class="rl-role__name">{{ r.name }}</span>
              <span v-if="r.is_builtin" class="rl-role__builtin">内建</span>
            </div>
            <div class="rl-role__code">{{ r.code }}</div>
            <div class="rl-role__meta">{{ scopeLabel(r.data_scope) }} · {{ r.permission_count }} 权限</div>
          </button>
          <div v-if="!roles.length" class="rl-empty">尚未立角色</div>
        </div>
      </section>

      <section class="mv-panel rl-right">
        <template v-if="active">
          <div class="rl-head">
            <div>
              <div class="rl-head__name">
                {{ active.name }}
                <span class="rl-head__code">{{ active.code }}</span>
              </div>
              <div class="rl-head__desc">{{ active.description || '未著释义' }}</div>
            </div>
            <div class="rl-head__ops">
              <el-button v-if="canUpdate" class="mv-ghost-btn" size="small" @click="openEdit">编辑角色</el-button>
            </div>
          </div>

          <div class="rl-meta">
            <span>数据域：{{ scopeLabel(active.data_scope) }}</span>
            <span>状态：{{ active.status }}</span>
            <span>排序：{{ active.sort }}</span>
            <span>已授：{{ checkedIds.length }} / {{ permsFlat.length }}</span>
            <span v-if="dirty" class="rl-dirty">有未存之改动（拟 {{ draftSet.size }}）</span>
          </div>

          <div v-if="isSuper" class="rl-super">
            <span>内建角色 · 全域全权，不可编辑授权</span>
            <el-button link class="rl-link" @click="confirmSuper">何以如此</el-button>
          </div>

          <div class="rl-perms">
            <div v-for="g in moduleGroups" :key="g.module" class="rl-module">
              <div class="rl-module__head">
                <label class="rl-module__label" @click="toggleModule(g.items)">
                  <i class="rl-check" :class="{ 'is-on': moduleChecked(g.items) }"></i>
                  <span class="rl-module__name">{{ g.module }}</span>
                </label>
                <span class="rl-module__count">{{ g.granted }} / {{ g.count }}</span>
              </div>
              <div class="rl-module__items">
                <button
                  v-for="p in g.items"
                  :key="p.id"
                  class="rl-perm"
                  :class="{ 'is-on': isChecked(p.id), 'is-locked': isSuper || !canAssign }"
                  :title="`${p.name} · ${p.code} · ${p.type}`"
                  @click="togglePerm(p.id)"
                >
                  {{ p.name }}
                </button>
              </div>
            </div>
            <div v-if="!moduleGroups.length" class="rl-empty">尚无权限点</div>
          </div>

          <div v-if="canAssign && !isSuper" class="rl-actions">
            <span class="rl-hint">保存将以当前勾选覆盖该角色全部授权。</span>
            <div class="rl-actions__btns">
              <el-button class="mv-ghost-btn" size="small" :disabled="!dirty" @click="resetDraft">还原</el-button>
              <el-button class="mv-seal-btn" size="small" :loading="saving" :disabled="!dirty" @click="submitPerms">
                存授权（{{ draftSet.size }}）
              </el-button>
            </div>
          </div>
        </template>
        <div v-else class="rl-placeholder">左侧择一角色</div>
      </section>
    </div>

    <el-dialog v-model="dialog" :title="editMode ? '编辑角色' : '新增角色'" width="460px">
      <el-form label-width="88px" size="small">
        <el-form-item label="角色编码" required>
          <el-input v-model="form.code" :disabled="editMode" placeholder="大写英文，如 YANLUO_JUDGE" />
        </el-form-item>
        <el-form-item label="角色名" required>
          <el-input v-model="form.name" placeholder="如：五殿阎罗" />
        </el-form-item>
        <el-form-item label="数据域">
          <el-select v-model="form.data_scope" class="rl-w100">
            <el-option v-for="s in SCOPES" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editMode" label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="在职">在职</el-radio>
            <el-radio value="停职">停职</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item label="释义">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="此角色所司何事" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="rl-dialog-foot">
          <el-button class="mv-ghost-btn" size="small" @click="dialog = false">取消</el-button>
          <el-button class="mv-seal-btn" size="small" :loading="saving" @click="submitRole">存案</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.rl-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rl-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.rl-banner .mv-subtitle {
  margin-top: 8px;
}
.rl-body {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.rl-left {
  padding-bottom: 8px;
}
.rl-count {
  font-size: 12px;
  color: var(--mv-muted);
}
.rl-roles {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  max-height: 660px;
  overflow: auto;
}
.rl-role {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  text-align: left;
  background: rgba(232, 227, 214, 0.02);
  border: 1px solid rgba(232, 227, 214, 0.1);
  cursor: pointer;
  transition: all 0.16s;
}
.rl-role:hover {
  border-color: rgba(201, 162, 39, 0.4);
}
.rl-role.is-active {
  border-color: rgba(201, 162, 39, 0.8);
  background: rgba(201, 162, 39, 0.07);
}
.rl-role__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.rl-role__name {
  font-family: var(--mv-font-title);
  font-size: 15px;
  color: var(--mv-paper);
}
.rl-role__builtin {
  font-size: 10px;
  padding: 0 5px;
  color: var(--mv-gold);
  border: 1px solid rgba(201, 162, 39, 0.45);
}
.rl-role__code {
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--mv-muted);
}
.rl-role__meta {
  font-size: 11px;
  color: rgba(232, 227, 214, 0.42);
}
.rl-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px 20px;
  min-height: 520px;
}
.rl-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.rl-head__name {
  font-family: var(--mv-font-title);
  font-size: 20px;
  color: var(--mv-gold);
  letter-spacing: 0.08em;
}
.rl-head__code {
  margin-left: 10px;
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--mv-muted);
}
.rl-head__desc {
  margin-top: 5px;
  font-size: 12px;
  color: var(--mv-muted);
}
.rl-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 9px 12px;
  font-size: 12px;
  color: var(--mv-muted);
  border: 1px dashed rgba(232, 227, 214, 0.14);
}
.rl-dirty {
  color: var(--mv-gold);
}
.rl-super {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 12px;
  font-size: 12px;
  color: var(--mv-gold);
  border: 1px solid rgba(201, 162, 39, 0.4);
  background: rgba(201, 162, 39, 0.06);
}
.rl-link {
  color: var(--mv-gold);
  font-size: 12px;
  padding: 0;
}
.rl-perms {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rl-module {
  border: 1px solid rgba(232, 227, 214, 0.1);
  background: rgba(232, 227, 214, 0.015);
}
.rl-module__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(232, 227, 214, 0.08);
}
.rl-module__label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.rl-check {
  width: 12px;
  height: 12px;
  border: 1px solid rgba(232, 227, 214, 0.3);
  display: inline-block;
}
.rl-check.is-on {
  background: var(--mv-gold);
  border-color: var(--mv-gold);
}
.rl-module__name {
  font-family: var(--mv-font-title);
  font-size: 14px;
  color: var(--mv-paper);
  letter-spacing: 0.06em;
}
.rl-module__count {
  font-size: 11px;
  color: var(--mv-muted);
}
.rl-module__items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 12px;
}
.rl-perm {
  padding: 3px 10px;
  font-size: 12px;
  color: var(--mv-muted);
  background: transparent;
  border: 1px solid rgba(232, 227, 214, 0.14);
  cursor: pointer;
  transition: all 0.14s;
}
.rl-perm:hover {
  border-color: rgba(201, 162, 39, 0.5);
  color: var(--mv-paper);
}
.rl-perm.is-on {
  color: var(--mv-gold);
  border-color: rgba(201, 162, 39, 0.7);
  background: rgba(201, 162, 39, 0.1);
}
.rl-perm.is-locked {
  cursor: not-allowed;
  opacity: 0.75;
}
.rl-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-top: 4px;
}
.rl-hint {
  font-size: 12px;
  color: var(--mv-muted);
}
.rl-actions__btns {
  display: flex;
  gap: 10px;
}
.rl-empty,
.rl-placeholder {
  padding: 30px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
.rl-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rl-w100 {
  width: 100%;
}
.rl-dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
@media (max-width: 1200px) {
  .rl-body {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
