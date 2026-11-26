<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import type { MenuNode } from '@/api/types'
import { clockText, lunarDate } from '@/utils/chineseDate'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const lunar = ref(lunarDate())
const clock = ref(clockText())
let timer = 0

onMounted(() => {
  timer = window.setInterval(() => {
    clock.value = clockText()
    lunar.value = lunarDate()
  }, 1000)
})
onBeforeUnmount(() => window.clearInterval(timer))

interface NavGroup {
  key: string
  name: string
  icon: string
  items: MenuNode[]
}

/** 后端菜单树 → 侧栏结构（一级叶子直接成组，目录收拢子项） */
const navGroups = computed<NavGroup[]>(() => {
  const groups: NavGroup[] = []
  for (const node of auth.menus) {
    const children = (node.children || []).filter((c) => c.visible !== false)
    if (children.length) {
      groups.push({ key: `dir-${node.id}`, name: node.name, icon: node.icon || 'Files', items: children })
    } else if (node.type === '菜单') {
      const last = groups[groups.length - 1]
      if (last && last.key === 'root') last.items.push(node)
      else groups.push({ key: 'root', name: '案牍', icon: 'Files', items: [node] })
    }
  }
  return groups
})

const activePath = computed(() => route.path)

function isActive(path: string): boolean {
  return activePath.value === path || activePath.value.startsWith(`${path}/`)
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('欲离幽冥、还归阳世？当前会籍将被登出。', '辞去值司', {
      confirmButtonText: '登出归阳',
      cancelButtonText: '仍留冥府',
      type: 'warning',
    })
  } catch {
    return
  }
  await auth.signOut()
  router.replace('/login')
}
</script>

<template>
  <div class="mv-shell" :class="{ 'is-collapsed': collapsed }">
    <aside class="mv-aside">
      <div class="mv-brand">
        <div class="mv-brand__seal">冥</div>
        <div v-show="!collapsed" class="mv-brand__text">
          <h1 class="mv-title mv-title--gold">地府生死铺</h1>
          <p class="mv-subtitle">幽冥政务 · 亡魂全流程</p>
        </div>
      </div>
      <div class="mv-divider" />

      <nav class="mv-nav">
        <div v-for="group in navGroups" :key="group.key" class="mv-nav__group">
          <div v-show="!collapsed" class="mv-nav__group-head">
            <el-icon class="mv-nav__group-icon"><component :is="group.icon" /></el-icon>
            <span>{{ group.name }}</span>
          </div>
          <el-tooltip
            v-for="item in group.items"
            :key="item.id"
            :content="item.name"
            placement="right"
            :disabled="!collapsed"
          >
            <router-link :to="item.path" class="mv-nav__item" :class="{ 'is-active': isActive(item.path) }">
              <el-icon class="mv-nav__icon"><component :is="item.icon || 'Menu'" /></el-icon>
              <span v-show="!collapsed" class="mv-nav__text">{{ item.name }}</span>
            </router-link>
          </el-tooltip>
        </div>
      </nav>

      <div class="mv-aside__foot" v-show="!collapsed">
        <div class="mv-aside__line" />
        <p class="mv-aside__hint">阴律昭彰 · 生死有簿</p>
      </div>
    </aside>

    <div class="mv-body">
      <header class="mv-topbar">
        <button class="mv-collapse" type="button" @click="collapsed = !collapsed">
          <el-icon><component :is="collapsed ? 'Expand' : 'Fold'" /></el-icon>
        </button>
        <div class="mv-crumb">
          <span class="mv-crumb__main">{{ route.meta.title }}</span>
          <span class="mv-crumb__sub mv-muted">/ {{ auth.regionName }}鬼域</span>
        </div>

        <div class="mv-spacer" />

        <div class="mv-chips">
          <span class="mv-chip">值司 · {{ auth.roleName }}</span>
          <span class="mv-chip">殿次 · {{ auth.dutyTitle }}</span>
          <span class="mv-chip mv-chip--lunar">
            <el-icon><MoonNight /></el-icon>
            阴历 {{ lunar }}
          </span>
          <span class="mv-chip mv-chip--clock">{{ clock }}</span>
        </div>

        <el-dropdown trigger="click" @command="handleLogout">
          <span class="mv-user">
            <span class="mv-user__seal">{{ (auth.profile?.real_name || '鬼').slice(0, 1) }}</span>
            <span class="mv-user__name">{{ auth.profile?.real_name || '无名鬼差' }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">辞去值司 · 登出</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>

      <main class="mv-main">
        <router-view v-slot="{ Component }">
          <transition name="mv-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.mv-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ---------------- 侧栏 ---------------- */
.mv-aside {
  width: 236px;
  flex: 0 0 236px;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(180deg, rgba(18, 24, 31, 0.98), rgba(8, 8, 12, 0.99));
  border-right: 1px solid rgba(201, 162, 39, 0.22);
  box-shadow: 6px 0 28px rgba(0, 0, 0, 0.55);
  transition: width 0.24s ease, flex-basis 0.24s ease;
  overflow: hidden;
}
.is-collapsed .mv-aside {
  width: 68px;
  flex-basis: 68px;
}

.mv-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 16px 12px;
}
.mv-brand__seal {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  display: grid;
  place-items: center;
  font-family: var(--mv-font-title);
  font-size: 20px;
  color: #f6ece0;
  background: linear-gradient(160deg, #c8382d, #8b1712);
  border: 1px solid rgba(201, 162, 39, 0.6);
  box-shadow: 0 0 16px rgba(179, 38, 30, 0.45), inset 0 0 8px rgba(0, 0, 0, 0.4);
  border-radius: 2px;
}
.mv-brand__text h1 {
  font-size: 17px;
  line-height: 1.2;
}
.mv-brand__text p {
  margin: 4px 0 0;
  font-size: 11px;
}

.mv-nav {
  flex: 1;
  overflow-y: auto;
  padding: 6px 10px 20px;
}
.mv-nav__group + .mv-nav__group {
  margin-top: 6px;
}
.mv-nav__group-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 6px 6px;
  font-family: var(--mv-font-title);
  font-size: 11px;
  letter-spacing: 0.26em;
  color: rgba(201, 162, 39, 0.72);
}
.mv-nav__group-icon {
  font-size: 12px;
  opacity: 0.7;
}
.mv-nav__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  margin: 2px 0;
  color: var(--mv-paper-dim);
  text-decoration: none;
  font-size: 13px;
  letter-spacing: 0.08em;
  border: 1px solid transparent;
  border-radius: 2px;
  transition: all 0.16s ease;
}
.mv-nav__item:hover {
  color: var(--mv-paper);
  background: rgba(201, 162, 39, 0.06);
  border-color: rgba(201, 162, 39, 0.18);
}
.mv-nav__item.is-active {
  color: #fff4e0;
  background:
    linear-gradient(90deg, rgba(179, 38, 30, 0.24) 0%, rgba(201, 162, 39, 0.08) 60%, rgba(18, 24, 31, 0.1) 100%);
  border-color: rgba(201, 162, 39, 0.5);
  box-shadow:
    inset 2px 0 0 var(--mv-cinnabar-lit),
    inset 0 0 22px rgba(201, 162, 39, 0.07);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9);
}
.mv-nav__item.is-active .mv-nav__icon {
  color: var(--mv-gold);
}
.mv-nav__icon {
  font-size: 15px;
  flex: 0 0 15px;
}
.mv-nav__text {
  white-space: nowrap;
}
.mv-aside__foot {
  padding: 10px 16px 16px;
}
.mv-aside__line {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(201, 162, 39, 0.35), transparent);
}
.mv-aside__hint {
  margin: 8px 0 0;
  font-family: var(--mv-font-title);
  font-size: 10px;
  letter-spacing: 0.22em;
  color: rgba(125, 119, 108, 0.85);
  text-align: center;
}

/* ---------------- 主体 ---------------- */
.mv-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.mv-topbar {
  height: 62px;
  flex: 0 0 62px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 20px;
  background: linear-gradient(180deg, rgba(22, 30, 39, 0.92), rgba(11, 11, 16, 0.72));
  border-bottom: 1px solid rgba(201, 162, 39, 0.2);
  backdrop-filter: blur(6px);
}
.mv-collapse {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  color: var(--mv-gold);
  background: rgba(201, 162, 39, 0.06);
  border: 1px solid rgba(201, 162, 39, 0.28);
  border-radius: 2px;
  cursor: pointer;
}
.mv-collapse:hover {
  background: rgba(201, 162, 39, 0.14);
}
.mv-crumb {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.mv-crumb__main {
  font-family: var(--mv-font-title);
  font-size: 17px;
  letter-spacing: 0.2em;
  color: var(--mv-paper);
}
.mv-crumb__sub {
  font-size: 11px;
  letter-spacing: 0.14em;
}
.mv-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.mv-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--mv-paper-dim);
  background: rgba(201, 162, 39, 0.05);
  border: 1px solid rgba(201, 162, 39, 0.2);
  border-radius: 2px;
}
.mv-chip--lunar {
  color: var(--mv-gold);
}
.mv-chip--clock {
  color: var(--mv-phosphor);
  font-variant-numeric: tabular-nums;
}
.mv-user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px 5px 5px;
  cursor: pointer;
  color: var(--mv-paper);
  border: 1px solid rgba(201, 162, 39, 0.24);
  border-radius: 2px;
  background: rgba(201, 162, 39, 0.04);
}
.mv-user__seal {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  font-family: var(--mv-font-title);
  font-size: 13px;
  color: #f6ece0;
  background: linear-gradient(160deg, #c8382d, #8b1712);
  border: 1px solid rgba(201, 162, 39, 0.5);
}
.mv-user__name {
  font-size: 12px;
  letter-spacing: 0.12em;
}

.mv-main {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 20px 28px;
}

.mv-fade-enter-active,
.mv-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.mv-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.mv-fade-leave-to {
  opacity: 0;
}
</style>
