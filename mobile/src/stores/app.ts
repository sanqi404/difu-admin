/** 全局角标计数：待办 / 未读消息，供 Tabbar 与工作台复用 */
import { ref } from 'vue'
import { defineStore } from 'pinia'

import { approvalsApi, messagesApi } from '@/api/mobile'

export const useAppStore = defineStore('app', () => {
  const todoCount = ref(0)
  const unreadCount = ref(0)
  const onDutyOrderCount = ref(0)
  const refreshedAt = ref(0)
  const refreshing = ref(false)

  /** 拉取待办数、未读数（失败静默，不打扰用户） */
  async function refreshCounters(): Promise<void> {
    if (refreshing.value) return
    refreshing.value = true
    try {
      const [todo, unread] = await Promise.allSettled([
        approvalsApi.list({ scope: 'todo', page: 1, page_size: 1 }),
        messagesApi.unreadCount(),
      ])
      if (todo.status === 'fulfilled') todoCount.value = todo.value.meta?.total ?? 0
      if (unread.status === 'fulfilled') unreadCount.value = unread.value.unread ?? 0
      refreshedAt.value = Date.now()
    } finally {
      refreshing.value = false
    }
  }

  function setTodoCount(value: number): void {
    todoCount.value = Math.max(0, value)
  }

  function setUnreadCount(value: number): void {
    unreadCount.value = Math.max(0, value)
  }

  function decrementUnread(step = 1): void {
    unreadCount.value = Math.max(0, unreadCount.value - step)
  }

  function reset(): void {
    todoCount.value = 0
    unreadCount.value = 0
    onDutyOrderCount.value = 0
    refreshedAt.value = 0
  }

  return {
    todoCount,
    unreadCount,
    onDutyOrderCount,
    refreshedAt,
    refreshing,
    refreshCounters,
    setTodoCount,
    setUnreadCount,
    decrementUnread,
    reset,
  }
})
