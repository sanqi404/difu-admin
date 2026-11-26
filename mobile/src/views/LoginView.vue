<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'

import { fetchCaptcha } from '@/api/auth'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const form = reactive({
  username: '',
  password: '',
  captcha_code: '',
})

const captchaId = ref('')
const captchaImg = ref('')
const captchaLoading = ref(false)

// dev 环境验证码固定 0000，后端 CAPTCHA_DEV_CODE 已开启豁免
const DEV_CAPTCHA = '0000'

const demoAccounts = [
  { username: 'admin', password: '123123', role: '酆都大帝', desc: '超级管理员' },
  { username: 'cuiyu', password: '123456', role: '崔珏', desc: '生死簿主簿' },
  { username: 'yanluo_05', password: '123456', role: '十殿阎罗', desc: '判官' },
  { username: 'wuchang_hei', password: '123456', role: '黑白无常', desc: '外勤鬼差' },
  { username: 'dizang', password: '123456', role: '地藏王', desc: '稽核' },
]

async function loadCaptcha(): Promise<void> {
  if (captchaLoading.value) return
  captchaLoading.value = true
  try {
    const data = await fetchCaptcha()
    captchaId.value = data.captcha_id
    captchaImg.value = data.image?.startsWith('data:') ? data.image : `data:image/png;base64,${data.image}`
    if (!form.captcha_code) form.captcha_code = DEV_CAPTCHA
  } catch {
    captchaImg.value = ''
  } finally {
    captchaLoading.value = false
  }
}

function useDemo(item: (typeof demoAccounts)[number]): void {
  form.username = item.username
  form.password = item.password
  form.captcha_code = DEV_CAPTCHA
  showToast({ message: `已填入 ${item.role} 的通关文牒`, duration: 1200 })
}

async function submit(): Promise<void> {
  if (auth.loading) return
  if (!form.username.trim()) {
    showToast('请填写鬼差账号')
    return
  }
  if (!form.password) {
    showToast('请填写令牌口令')
    return
  }
  if (!form.captcha_code.trim()) {
    showToast('请填写路引验证码')
    return
  }

  try {
    await auth.signIn({
      username: form.username.trim(),
      password: form.password,
      // 未取到 captcha_id 时仍传占位值，后端 dev 模式按 CAPTCHA_DEV_CODE 放行
      captcha_id: captchaId.value || 'devbypass0000',
      captcha_code: form.captcha_code.trim().toUpperCase(),
    })
    app.reset()
    void app.refreshCounters()
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch {
    // 错误提示已由 HTTP 层统一弹出，这里只需刷新验证码
    form.captcha_code = ''
    await loadCaptcha()
  }
}

onMounted(() => {
  void loadCaptcha()
})
</script>

<template>
  <div class="login">
    <div class="login__mist"></div>

    <header class="login__gate">
      <div class="login__plaque">鬼门关</div>
      <div class="login__ridge"></div>
      <p class="login__sub">幽冥政务中台 · 移动端通关文牒</p>
    </header>

    <section class="m-card m-card--gold login__panel">
      <div class="login__panel-head">
        <span class="login__panel-title">验明正身</span>
        <span class="m-faint">阳间弟子勿入</span>
      </div>

      <van-field
        v-model="form.username"
        label="鬼差"
        placeholder="请输入账号"
        clearable
        autocomplete="username"
      />
      <van-field
        v-model="form.password"
        type="password"
        label="口令"
        placeholder="请输入密码"
        autocomplete="current-password"
        @keyup.enter="submit"
      />
      <van-field
        v-model="form.captcha_code"
        label="路引"
        placeholder="图形验证码"
        maxlength="6"
        @keyup.enter="submit"
      >
        <template #button>
          <button class="login__captcha" type="button" :disabled="captchaLoading" @click="loadCaptcha">
            <img v-if="captchaImg" :src="captchaImg" alt="路引验证码" />
            <span v-else>{{ captchaLoading ? '请符中' : '点击获取' }}</span>
          </button>
        </template>
      </van-field>

      <div class="login__dev-hint">
        <van-icon name="info-o" />
        <span>本地联调环境路引固定为 <b class="m-mono">0000</b>，可随意填写</span>
      </div>

      <van-button
        class="login__submit"
        type="primary"
        block
        round
        :loading="auth.loading"
        loading-text="通关中…"
        @click="submit"
      >
        入 关
      </van-button>
    </section>

    <section class="login__accounts">
      <div class="login__accounts-head">
        <span class="m-serif">演示文牒</span>
        <span class="m-faint">点击即填入账号</span>
      </div>
      <div class="login__accounts-grid">
        <button
          v-for="item in demoAccounts"
          :key="item.username"
          class="login__account"
          type="button"
          @click="useDemo(item)"
        >
          <span class="login__account-role m-serif">{{ item.role }}</span>
          <span class="login__account-name m-mono">{{ item.username }}</span>
          <span class="login__account-desc">{{ item.desc }}</span>
        </button>
      </div>
    </section>

    <footer class="login__foot m-faint">
      <p>阴律司 · 幽冥政务中台 v0.1.0</p>
      <p>生死有命，文书有凭</p>
    </footer>
  </div>
</template>

<style scoped lang="scss">
.login {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 42px 18px calc(24px + env(safe-area-inset-bottom));
  overflow: hidden;
}

.login__mist {
  position: absolute;
  top: -90px;
  left: 50%;
  width: 520px;
  height: 320px;
  transform: translateX(-50%);
  pointer-events: none;
  background: radial-gradient(ellipse at 50% 50%, rgba(201, 162, 39, 0.22), rgba(201, 162, 39, 0) 68%);
  filter: blur(6px);
}

.login__gate {
  position: relative;
  text-align: center;
}

.login__plaque {
  display: inline-block;
  padding: 6px 26px;
  border: 1px solid rgba(201, 162, 39, 0.5);
  border-radius: 4px;
  color: #e9cd76;
  font-family: 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 34px;
  font-weight: 700;
  letter-spacing: 0.28em;
  text-indent: 0.28em;
  text-shadow: 0 0 18px rgba(201, 162, 39, 0.55);
  background: linear-gradient(180deg, rgba(201, 162, 39, 0.16), rgba(201, 162, 39, 0.02));
  box-shadow: inset 0 0 24px rgba(201, 162, 39, 0.16);
}

.login__ridge {
  width: 132px;
  height: 1px;
  margin: 14px auto 10px;
  background: linear-gradient(90deg, transparent, rgba(201, 162, 39, 0.7), transparent);
}

.login__sub {
  margin: 0;
  color: var(--m-text-1);
  font-size: 12px;
  letter-spacing: 0.22em;
}

.login__panel {
  margin-top: 30px;
  padding: 16px 16px 18px;
}

.login__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.08);
}

.login__panel-title {
  color: var(--m-gold);
  font-family: 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 15px;
  letter-spacing: 0.12em;
}

.login__captcha {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 92px;
  height: 34px;
  padding: 0;
  border: 1px solid rgba(201, 162, 39, 0.35);
  border-radius: 6px;
  color: var(--m-gold);
  font-size: 12px;
  background: rgba(255, 255, 255, 0.04);
  overflow: hidden;
}

.login__captcha img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.login__dev-hint {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 10px 0 4px;
  color: var(--m-text-2);
  font-size: 11px;
}

.login__dev-hint b {
  color: var(--m-gold-soft);
}

.login__submit {
  margin-top: 14px;
  font-family: 'Songti SC', 'STSong', serif;
  letter-spacing: 0.4em;
  text-indent: 0.4em;
  font-weight: 600;
}

.login__accounts {
  margin-top: 22px;
}

.login__accounts-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
  color: var(--m-text-1);
  font-size: 13px;
}

.login__accounts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.login__account {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 9px 10px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  text-align: left;
  background: rgba(255, 255, 255, 0.025);
  transition: border-color 0.16s ease, background 0.16s ease;

  &:active {
    border-color: rgba(201, 162, 39, 0.45);
    background: rgba(201, 162, 39, 0.08);
  }
}

.login__account-role {
  color: var(--m-text-0);
  font-size: 13px;
  letter-spacing: 0.06em;
}

.login__account-name {
  color: var(--m-gold-soft);
  font-size: 11px;
}

.login__account-desc {
  color: var(--m-text-2);
  font-size: 10px;
}

.login__foot {
  margin-top: auto;
  padding-top: 26px;
  text-align: center;
  line-height: 1.9;
}

.login__foot p {
  margin: 0;
}
</style>
