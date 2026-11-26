<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createMenu, fetchAdminMenus, updateMenu } from '@/api'
import type { MenuNode } from '@/api/types'
import { usePerms } from '@/composables/usePerms'

const { hasPerm } = usePerms()
const canCreate = computed(() => hasPerm('menu:create'))
const canUpdate = computed(() => hasPerm('menu:update'))

const TYPES = ['目录', '菜单', '按钮']
const loading = ref(false)
const tree = ref<MenuNode[]>([])
const keyword = ref('')
const typeFilter = ref('')
const expandAll = ref(true)

const tableKey = ref(0)

function filterTree(nodes: MenuNode[]): MenuNode[] {
  const kw = keyword.value.trim()
  const out: MenuNode[] = []
  nodes.forEach((n) => {
    const children = filterTree(n.children || [])
    const hit =
      (!kw || `${n.name}${n.code}${n.path}${n.permission_code}`.toLowerCase().includes(kw.toLowerCase())) &&
      (!typeFilter.value || n.type === typeFilter.value)
    if (hit || children.length) out.push({ ...n, children })
  })
  return out
}

const shown = computed(() => filterTree(tree.value))

const stats = computed(() => {
  const counter: Record<string, number> = {}
  const walk = (nodes: MenuNode[]) =>
    nodes.forEach((n) => {
      counter[n.type] = (counter[n.type] || 0) + 1
      walk(n.children || [])
    })
  walk(tree.value)
  const all = Object.values(counter).reduce((a, b) => a + b, 0)
  return { all, byType: counter }
})

async function load() {
  loading.value = true
  try {
    tree.value = await fetchAdminMenus()
    tableKey.value += 1
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '菜单树读取失败')
  } finally {
    loading.value = false
  }
}

/* ---------------- 新增 / 编辑 ---------------- */
const dialog = ref(false)
const editMode = ref(false)
const editId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  parent_id: null as number | null,
  code: '',
  name: '',
  path: '',
  component: '',
  icon: '',
  type: '菜单',
  permission_code: '',
  sort: 0,
  visible: true,
})

const flatOptions = computed(() => {
  const out: { id: number; label: string; depth: number }[] = []
  const walk = (nodes: MenuNode[], depth: number) =>
    nodes.forEach((n) => {
      out.push({ id: n.id, label: n.name, depth })
      walk(n.children || [], depth + 1)
    })
  walk(tree.value, 0)
  return out
})

function openCreate(parent?: MenuNode) {
  editMode.value = false
  editId.value = null
  Object.assign(form, {
    parent_id: parent ? parent.id : null,
    code: '',
    name: '',
    path: '',
    component: '',
    icon: '',
    type: parent ? '菜单' : '目录',
    permission_code: '',
    sort: 0,
    visible: true,
  })
  dialog.value = true
}

function openEdit(row: MenuNode) {
  editMode.value = true
  editId.value = row.id
  Object.assign(form, {
    parent_id: row.parent_id,
    code: row.code,
    name: row.name,
    path: row.path || '',
    component: row.component || '',
    icon: row.icon || '',
    type: row.type || '菜单',
    permission_code: row.permission_code || '',
    sort: row.sort ?? 0,
    visible: row.visible,
  })
  dialog.value = true
}

async function submit() {
  if (!form.name.trim()) return ElMessage.warning('请填写菜单名')
  if (!form.code.trim()) return ElMessage.warning('请填写菜单编码')
  saving.value = true
  try {
    if (editMode.value && editId.value) {
      await updateMenu(editId.value, {
        parent_id: form.parent_id,
        name: form.name,
        path: form.path,
        component: form.component,
        icon: form.icon,
        type: form.type,
        permission_code: form.permission_code,
        sort: form.sort,
        visible: form.visible,
      })
      ElMessage.success('菜单已更新')
    } else {
      await createMenu({
        parent_id: form.parent_id,
        code: form.code.trim(),
        name: form.name,
        path: form.path,
        component: form.component,
        icon: form.icon,
        type: form.type,
        permission_code: form.permission_code,
        sort: form.sort,
        visible: form.visible,
      })
      ElMessage.success('菜单已创建')
    }
    dialog.value = false
    await load()
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mn-page">
    <div class="mv-panel mn-banner">
      <div>
        <h2 class="mv-title">菜单配置</h2>
        <p class="mv-subtitle">前台所见之路径，皆由此出。菜单挂权限码，无码者隐、无权限者拒。</p>
      </div>
      <div class="mn-banner__stats">
        <div class="mn-stat">
          <span class="mn-stat__label">节点</span>
          <strong class="mn-stat__value">{{ stats.all }}</strong>
        </div>
        <div class="mn-stat">
          <span class="mn-stat__label">目录</span>
          <strong class="mn-stat__value">{{ stats.byType['目录'] || 0 }}</strong>
        </div>
        <div class="mn-stat">
          <span class="mn-stat__label">菜单</span>
          <strong class="mn-stat__value mv-gold">{{ stats.byType['菜单'] || 0 }}</strong>
        </div>
        <div class="mn-stat">
          <span class="mn-stat__label">按钮</span>
          <strong class="mn-stat__value">{{ stats.byType['按钮'] || 0 }}</strong>
        </div>
      </div>
    </div>

    <section class="mv-panel mn-list">
      <div class="mv-panel__head">
        <span class="mv-panel__title">菜单树</span>
        <div class="mn-filters">
          <el-input
            v-model="keyword"
            placeholder="名称 / 编码 / 路径 / 权限码"
            clearable
            size="small"
            class="mn-w240"
          />
          <el-select v-model="typeFilter" placeholder="全部类型" clearable size="small" class="mn-w110">
            <el-option v-for="t in TYPES" :key="t" :label="t" :value="t" />
          </el-select>
          <el-button class="mv-ghost-btn" size="small" @click="expandAll = !expandAll; tableKey += 1">
            {{ expandAll ? '收起全部' : '展开全部' }}
          </el-button>
          <el-button v-if="canCreate" class="mv-seal-btn" size="small" @click="openCreate()">新增菜单</el-button>
        </div>
      </div>

      <el-table
        :key="tableKey"
        v-loading="loading"
        :data="shown"
        size="small"
        row-key="id"
        :default-expand-all="expandAll"
        :tree-props="{ children: 'children' }"
      >
        <el-table-column prop="name" label="菜单名" min-width="200">
          <template #default="{ row }">
            <span class="mn-name" :class="{ 'is-dir': row.type === '目录' }">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="编码" width="150" />
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <span class="mn-type" :class="`t-${row.type}`">{{ row.type }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.path || '—' }}</template>
        </el-table-column>
        <el-table-column prop="component" label="组件" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mn-dim">{{ row.component || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="permission_code" label="权限码" width="150">
          <template #default="{ row }">
            <span :class="row.permission_code ? 'mn-perm' : 'mn-dim'">{{ row.permission_code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort" label="排序" width="66" />
        <el-table-column label="可见" width="70">
          <template #default="{ row }">
            <span :class="row.visible ? 'mn-on' : 'mn-off'">{{ row.visible ? '显' : '隐' }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="canCreate || canUpdate" label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <div class="mn-ops">
              <el-button v-if="canCreate" link class="mn-link" @click="openCreate(row)">增子</el-button>
              <el-button v-if="canUpdate" link class="mn-link" @click="openEdit(row)">编辑</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="mn-empty">此条件下无菜单</div>
        </template>
      </el-table>
    </section>

    <el-dialog v-model="dialog" :title="editMode ? '编辑菜单' : '新增菜单'" width="520px">
      <el-form label-width="92px" size="small">
        <el-form-item label="上级目录">
          <el-select v-model="form.parent_id" clearable placeholder="顶级" class="mn-w100">
            <el-option
              v-for="o in flatOptions"
              :key="o.id"
              :label="`${'　'.repeat(o.depth)}${o.label}`"
              :value="o.id"
              :disabled="editMode && o.id === editId"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="菜单名" required>
          <el-input v-model="form.name" placeholder="如：流转台账" />
        </el-form-item>
        <el-form-item label="编码" required>
          <el-input v-model="form.code" :disabled="editMode" placeholder="如：soul_flow" />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.type">
            <el-radio v-for="t in TYPES" :key="t" :value="t">{{ t }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="路径">
          <el-input v-model="form.path" placeholder="如：/soul/flow" />
        </el-form-item>
        <el-form-item label="组件">
          <el-input v-model="form.component" placeholder="如：flow/SoulFlowView" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="Element Plus 图标名" />
        </el-form-item>
        <el-form-item label="权限码">
          <el-input v-model="form.permission_code" placeholder="如：soul:view" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item label="可见">
          <el-switch v-model="form.visible" active-text="显" inactive-text="隐" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="mn-dialog-foot">
          <el-button class="mv-ghost-btn" size="small" @click="dialog = false">取消</el-button>
          <el-button class="mv-seal-btn" size="small" :loading="saving" @click="submit">存案</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.mn-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.mn-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.mn-banner .mv-subtitle {
  margin-top: 8px;
}
.mn-banner__stats {
  display: flex;
  gap: 10px;
}
.mn-stat {
  min-width: 76px;
  padding: 8px 12px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mn-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.mn-stat__value {
  font-family: var(--mv-font-title);
  font-size: 20px;
  line-height: 1.1;
}
.mn-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.mn-w240 {
  width: 240px;
}
.mn-w110 {
  width: 110px;
}
.mn-w100 {
  width: 100%;
}
.mn-name {
  font-family: var(--mv-font-title);
  font-size: 14px;
  color: var(--mv-paper);
}
.mn-name.is-dir {
  color: var(--mv-gold);
  letter-spacing: 0.08em;
}
.mn-type {
  font-size: 11px;
  padding: 1px 6px;
  border: 1px solid rgba(232, 227, 214, 0.18);
  color: var(--mv-muted);
}
.mn-type.t-目录 {
  color: var(--mv-gold);
  border-color: rgba(201, 162, 39, 0.4);
}
.mn-type.t-按钮 {
  color: var(--mv-phosphor, #4ce0c3);
  border-color: rgba(76, 224, 195, 0.35);
}
.mn-dim {
  font-size: 12px;
  color: var(--mv-muted);
}
.mn-perm {
  font-size: 12px;
  color: var(--mv-gold);
  letter-spacing: 0.04em;
}
.mn-on {
  color: var(--mv-phosphor, #4ce0c3);
  font-size: 12px;
}
.mn-off {
  color: rgba(232, 227, 214, 0.3);
  font-size: 12px;
}
.mn-ops {
  display: flex;
  gap: 8px;
}
.mn-link {
  color: var(--mv-gold);
  font-size: 12px;
  padding: 0;
}
.mn-empty {
  padding: 26px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
.mn-dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
