<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { fetchCaptcha } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const formRef = ref<FormInstance>()
const loading = ref(false)
const captchaLoading = ref(false)
const captchaImg = ref('')
const captchaId = ref('')

const form = reactive({
  username: 'admin',
  password: '123123',
  captcha_code: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请报上名号', trigger: 'blur' }],
  password: [{ required: true, message: '请出示口令', trigger: 'blur' }],
  captcha_code: [{ required: true, message: '请填入路引码', trigger: 'blur' }],
}

const demoAccounts = [
  { name: '酆都大帝', user: 'admin', pwd: '123123' },
  { name: '地藏王', user: 'dizang', pwd: '123456' },
  { name: '东方鬼帝', user: 'guidi_dong', pwd: '123456' },
  { name: '五殿阎罗', user: 'yanluo_05', pwd: '123456' },
  { name: '崔珏', user: 'cuiyu', pwd: '123456' },
  { name: '黑无常', user: 'wuchang_hei', pwd: '123456' },
]

function fillDemo(user: string, pwd: string) {
  form.username = user
  form.password = pwd
  form.captcha_code = '0000'
}

async function loadCaptcha() {
  captchaLoading.value = true
  try {
    const data = await fetchCaptcha()
    captchaId.value = data.captcha_id
    captchaImg.value = data.image?.startsWith('data:') ? data.image : `data:image/png;base64,${data.image}`
    if (!form.captcha_code) form.captcha_code = '0000'
  } catch {
    captchaImg.value = ''
  } finally {
    captchaLoading.value = false
  }
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await auth.signIn({
      username: form.username,
      password: form.password,
      captcha_id: captchaId.value || 'devbypass0000',
      captcha_code: form.captcha_code,
    })
    ElMessage.success('路引已验，鬼门关开门放行')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.replace(redirect)
  } catch {
    form.captcha_code = '0000'
    loadCaptcha()
  } finally {
    loading.value = false
  }
}

/* ---------- 磷火粒子 ---------- */
const canvasRef = ref<HTMLCanvasElement | null>(null)
let rafId = 0
let particles: {
  x: number
  y: number
  r: number
  vy: number
  vx: number
  alpha: number
  hue: 'teal' | 'gold'
  phase: number
}[] = []
let ctx: CanvasRenderingContext2D | null = null

function setupCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const dpr = window.devicePixelRatio || 1
  canvas.width = canvas.clientWidth * dpr
  canvas.height = canvas.clientHeight * dpr
  ctx = canvas.getContext('2d')
  ctx?.scale(dpr, dpr)
  buildParticles()
}

function buildParticles() {
  const canvas = canvasRef.value
  if (!canvas) return
  const count = Math.min(120, Math.round((canvas.clientWidth * canvas.clientHeight) / 12000))
  particles = Array.from({ length: count }, () => ({
    x: Math.random() * canvas.clientWidth,
    y: Math.random() * canvas.clientHeight,
    r: Math.random() * 1.9 + 0.5,
    vy: -(Math.random() * 0.32 + 0.06),
    vx: (Math.random() - 0.5) * 0.18,
    alpha: Math.random() * 0.5 + 0.2,
    hue: Math.random() > 0.84 ? 'gold' : 'teal',
    phase: Math.random() * Math.PI * 2,
  }))
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas || !ctx) return
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  ctx.clearRect(0, 0, w, h)
  const t = performance.now() / 1000
  for (const p of particles) {
    p.y += p.vy
    p.x += p.vx + Math.sin(t + p.phase) * 0.12
    if (p.y < -10) {
      p.y = h + 6
      p.x = Math.random() * w
    }
    if (p.x < -10) p.x = w + 6
    if (p.x > w + 10) p.x = -6

    const flicker = 0.55 + Math.sin(t * 2 + p.phase) * 0.35
    const color = p.hue === 'teal' ? '76,224,195' : '201,162,39'
    const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 7)
    glow.addColorStop(0, `rgba(${color},${p.alpha * flicker})`)
    glow.addColorStop(1, `rgba(${color},0)`)
    ctx.fillStyle = glow
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r * 7, 0, Math.PI * 2)
    ctx.fill()

    ctx.fillStyle = `rgba(${color},${Math.min(0.95, p.alpha * flicker + 0.25)})`
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    ctx.fill()
  }
  rafId = requestAnimationFrame(draw)
}

function onResize() {
  setupCanvas()
}

onMounted(() => {
  setupCanvas()
  rafId = requestAnimationFrame(draw)
  window.addEventListener('resize', onResize)
  loadCaptcha()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  window.removeEventListener('resize', onResize)
})
</script>

<template>
  <div class="mv-login">
    <canvas ref="canvasRef" class="mv-login__embers" />

    <div class="mv-login__left">
      <div class="mv-login__gate">
        <div class="mv-login__plaque">
          <span class="mv-login__plaque-text">鬼门关</span>
        </div>
        <p class="mv-login__poem">
          阳世三间，积善作恶皆由你<br />
          阴曹地府，古往今来放过谁
        </p>
        <div class="mv-login__steps">
          <span>勾魂</span>
          <i />
          <span>备案</span>
          <i />
          <span>验引</span>
          <i />
          <span>录供</span>
          <i />
          <span>审判</span>
          <i />
          <span>轮回</span>
        </div>
      </div>
    </div>

    <div class="mv-login__panel mv-panel">
      <div class="mv-panel__head">
        <div>
          <h2 class="mv-title">过 · 鬼门关</h2>
          <p class="mv-subtitle">地府生死铺 · 幽冥政务后台</p>
        </div>
        <div class="mv-login__seal">酆都</div>
      </div>
      <div class="mv-divider" />

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
        <el-form-item label="名号" prop="username">
          <el-input v-model="form.username" placeholder="鬼差名号" autocomplete="username">
            <template #prefix><el-icon><Avatar /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="口令" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="幽冥口令"
            autocomplete="current-password"
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="路引" prop="captcha_code">
          <div class="mv-login__captcha">
            <el-input v-model="form.captcha_code" maxlength="6" placeholder="路引验证码" />
            <button class="mv-login__captcha-img" type="button" :disabled="captchaLoading" @click="loadCaptcha">
              <img v-if="captchaImg" :src="captchaImg" alt="路引验证码" />
              <span v-else>点击取引</span>
            </button>
          </div>
        </el-form-item>

        <p class="mv-login__tip">dev 环境验证码可直填 0000；点验证码图可换一张</p>

        <el-button class="mv-seal-btn mv-login__submit" :loading="loading" type="primary" @click="submit">
          验 引 入 关
        </el-button>
      </el-form>

      <div class="mv-divider" />
      <p class="mv-login__demo-label">在册值司（点击试填）</p>
      <div class="mv-login__demo">
        <button
          v-for="acc in demoAccounts"
          :key="acc.user"
          type="button"
          class="mv-login__demo-item"
          @click="fillDemo(acc.user, acc.pwd)"
        >
          <strong>{{ acc.name }}</strong>
          <span>{{ acc.user }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.mv-login {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 70px;
  padding: 40px;
  overflow: hidden;
  background:
    radial-gradient(900px 520px at 18% 18%, rgba(76, 224, 195, 0.08), transparent 70%),
    radial-gradient(760px 460px at 84% 74%, rgba(179, 38, 30, 0.12), transparent 72%),
    #0b0b10;
}
.mv-login__embers {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.mv-login__left {
  position: relative;
  z-index: 1;
  flex: 0 1 440px;
  display: flex;
  justify-content: center;
}
.mv-login__gate {
  text-align: center;
}
.mv-login__plaque {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 26px 46px;
  background: linear-gradient(180deg, #1b2230 0%, #0e131a 100%);
  border: 1px solid rgba(201, 162, 39, 0.45);
  box-shadow:
    inset 0 0 40px rgba(201, 162, 39, 0.08),
    0 16px 44px rgba(0, 0, 0, 0.6);
}
.mv-login__plaque::before,
.mv-login__plaque::after {
  content: "";
  position: absolute;
  width: 16px;
  height: 16px;
  border-color: var(--mv-gold);
}
.mv-login__plaque::before {
  top: -1px;
  left: -1px;
  border-top: 1px solid;
  border-left: 1px solid;
}
.mv-login__plaque::after {
  right: -1px;
  bottom: -1px;
  border-right: 1px solid;
  border-bottom: 1px solid;
}
.mv-login__plaque-text {
  font-family: var(--mv-font-title);
  font-size: 52px;
  letter-spacing: 0.3em;
  text-indent: 0.3em;
  color: #e8e3d6;
  text-shadow:
    0 0 22px rgba(179, 38, 30, 0.55),
    0 0 60px rgba(201, 162, 39, 0.22);
}
.mv-login__poem {
  margin: 26px 0 0;
  font-family: var(--mv-font-title);
  font-size: 13px;
  line-height: 2.1;
  letter-spacing: 0.22em;
  color: var(--mv-paper-dim);
}
.mv-login__steps {
  margin-top: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--mv-font-title);
  font-size: 11px;
  letter-spacing: 0.2em;
  color: rgba(76, 224, 195, 0.75);
}
.mv-login__steps i {
  width: 16px;
  height: 1px;
  background: rgba(201, 162, 39, 0.45);
}

.mv-login__panel {
  position: relative;
  z-index: 1;
  width: 400px;
  flex: 0 0 400px;
  padding: 26px 26px 22px;
  backdrop-filter: blur(3px);
}
.mv-login__seal {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  font-family: var(--mv-font-title);
  font-size: 14px;
  line-height: 1.1;
  color: #f6ece0;
  background: linear-gradient(160deg, #c8382d, #8b1712);
  border: 1px solid rgba(201, 162, 39, 0.65);
  border-radius: 2px;
  box-shadow: 0 0 18px rgba(179, 38, 30, 0.5);
}
.mv-login__captcha {
  display: flex;
  gap: 10px;
  width: 100%;
}
.mv-login__captcha-img {
  width: 132px;
  height: 34px;
  flex: 0 0 132px;
  display: grid;
  place-items: center;
  overflow: hidden;
  cursor: pointer;
  background: rgba(8, 10, 14, 0.75);
  border: 1px solid rgba(201, 162, 39, 0.3);
  border-radius: 2px;
  color: var(--mv-muted);
  font-size: 11px;
}
.mv-login__captcha-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.mv-login__tip {
  margin: -4px 0 16px;
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--mv-muted);
}
.mv-login__submit {
  width: 100%;
  height: 42px;
  font-size: 15px;
}
.mv-login__demo-label {
  margin: 0 0 8px;
  font-family: var(--mv-font-title);
  font-size: 11px;
  letter-spacing: 0.2em;
  color: rgba(201, 162, 39, 0.7);
}
.mv-login__demo {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}
.mv-login__demo-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  text-align: left;
  cursor: pointer;
  background: rgba(201, 162, 39, 0.04);
  border: 1px solid rgba(201, 162, 39, 0.16);
  border-radius: 2px;
  color: var(--mv-paper-dim);
  transition: all 0.16s ease;
}
.mv-login__demo-item:hover {
  border-color: rgba(201, 162, 39, 0.5);
  background: rgba(201, 162, 39, 0.1);
}
.mv-login__demo-item strong {
  font-family: var(--mv-font-title);
  font-size: 12px;
  font-weight: 500;
  color: var(--mv-paper);
  letter-spacing: 0.08em;
}
.mv-login__demo-item span {
  font-size: 10px;
  color: var(--mv-muted);
}

:deep(.el-form-item__label) {
  font-family: var(--mv-font-title);
  letter-spacing: 0.18em;
  color: var(--mv-gold);
  padding-bottom: 4px;
}

@media (max-width: 1000px) {
  .mv-login {
    flex-direction: column;
    gap: 32px;
  }
  .mv-login__left {
    flex: 0 1 auto;
  }
  .mv-login__panel {
    width: min(420px, 92vw);
    flex: 0 0 auto;
  }
}
</style>
