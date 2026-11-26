<script setup lang="ts">
/**
 * 无权通行 / 迷途忘川：403 与 404 共用。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

defineOptions({ name: 'ForbiddenView' })

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const isNotFound = computed(() => route.name === 'not-found')
const from = computed(() => (typeof route.query.from === 'string' ? route.query.from : ''))
const need = computed(() => (typeof route.query.need === 'string' ? route.query.need : ''))

const title = computed(() => (isNotFound ? '迷途忘川' : '无权通行'))
const code = computed(() => (isNotFound ? '404' : '403'))
const desc = computed(() =>
  isNotFound
    ? '此路不在幽冥舆图之内，许是判词有误，或文书已被勾销。'
    : '阴律有定，此司不在你的职权之内。若确需查阅，请向酆都大帝请印。',
)

function goBack(): void {
  if (window.history.length > 1) router.back()
  else void router.replace({ name: 'dashboard' })
}

function goHome(): void {
  if (auth.token) void router.replace({ name: 'dashboard' })
  else void router.replace({ name: 'login' })
}

function relogin(): void {
  auth.reset()
  void router.replace({ name: 'login', query: from.value ? { redirect: from.value } : {} })
}
</script>

<template>
  <div class="forbid">
    <div class="forbid__seal m-serif">{{ code }}</div>

    <h1 class="forbid__title m-serif">{{ title }}</h1>
    <p class="forbid__desc">{{ desc }}</p>

    <dl v-if="from || need" class="forbid__kv">
      <div v-if="from" class="forbid__row">
        <dt>所求之处</dt>
        <dd class="m-mono">{{ from }}</dd>
      </div>
      <div v-if="need" class="forbid__row">
        <dt>所需印信</dt>
        <dd class="m-mono m-gold">{{ need }}</dd>
      </div>
    </dl>

    <div class="forbid__acts">
      <button type="button" class="forbid__btn forbid__btn--main" @click="goHome">
        {{ auth.token ? '回工作台' : '回鬼门关' }}
      </button>
      <button type="button" class="forbid__btn" @click="goBack">原路折返</button>
      <button v-if="auth.token" type="button" class="forbid__btn forbid__btn--quiet" @click="relogin">
        换一枚印信
      </button>
    </div>

    <p class="forbid__foot m-faint">幽冥政务 · 移动端</p>
  </div>
</template>

<style scoped lang="scss">
.forbid {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 24px calc(32px + env(safe-area-inset-bottom));
  text-align: center;
}

.forbid__seal {
  width: 92px;
  height: 92px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(212, 85, 63, 0.5);
  border-radius: 10px;
  color: var(--m-fire);
  font-size: 34px;
  letter-spacing: 0.08em;
  background: rgba(212, 85, 63, 0.08);
  box-shadow: inset 0 0 24px rgba(212, 85, 63, 0.16);
  transform: rotate(-4deg);
}

.forbid__title {
  margin: 20px 0 0;
  color: var(--m-text-0);
  font-size: 20px;
  letter-spacing: 0.16em;
}

.forbid__desc {
  margin: 10px 0 0;
  max-width: 320px;
  color: var(--m-text-1);
  font-size: 12.5px;
  line-height: 1.75;
}

.forbid__kv {
  width: 100%;
  max-width: 340px;
  margin: 18px 0 0;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  background: var(--m-ink-1);
  text-align: left;
}

.forbid__row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 11.5px;

  & + & {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed rgba(255, 255, 255, 0.06);
  }

  dt {
    flex: none;
    color: var(--m-text-2);
  }

  dd {
    min-width: 0;
    margin: 0;
    word-break: break-all;
    color: var(--m-text-0);
  }
}

.forbid__acts {
  width: 100%;
  max-width: 340px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin-top: 22px;
}

.forbid__btn {
  height: 42px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  color: var(--m-text-0);
  font-size: 14px;
  letter-spacing: 0.08em;
  background: rgba(255, 255, 255, 0.04);
}

.forbid__btn--main {
  border-color: var(--m-gold-line);
  color: var(--m-gold-soft);
  background: rgba(201, 162, 39, 0.12);
}

.forbid__btn--quiet {
  border-color: transparent;
  color: var(--m-text-2);
  font-size: 12.5px;
  background: transparent;
}

.forbid__foot {
  margin: 26px 0 0;
  font-size: 11px;
}
</style>
