<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createOfficer,
  fetchOfficerPage,
  fetchRoles,
  resetOfficerPassword,
  setOfficerStatus,
  updateOfficer,
} from '@/api'
import type { OfficerRecord, RoleItem } from '@/api/types'
import { usePerms } from '@/composables/usePerms'
import { formatDateTime } from '@/utils/status'

const { hasPerm } = usePerms()
const canCreate = computed(() => hasPerm('officer:create'))
const canUpdate = computed(() => hasPerm('officer:update'))
const canReset = computed(() => hasPerm('officer:reset'))
const canStatus = computed(() => hasPerm('officer:status'))

const REGIONS = ['东方', '南方', '西方', '北方', '中央']
const SCOPES = [
  { value: 'ALL', label: '全域（酆都全境）' },
  { value: 'REGION', label: '本域（所属鬼域）' },
  { value: 'SELF', label: '自辖（本人经办）' },
]

const loading = ref(false)
const rows = ref<OfficerRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const roles = ref<RoleItem[]>([])
const query = reactive({ keyword: '', role_id: undefined as number | undefined, region: '', status: '' })

async function loadRoles() {
  try {
    roles.value = await fetchRoles()
  } catch {
    roles.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const res = await fetchOfficerPage({
      keyword: query.keyword || undefined,
      role_id: query.role_id,
      region: query.region || undefined,
      status: query.status || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    rows.value = res.items || []
    total.value = res.meta?.total ?? rows.value.length
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '鬼差名录读取失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.keyword = ''
  query.role_id = undefined
  query.region = ''
  query.status = ''
  page.value = 1
  load()
}

/* ---------------- 新增 / 编辑 ---------------- */
const drawer = ref(false)
const editId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  username: '',
  password: '',
  real_name: '',
  title: '',
  role_id: undefined as number | undefined,
  region: '中央',
  data_scope: 'REGION',
  phone: '',
  email: '',
  status: '在职',
  remark: '',
})

function openCreate() {
  editId.value = null
  Object.assign(form, {
    username: '',
    password: '',
    real_name: '',
    title: '',
    role_id: undefined,
    region: '中央',
    data_scope: 'REGION',
    phone: '',
    email: '',
    status: '在职',
    remark: '',
  })
  drawer.value = true
}

function openEdit(row: OfficerRecord) {
  editId.value = row.id
  Object.assign(form, {
    username: row.username,
    password: '',
    real_name: row.real_name,
    title: row.title || '',
    role_id: row.role_id,
    region: row.region || '中央',
    data_scope: row.data_scope || 'REGION',
    phone: row.phone || '',
    email: row.email || '',
    status: row.status || '在职',
    remark: row.remark || '',
  })
  drawer.value = true
}

async function submit() {
  if (!form.real_name.trim()) return ElMessage.warning('请填写鬼差本名')
  if (!form.role_id) return ElMessage.warning('请择角色')
  saving.value = true
  try {
    if (editId.value) {
      await updateOfficer(editId.value, {
        real_name: form.real_name,
        title: form.title,
        role_id: form.role_id,
        region: form.region,
        data_scope: form.data_scope,
        phone: form.phone,
        email: form.email,
        remark: form.remark,
      })
      ElMessage.success('鬼差档案已更新')
    } else {
      if (form.username.trim().length < 3) return ElMessage.warning('账号不得少于 3 位')
      if (form.password.length < 6) return ElMessage.warning('初始密码不得少于 6 位')
      await createOfficer({
        username: form.username.trim(),
        password: form.password,
        real_name: form.real_name,
        title: form.title,
        role_id: form.role_id,
        region: form.region,
        data_scope: form.data_scope,
        phone: form.phone,
        email: form.email,
        status: form.status,
        remark: form.remark,
      })
      ElMessage.success('鬼差已入册')
    }
    drawer.value = false
    await load()
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

/* ---------------- 重置密码 ---------------- */
async function resetPwd(row: OfficerRecord) {
  try {
    const { value } = await ElMessageBox.prompt(
      `为「${row.real_name}（${row.username}）」设新密码，不少于 6 位。重置后该账号需以此密码重新登录。`,
      '重置密码',
      {
        confirmButtonText: '确认重置',
        cancelButtonText: '取消',
        inputPlaceholder: '输入新密码',
        inputValidator: (v: string) => (v && v.length >= 6 ? true : '密码不得少于 6 位'),
      },
    )
    await resetOfficerPassword(row.id, value)
    ElMessage.success('密码已重置')
  } catch (err) {
    if (err === 'cancel' || err === 'close') return
    ElMessage.error((err as { message?: string })?.message || '重置失败')
  }
}

/* ---------------- 启停 ---------------- */
async function toggleStatus(row: OfficerRecord) {
  const next = row.status === '在职' ? '停职' : '在职'
  try {
    await ElMessageBox.confirm(
      `确认将「${row.real_name}」状态由「${row.status}」改为「${next}」？停职后该账号将无法登录。`,
      '变更鬼差状态',
      { confirmButtonText: `确认改为${next}`, cancelButtonText: '取消', type: 'warning' },
    )
    await setOfficerStatus(row.id, next)
    ElMessage.success(`已改为「${next}」`)
    await load()
  } catch (err) {
    if (err === 'cancel' || err === 'close') return
    ElMessage.error((err as { message?: string })?.message || '状态变更失败')
  }
}

const scopeLabel = (v: string) => SCOPES.find((s) => s.value === v)?.label || v || '—'

onMounted(() => {
  loadRoles()
  load()
})
</script>

<template>
  <div class="of-page">
    <div class="mv-panel of-banner">
      <div>
        <h2 class="mv-title">鬼差账号</h2>
        <p class="mv-subtitle">掌冥府诸司办案之吏，按角色授职、按鬼域定域，启停之间皆入阴律日志。</p>
      </div>
      <div class="of-banner__ops">
        <el-button v-if="canCreate" class="mv-seal-btn" size="small" @click="openCreate">新增鬼差</el-button>
      </div>
    </div>

    <section class="mv-panel of-list">
      <div class="mv-panel__head">
        <span class="mv-panel__title">名录</span>
        <div class="of-filters">
          <el-input
            v-model="query.keyword"
            placeholder="账号 / 本名"
            clearable
            size="small"
            class="of-w180"
            @keyup.enter="page = 1; load()"
            @clear="page = 1; load()"
          />
          <el-select v-model="query.role_id" placeholder="全部角色" clearable size="small" class="of-w160" @change="page = 1; load()">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
          <el-select v-model="query.region" placeholder="全部鬼域" clearable size="small" class="of-w110" @change="page = 1; load()">
            <el-option v-for="r in REGIONS" :key="r" :label="r" :value="r" />
          </el-select>
          <el-select v-model="query.status" placeholder="全部状态" clearable size="small" class="of-w110" @change="page = 1; load()">
            <el-option label="在职" value="在职" />
            <el-option label="停职" value="停职" />
          </el-select>
          <el-button class="mv-ghost-btn" size="small" @click="page = 1; load()">查阅</el-button>
          <el-button class="mv-ghost-btn" size="small" @click="resetQuery">重置</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" size="small">
        <el-table-column prop="username" label="账号" width="130" />
        <el-table-column prop="real_name" label="本名" width="110">
          <template #default="{ row }">
            <span class="mv-title">{{ row.real_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="职衔" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.title || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <span class="of-role">{{ row.role_name || row.role_code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="region" label="鬼域" width="80" />
        <el-table-column label="数据域" width="150">
          <template #default="{ row }">
            <span class="of-dim">{{ scopeLabel(row.data_scope) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="84">
          <template #default="{ row }">
            <span class="of-status" :class="row.status === '在职' ? 'is-on' : 'is-off'">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="末次登录" width="150">
          <template #default="{ row }">
            <span class="of-dim">{{ row.last_login_at ? formatDateTime(row.last_login_at) : '未曾登录' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" :width="canUpdate || canReset || canStatus ? 210 : 80" fixed="right">
          <template #default="{ row }">
            <div class="of-ops">
              <el-button v-if="canUpdate" link class="of-link" @click="openEdit(row)">编辑</el-button>
              <el-button v-if="canReset" link class="of-link" @click="resetPwd(row)">重置密码</el-button>
              <el-button
                v-if="canStatus"
                link
                class="of-link"
                :class="{ 'is-danger': row.status === '在职' }"
                @click="toggleStatus(row)"
              >{{ row.status === '在职' ? '停职' : '复职' }}</el-button>
              <span v-if="!canUpdate && !canReset && !canStatus" class="of-dim">仅查阅</span>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="of-empty">此条件下无鬼差</div>
        </template>
      </el-table>

      <div class="of-pager">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          @current-change="(p: number) => { page = p; load() }"
        />
      </div>
    </section>

    <el-drawer v-model="drawer" :title="editId ? '编辑鬼差' : '新增鬼差'" size="460px">
      <el-form label-width="88px" label-position="right" size="small">
        <el-form-item label="账号" required>
          <el-input v-model="form.username" :disabled="!!editId" placeholder="登录账号，不少于 3 位" />
        </el-form-item>
        <el-form-item v-if="!editId" label="初始密码" required>
          <el-input v-model="form.password" type="password" show-password placeholder="不少于 6 位" />
        </el-form-item>
        <el-form-item label="本名" required>
          <el-input v-model="form.real_name" placeholder="鬼差姓名" />
        </el-form-item>
        <el-form-item label="职衔">
          <el-input v-model="form.title" placeholder="如：勾魂使、判官、书记官" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="form.role_id" placeholder="择角色" class="of-w100p">
            <el-option v-for="r in roles" :key="r.id" :label="`${r.name}（${r.code}）`" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属鬼域">
          <el-select v-model="form.region" class="of-w100p">
            <el-option v-for="r in REGIONS" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据域">
          <el-select v-model="form.data_scope" class="of-w100p">
            <el-option v-for="s in SCOPES" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="选填" />
        </el-form-item>
        <el-form-item v-if="!editId" label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="在职">在职</el-radio>
            <el-radio value="停职">停职</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="of-drawer-foot">
          <el-button class="mv-ghost-btn" size="small" @click="drawer = false">取消</el-button>
          <el-button class="mv-seal-btn" size="small" :loading="saving" @click="submit">存案</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.of-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.of-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.of-banner .mv-subtitle {
  margin-top: 8px;
}
.of-list {
  padding-bottom: 6px;
}
.of-filters {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.of-w180 {
  width: 180px;
}
.of-w160 {
  width: 160px;
}
.of-w110 {
  width: 110px;
}
.of-w100p {
  width: 100%;
}
.of-role {
  font-size: 12px;
  color: var(--mv-gold);
}
.of-dim {
  font-size: 12px;
  color: var(--mv-muted);
}
.of-status {
  font-size: 12px;
  padding: 1px 7px;
  border: 1px solid transparent;
  border-radius: 2px;
}
.of-status.is-on {
  color: var(--mv-phosphor, #4ce0c3);
  border-color: rgba(76, 224, 195, 0.35);
  background: rgba(76, 224, 195, 0.08);
}
.of-status.is-off {
  color: #e05b45;
  border-color: rgba(224, 91, 69, 0.35);
  background: rgba(224, 91, 69, 0.08);
}
.of-ops {
  display: flex;
  align-items: center;
  gap: 8px;
}
.of-link {
  color: var(--mv-gold);
  padding: 0;
  font-size: 12px;
}
.of-link.is-danger {
  color: #e05b45;
}
.of-empty {
  padding: 26px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
.of-pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px 6px;
}
.of-drawer-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
