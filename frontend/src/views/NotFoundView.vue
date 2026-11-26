<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="mv-notfound">
    <div class="mv-notfound__box">
      <p class="mv-notfound__code">黄泉</p>
      <h2 class="mv-title">此处无路</h2>
      <p class="mv-notfound__desc">所寻径路已随阳寿断绝，请回鬼门关另择道而行。</p>
      <button class="mv-seal-btn mv-seal-btn--sm" @click="router.replace('/login')">回 鬼 门 关</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.mv-notfound {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: radial-gradient(700px 400px at 50% 40%, rgba(179, 38, 30, 0.12), transparent 70%), #0b0b10;
}
.mv-notfound__box {
  text-align: center;
  padding: 34px 40px;
  border: 1px solid rgba(201, 162, 39, 0.22);
  background: linear-gradient(180deg, rgba(22, 30, 39, 0.9), rgba(11, 11, 16, 0.96));
}
.mv-notfound__code {
  margin: 0 0 8px;
  font-family: var(--mv-font-title);
  font-size: 44px;
  letter-spacing: 0.3em;
  color: rgba(179, 38, 30, 0.55);
}
.mv-notfound__desc {
  margin: 10px 0 22px;
  font-size: 12px;
  color: var(--mv-paper-dim);
  letter-spacing: 0.1em;
}
</style>
