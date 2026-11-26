import { createPinia } from 'pinia'
import Vant from 'vant'
import { createApp } from 'vue'

import 'vant/lib/index.css'
import '@/styles/theme.scss'

import App from '@/App.vue'
import router from '@/router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Vant)

app.mount('#app')
