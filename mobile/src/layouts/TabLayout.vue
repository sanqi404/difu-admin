<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const active = computed<string>({
  get: () => (route.meta.tab as string) || 'dashboard',
  set: (name: string) => {
    const map: Record<string, string> = {
      dashboard: '/',
      inbox: '/inbox',
      messages: '/messages',
      me: '/me',
    }
    const target = map[name]
    if (target && route.path !== target) void router.push(target)
  },
})

const todoBadge = computed(() => (app.todoCount > 0 ? (app.todoCount > 99 ? '99+' : app.todoCount) : undefined))
const unreadBadge = computed(() =>
  app.unreadCount > 0 ? (app.unreadCount > 99 ? '99+' : app.unreadCount) : undefined,
)

onMounted(() => {
  void app.refreshCounters()
})

// 切换 Tab 时同步刷新角标，保证待办/未读数据不过期
watch(
  () => route.fullPath,
  () => {
    void app.refreshCounters()
  },
)
</script>

<template>
  <div class="tab-layout">
    <router-view v-slot="{ Component }">
      <keep-alive :include="['DashboardView', 'InboxView', 'MessagesView']">
        <component :is="Component" />
      </keep-alive>
    </router-view>

    <div class="tab-layout__bar">
      <van-tabbar v-model="active" fixed safe-area-inset-bottom>
        <van-tabbar-item name="dashboard" icon="wap-home-o">工作台</van-tabbar-item>
        <van-tabbar-item name="inbox" icon="todo-list-o" :badge="todoBadge">待办</van-tabbar-item>
        <van-tabbar-item name="messages" icon="envelop-o" :badge="unreadBadge">消息</van-tabbar-item>
        <van-tabbar-item name="me" icon="manager-o">我的</van-tabbar-item>
      </van-tabbar>
    </div>

    <div v-if="!auth.isLogged" class="tab-layout__mask">
      <span>令牌已失效，正在返回鬼门关…</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.tab-layout {
  min-height: 100%;
}

.tab-layout__mask {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--m-gold);
  font-size: 13px;
  background: rgba(13, 15, 20, 0.86);
}
</style>
