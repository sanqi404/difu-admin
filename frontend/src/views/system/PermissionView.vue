<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchPermissionGroups, fetchRoles } from '@/api'
import type { PermissionItem, RoleItem } from '@/api/types'

const TYPES = ['菜单', '按钮', '接口']
const loading = ref(false)
const modules = ref<{ module: string; items: PermissionItem[] }[]>([])
const flat = ref<PermissionItem[]>([])
const roles = ref<RoleItem[]>([])
const keyword = ref('')
const typeFilter = ref('')
const activeModule = ref('')

const typeStats = computed(() => {
  const c: Record<string, number> = {}
  flat.value.forEach((p) => (c[p.type] = (c[p.type] || 0) + 1))
  return c
})

const moduleStats = computed(() =>
  modules.value.map((m) => ({
    module: m.module,
    count: m.items.length,
    grantedRoles: roles.value.filter((r) => r.code === 'SUPER_ADMIN' || (r.permissions || []).some((code) => m.items.some((p) => p.code === code))).length,
  })),
)

const shown = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return modules.value
    .filter((m) => !activeModule.value || m.module === activeModule.value)
    .map((m) => ({
      module: m.module,
      items: m.items.filter(
        (p) =>
          (!kw || `${p.name}${p.code}`.toLowerCase().includes(kw)) && (!typeFilter.value || p.type === typeFilter.value),
      ),
    }))
    .filter((m) => m.items.length)
})

function rolesHaving(code: string) {
  return roles.value.filter((r) => r.code === 'SUPER_ADMIN' || (r.permissions || []).includes(code)).map((r) => r.name)
}

async function load() {
  loading.value = true
  try {
    const [res, roleList] = await Promise.all([fetchPermissionGroups(), fetchRoles().catch(() => [] as RoleItem[])])
    modules.value = res.modules || []
    flat.value = res.flat || []
    roles.value = roleList
  } catch (err) {
    ElMessage.error((err as { message?: string })?.message || '权限点读取失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="pm-page">
    <div class="mv-panel pm-banner">
      <div>
        <h2 class="mv-title">权限点</h2>
        <p class="mv-subtitle">权者，可为之界也。权限点按模块归拢，授于角色、挂于接口，超管持「*」通诸关。</p>
      </div>
      <div class="pm-banner__stats">
        <div class="pm-stat">
          <span class="pm-stat__label">权限点</span>
          <strong class="pm-stat__value">{{ flat.length }}</strong>
        </div>
        <div class="pm-stat">
          <span class="pm-stat__label">模块</span>
          <strong class="pm-stat__value mv-gold">{{ modules.length }}</strong>
        </div>
        <div v-for="t in TYPES" :key="t" class="pm-stat">
          <span class="pm-stat__label">{{ t }}</span>
          <strong class="pm-stat__value">{{ typeStats[t] || 0 }}</strong>
        </div>
      </div>
    </div>

    <div class="pm-body">
      <section class="mv-panel pm-left">
        <div class="mv-panel__head">
          <span class="mv-panel__title">模块</span>
        </div>
        <div class="pm-modules">
          <button class="pm-module" :class="{ 'is-active': !activeModule }" @click="activeModule = ''">
            <span class="pm-module__name">全部</span>
            <span class="pm-module__count">{{ flat.length }}</span>
          </button>
          <button
            v-for="m in moduleStats"
            :key="m.module"
            class="pm-module"
            :class="{ 'is-active': activeModule === m.module }"
            @click="activeModule = activeModule === m.module ? '' : m.module"
          >
            <span class="pm-module__name">{{ m.module }}</span>
            <span class="pm-module__count">{{ m.count }}</span>
          </button>
        </div>
      </section>

      <section v-loading="loading" class="mv-panel pm-right">
        <div class="mv-panel__head">
          <span class="mv-panel__title">{{ activeModule || '全部权限' }}</span>
          <div class="pm-filters">
            <el-input v-model="keyword" placeholder="名称 / 权限码" clearable size="small" class="pm-w200" />
            <el-select v-model="typeFilter" placeholder="全部类型" clearable size="small" class="pm-w110">
              <el-option v-for="t in TYPES" :key="t" :label="t" :value="t" />
            </el-select>
          </div>
        </div>

        <div class="pm-groups">
          <div v-for="g in shown" :key="g.module" class="pm-group">
            <div class="pm-group__head">
              <span class="pm-group__name">{{ g.module }}</span>
              <span class="pm-group__count">{{ g.items.length }}</span>
            </div>
            <div class="pm-cards">
              <div v-for="p in g.items" :key="p.id" class="pm-card">
                <div class="pm-card__head">
                  <span class="pm-card__name">{{ p.name }}</span>
                  <span class="pm-card__type" :class="`t-${p.type}`">{{ p.type }}</span>
                </div>
                <code class="pm-card__code">{{ p.code }}</code>
                <div class="pm-card__roles">
                  <span class="pm-card__label">已授</span>
                  <template v-if="rolesHaving(p.code).length">
                    <span v-for="r in rolesHaving(p.code)" :key="r" class="pm-card__tag">{{ r }}</span>
                  </template>
                  <span v-else class="pm-card__none">未授任何角色</span>
                </div>
              </div>
            </div>
          </div>
          <div v-if="!shown.length" class="pm-empty">此条件下无权限点</div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.pm-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pm-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 22px;
  flex-wrap: wrap;
}
.pm-banner .mv-subtitle {
  margin-top: 8px;
  max-width: 560px;
}
.pm-banner__stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.pm-stat {
  min-width: 76px;
  padding: 8px 12px;
  border: 1px solid rgba(232, 227, 214, 0.12);
  background: rgba(232, 227, 214, 0.03);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.pm-stat__label {
  font-size: 12px;
  color: var(--mv-muted);
  letter-spacing: 0.08em;
}
.pm-stat__value {
  font-family: var(--mv-font-title);
  font-size: 20px;
  line-height: 1.1;
}
.pm-body {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}
.pm-modules {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  max-height: 640px;
  overflow: auto;
}
.pm-module {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  font-size: 13px;
  color: var(--mv-muted);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  text-align: left;
}
.pm-module:hover {
  color: var(--mv-paper);
  border-color: rgba(232, 227, 214, 0.12);
}
.pm-module.is-active {
  color: var(--mv-gold);
  border-color: rgba(201, 162, 39, 0.5);
  background: rgba(201, 162, 39, 0.07);
}
.pm-module__name {
  font-family: var(--mv-font-title);
}
.pm-module__count {
  font-size: 11px;
  color: var(--mv-muted);
}
.pm-filters {
  display: flex;
  gap: 8px;
  align-items: center;
}
.pm-w200 {
  width: 200px;
}
.pm-w110 {
  width: 110px;
}
.pm-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 14px 18px 20px;
  max-height: 680px;
  overflow: auto;
}
.pm-group__head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(232, 227, 214, 0.1);
}
.pm-group__name {
  font-family: var(--mv-font-title);
  font-size: 15px;
  letter-spacing: 0.1em;
  color: var(--mv-paper);
}
.pm-group__count {
  font-size: 11px;
  color: var(--mv-muted);
}
.pm-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(232px, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.pm-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid rgba(232, 227, 214, 0.1);
  background: rgba(232, 227, 214, 0.02);
}
.pm-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.pm-card__name {
  font-size: 13px;
  color: var(--mv-paper);
}
.pm-card__type {
  font-size: 10px;
  padding: 0 5px;
  color: var(--mv-muted);
  border: 1px solid rgba(232, 227, 214, 0.18);
}
.pm-card__type.t-菜单 {
  color: var(--mv-gold);
  border-color: rgba(201, 162, 39, 0.4);
}
.pm-card__type.t-接口 {
  color: var(--mv-phosphor, #4ce0c3);
  border-color: rgba(76, 224, 195, 0.35);
}
.pm-card__code {
  font-size: 11px;
  color: rgba(201, 162, 39, 0.85);
  letter-spacing: 0.04em;
  word-break: break-all;
}
.pm-card__roles {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding-top: 4px;
  border-top: 1px dashed rgba(232, 227, 214, 0.1);
}
.pm-card__label {
  font-size: 11px;
  color: var(--mv-muted);
}
.pm-card__tag {
  font-size: 11px;
  padding: 0 6px;
  color: var(--mv-phosphor, #4ce0c3);
  border: 1px solid rgba(76, 224, 195, 0.28);
}
.pm-card__none {
  font-size: 11px;
  color: rgba(232, 227, 214, 0.32);
}
.pm-empty {
  padding: 40px 0;
  text-align: center;
  font-family: var(--mv-font-title);
  color: var(--mv-muted);
}
@media (max-width: 1200px) {
  .pm-body {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
