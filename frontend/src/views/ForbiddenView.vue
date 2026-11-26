<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
</script>

<template>
  <div class="mv-page">
    <div class="mv-panel mv-forbid">
      <div class="mv-forbid__seal">禁</div>
      <h2 class="mv-title">阴律闭门</h2>
      <p class="mv-forbid__desc">
        足下会籍为「{{ auth.roleName }}」，未列此司名册，卷宗不得启阅。<br />
        若确需办案，请转呈上级鬼帝或大帝加注权限。
      </p>
      <div class="mv-forbid__btns">
        <button class="mv-seal-btn mv-seal-btn--sm" @click="router.back()">退回原司</button>
        <button class="mv-ghost-btn" @click="router.replace('/dashboard')">回酆都城舆图</button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.mv-forbid {
  max-width: 520px;
  margin: 60px auto;
  padding: 34px 30px;
  text-align: center;
}
.mv-forbid__seal {
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  display: grid;
  place-items: center;
  font-family: var(--mv-font-title);
  font-size: 22px;
  color: #f6ece0;
  background: linear-gradient(160deg, #c8382d, #8b1712);
  border: 1px solid rgba(201, 162, 39, 0.6);
  box-shadow: 0 0 20px rgba(179, 38, 30, 0.45);
}
.mv-forbid__desc {
  margin: 12px 0 20px;
  font-size: 12px;
  line-height: 1.9;
  color: var(--mv-paper-dim);
  letter-spacing: 0.06em;
}
.mv-forbid__btns {
  display: flex;
  justify-content: center;
  gap: 10px;
}
</style>
