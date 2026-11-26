<script setup lang="ts">
/**
 * 我的：身份卡 / 权限清单 / 设备绑定 / 退出登录。
 */
import { computed, onActivated, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showFailToast, showSuccessToast } from 'vant'
import { devicesApi } from '@/api/mobile'
import type { DeviceItem } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { formatDateTime } from '@/utils/format'

defineOptions({ name: 'ProfileView' })

const DEVICE_KEY = 'difu.mobile.device_id'

const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const devices = ref<DeviceItem[]>([])
const loadingDevices = ref(false)
const binding = ref(false)
const showPerms = ref(false)

const perms = computed(() => auth.perms || [])
const permPreview = computed(() => (showPerms.value ? perms.value : perms.value.slice(0, 6)))
const scopeText = computed(() => {
  if (auth.isSuper) return '全域通行（超管）'
  return auth.dataScope || '本辖区'
})

function deviceId(): string {
  const cached = localStorage.getItem(DEVICE_KEY)
  if (cached) return cached
  const next = `h5-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
  localStorage.setItem(DEVICE_KEY, next)
  return next
}

async function loadDevices(): Promise<void> {
  if (loadingDevices.value) return
  loadingDevices.value = true
  try {
    const res = await devicesApi.list()
    devices.value = Array.isArray(res) ? res : []
  } catch {
    devices.value = []
  } finally {
    loadingDevices.value = false
  }
}

async function bindThisDevice(): Promise<void> {
  if (binding.value) return
  binding.value = true
  try {
    const mine = deviceId()
    if (devices.value.some((item) => item.device_id === mine)) {
      showSuccessToast('本机已在册')
      return
    }
    await devicesApi.bind({ device_id: mine, platform: 'h5' })
    showSuccessToast('本机已驻册')
    await loadDevices()
  } catch {
    /* 错误提示由 http 层统一弹出 */
  } finally {
    binding.value = false
  }
}

async function unbindDevice(item: DeviceItem): Promise<void> {
  const isCurrent = item.device_id === deviceId()
  try {
    await showConfirmDialog({
      title: '解绑设备',
      message: isCurrent
        ? '解绑后本机将收不到推送阴讯，是否继续？'
        : `确认解绑设备「${item.device_id}」？`,
      confirmButtonText: '解绑',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await devicesApi.unbind(item.id)
    showSuccessToast('已解绑')
    await loadDevices()
  } catch {
    /* 错误提示由 http 层统一弹出 */
  }
}

async function refreshIdentity(): Promise<void> {
  try {
    await auth.loadIdentity()
    void app.refreshCounters()
    showSuccessToast('身份已刷新')
  } catch {
    showFailToast('身份刷新失败')
  }
}

async function onSignOut(): Promise<void> {
  try {
    await showConfirmDialog({
      title: '返回鬼门关',
      message: '退出后需重新验明身份，是否继续？',
      confirmButtonText: '退出登录',
      cancelButtonText: '留下',
    })
  } catch {
    return
  }
  await auth.signOut()
  app.reset()
  void router.replace({ name: 'login' })
}

onMounted(() => {
  void loadDevices()
})

onActivated(() => {
  void loadDevices()
})
</script>

<template>
  <div class="m-page m-page--tabbar me">
    <header class="me__head">
      <h1 class="me__title m-serif">我的</h1>
      <p class="me__sub m-faint">{{ auth.isLogged ? '此身在册，印信有效' : '尚未验明身份' }}</p>
    </header>

    <section class="me__idcard">
      <div class="me__avatar m-serif">{{ (auth.displayName || '差').slice(0, 1) }}</div>
      <div class="me__idmain">
        <h2 class="me__name m-serif">
          {{ auth.displayName }}
          <span v-if="auth.badgeText" class="m-badge">{{ auth.badgeText }}</span>
        </h2>
        <p class="me__role">{{ auth.roleName }}<template v-if="auth.dutyTitle"> · {{ auth.dutyTitle }}</template></p>
        <p class="me__region m-faint">
          <van-icon name="location-o" /> {{ auth.regionName || '未定辖区' }}
        </p>
      </div>
    </section>

    <section class="m-card">
      <div class="m-card__head">
        <span class="m-card__title">印信与权限</span>
        <button type="button" class="me__mini" @click="refreshIdentity">
          <van-icon name="replay" /> 刷新
        </button>
      </div>
      <div class="me__kv">
        <span class="me__k">数据范围</span>
        <span class="me__v">{{ scopeText }}</span>
      </div>
      <div class="me__kv">
        <span class="me__k">令牌状态</span>
        <span class="me__v" :class="auth.isLogged ? 'm-teal' : 'm-fire'">
          {{ auth.isLogged ? '有效' : '已失效' }}
        </span>
      </div>

      <div class="me__perm-head">
        <span class="me__k">权限点数</span>
        <span class="me__v m-mono">{{ perms.length }}</span>
      </div>
      <div class="me__perms">
        <span v-for="code in permPreview" :key="code" class="me__perm m-mono">{{ code }}</span>
        <span v-if="!perms.length" class="m-faint">未获授权项</span>
      </div>
      <button
        v-if="perms.length > 6"
        type="button"
        class="me__more"
        @click="showPerms = !showPerms"
      >
        {{ showPerms ? '收起' : `展开全部 ${perms.length} 项` }}
        <van-icon :name="showPerms ? 'arrow-up' : 'arrow-down'" />
      </button>
    </section>

    <section class="m-card">
      <div class="m-card__head">
        <span class="m-card__title">随身法器（设备）</span>
        <button type="button" class="me__mini" :disabled="binding" @click="bindThisDevice">
          <van-icon name="add-o" /> {{ binding ? '驻册中' : '绑定本机' }}
        </button>
      </div>

      <div v-if="loadingDevices && !devices.length" class="m-faint me__loading">正在核验设备…</div>
      <div v-else-if="!devices.length" class="m-empty">尚无设备在册</div>

      <div v-for="item in devices" :key="item.id" class="me__dev">
        <div class="me__dev-main">
          <p class="me__dev-id m-mono">
            {{ item.device_id }}
            <span v-if="item.device_id === deviceId()" class="m-badge me__dev-flag">本机</span>
          </p>
          <p class="me__dev-meta m-faint">
            {{ item.platform || '未知平台' }} · 活跃 {{ formatDateTime(item.last_active_at) }}
          </p>
        </div>
        <button type="button" class="me__dev-del" @click="unbindDevice(item)">解绑</button>
      </div>
    </section>

    <button type="button" class="me__logout" @click="onSignOut">
      <van-icon name="sign" /> 退出登录
    </button>

    <p class="me__foot m-faint">幽冥政务 · 移动决策端 v0.1.0</p>
  </div>
</template>

<style scoped lang="scss">
.me__head {
  padding: 4px 2px 10px;
}

.me__title {
  margin: 0;
  color: var(--m-text-0);
  font-size: 20px;
  letter-spacing: 0.1em;
}

.me__sub {
  margin: 5px 0 0;
}

.me__idcard {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--m-gold-line);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(201, 162, 39, 0.12), rgba(201, 162, 39, 0.02)), var(--m-ink-1);
}

.me__avatar {
  flex: none;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--m-gold-line);
  border-radius: 50%;
  color: var(--m-gold);
  font-size: 20px;
  background: rgba(201, 162, 39, 0.1);
}

.me__idmain {
  min-width: 0;
}

.me__name {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  color: var(--m-text-0);
  font-size: 17px;
  letter-spacing: 0.06em;
}

.me__role {
  margin: 5px 0 0;
  color: var(--m-text-1);
  font-size: 12px;
}

.me__region {
  margin: 3px 0 0;
}

.me__mini {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  height: 24px;
  padding: 0 8px;
  border: 1px solid var(--m-gold-line);
  border-radius: 12px;
  color: var(--m-gold-soft);
  font-size: 11px;
  background: rgba(201, 162, 39, 0.08);

  &:disabled {
    opacity: 0.45;
  }
}

.me__kv {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.06);
  font-size: 12.5px;
}

.me__perm-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0 0;
  font-size: 12.5px;
}

.me__k {
  color: var(--m-text-2);
}

.me__v {
  color: var(--m-text-0);
}

.me__perms {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.me__perm {
  padding: 3px 7px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 4px;
  color: var(--m-text-1);
  font-size: 10.5px;
  background: rgba(255, 255, 255, 0.03);
}

.me__more {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-top: 9px;
  padding: 0;
  border: 0;
  color: var(--m-gold-soft);
  font-size: 11.5px;
  background: transparent;
}

.me__loading {
  padding: 10px 0;
}

.me__dev {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.06);

  &:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }
}

.me__dev-main {
  min-width: 0;
}

.me__dev-id {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  overflow: hidden;
  color: var(--m-text-0);
  font-size: 12px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.me__dev-flag {
  flex: none;
  height: 17px;
  line-height: 15px;
  font-size: 10px;
}

.me__dev-meta {
  margin: 4px 0 0;
  font-size: 11px;
}

.me__dev-del {
  flex: none;
  height: 26px;
  padding: 0 10px;
  border: 1px solid rgba(212, 85, 63, 0.4);
  border-radius: 13px;
  color: var(--m-fire);
  font-size: 11.5px;
  background: rgba(212, 85, 63, 0.1);
}

.me__logout {
  width: 100%;
  height: 42px;
  margin-top: 14px;
  border: 1px solid rgba(212, 85, 63, 0.45);
  border-radius: 10px;
  color: var(--m-fire);
  font-size: 14px;
  letter-spacing: 0.1em;
  background: rgba(212, 85, 63, 0.1);
}

.me__foot {
  margin: 16px 0 0;
  text-align: center;
  font-size: 11px;
}
</style>
