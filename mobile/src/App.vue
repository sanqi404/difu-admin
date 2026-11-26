<script setup lang="ts">
import { onMounted } from 'vue'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

onMounted(() => {
  // 启动时若本地已有令牌，尝试静默恢复身份（失败自动清理并跳登录）
  if (auth.token && !auth.loaded) void auth.hydrate()
})
</script>

<template>
  <router-view v-slot="{ Component }">
    <transition name="m-fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<style lang="scss">
.m-fade-enter-active,
.m-fade-leave-active {
  transition: opacity 0.18s ease;
}

.m-fade-enter-from,
.m-fade-leave-to {
  opacity: 0;
}
</style>
