<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => (route.meta.title as string) || '此页')
</script>

<template>
  <div class="mv-page">
    <div class="mv-panel mv-hold">
      <div class="mv-hold__seal">待</div>
      <h2 class="mv-title">{{ title }}</h2>
      <p class="mv-hold__desc">
        此殿尚在营造，卷宗已备、梁柱未漆。首批交付聚焦「酆都城舆图」与「亡魂台账」两条主线，
        余下诸司将按批次依次开门理案。
      </p>
      <div class="mv-divider" />
      <div class="mv-hold__grid">
        <div class="mv-hold__cell">
          <span class="mv-hold__cell-label">当前路由</span>
          <span class="mv-hold__cell-value">{{ route.path }}</span>
        </div>
        <div class="mv-hold__cell">
          <span class="mv-hold__cell-label">所需权限</span>
          <span class="mv-hold__cell-value">{{ (route.meta.perm as string) || '登录即可' }}</span>
        </div>
        <div class="mv-hold__cell">
          <span class="mv-hold__cell-label">菜单标识</span>
          <span class="mv-hold__cell-value">{{ (route.meta.menu as string) || '—' }}</span>
        </div>
      </div>
      <router-link to="/soul/list" class="mv-hold__link">先去亡魂主档 <span>→</span></router-link>
    </div>
  </div>
</template>

<style scoped lang="scss">
.mv-hold {
  max-width: 640px;
  margin: 40px auto;
  text-align: center;
  padding: 34px 30px 30px;
}
.mv-hold__seal {
  width: 54px;
  height: 54px;
  margin: 0 auto 16px;
  display: grid;
  place-items: center;
  font-family: var(--mv-font-title);
  font-size: 24px;
  color: #f6ece0;
  background: linear-gradient(160deg, #c8382d, #8b1712);
  border: 1px solid rgba(201, 162, 39, 0.6);
  box-shadow: 0 0 20px rgba(179, 38, 30, 0.45);
}
.mv-hold h2 {
  font-size: 22px;
}
.mv-hold__desc {
  margin: 10px auto 0;
  max-width: 460px;
  font-size: 12px;
  line-height: 1.9;
  letter-spacing: 0.08em;
  color: var(--mv-paper-dim);
}
.mv-hold__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 6px;
}
.mv-hold__cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  background: rgba(201, 162, 39, 0.04);
  border: 1px solid rgba(201, 162, 39, 0.16);
}
.mv-hold__cell-label {
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--mv-muted);
}
.mv-hold__cell-value {
  font-size: 12px;
  color: var(--mv-gold);
  word-break: break-all;
}
.mv-hold__link {
  display: inline-block;
  margin-top: 22px;
  font-family: var(--mv-font-title);
  font-size: 13px;
  letter-spacing: 0.18em;
  color: var(--mv-phosphor);
  text-decoration: none;
}
.mv-hold__link:hover {
  text-shadow: 0 0 14px rgba(76, 224, 195, 0.6);
}
</style>
