<script setup lang="ts">
import { ref, watch } from 'vue'
import { fetchSouls } from '@/api'
import type { SoulItem } from '@/api/types'

const props = withDefaults(
  defineProps<{
    modelValue?: number | null
    placeholder?: string
    disabled?: boolean
  }>(),
  { modelValue: null, placeholder: '按姓名 / 魂号检索亡魂', disabled: false },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number | null): void
  (e: 'change', soul: SoulItem | null): void
}>()

const loading = ref(false)
const options = ref<SoulItem[]>([])

async function remoteSearch(keyword: string) {
  if (!keyword) {
    options.value = []
    return
  }
  loading.value = true
  try {
    const data = await fetchSouls({ keyword, page: 1, page_size: 20 })
    options.value = data.items || []
  } catch {
    options.value = []
  } finally {
    loading.value = false
  }
}

function onSelect(id: number) {
  emit('update:modelValue', id)
  emit('change', options.value.find((s) => s.id === id) || null)
}

function onClear() {
  emit('update:modelValue', null)
  emit('change', null)
}

watch(
  () => props.modelValue,
  (val) => {
    if (!val) options.value = []
  },
)
</script>

<template>
  <el-select
    :model-value="props.modelValue"
    filterable
    remote
    clearable
    reserve-keyword
    :remote-method="remoteSearch"
    :loading="loading"
    :disabled="props.disabled"
    :placeholder="props.placeholder"
    class="soul-picker"
    @change="onSelect"
    @clear="onClear"
  >
    <el-option v-for="s in options" :key="s.id" :label="`${s.name} · ${s.soul_no}`" :value="s.id">
      <div class="soul-opt">
        <span class="soul-opt__name">{{ s.name }}</span>
        <span class="soul-opt__meta">{{ s.soul_no }} · {{ s.region }} · {{ s.status }}</span>
      </div>
    </el-option>
    <template #empty>
      <div class="soul-empty">键入姓名或魂号以检索</div>
    </template>
  </el-select>
</template>

<style scoped>
.soul-picker {
  width: 100%;
}
.soul-opt {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}
.soul-opt__name {
  color: var(--mv-paper);
}
.soul-opt__meta {
  font-size: 11px;
  color: var(--mv-muted);
  font-family: var(--mv-font-mono, ui-monospace, monospace);
}
.soul-empty {
  padding: 8px 12px;
  color: var(--mv-muted);
  font-size: 12px;
}
</style>
