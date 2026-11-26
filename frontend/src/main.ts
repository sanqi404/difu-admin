import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import '@/styles/theme.scss'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// 菜单 icon 由后端下发字符串，需要全量注册方可 <component :is="name" />
for (const [key, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, comp)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn, size: 'default', zIndex: 3000 })

app.mount('#app')
