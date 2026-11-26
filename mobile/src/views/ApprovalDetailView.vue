<script setup lang="ts">
/** 审批详情：单据信息 + payload 键值对比 + 流转时间轴 + 同意/驳回/转办 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast, showToast } from 'vant'

import { approvalsApi, fetchOfficers } from '@/api/mobile'
import type { ApprovalAction, ApprovalItem, OfficerBrief } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { bizTone, formatDateTime, payloadRows, remainTime, statusTone, stepTone } from '@/utils/format'

defineOptions({ name: 'ApprovalDetailView' })

const route = useRoute()
const router = useRouter()
const app = useAppStore()

const detail = ref<ApprovalItem | null>(null)
const loading = ref(false)
const errorText = ref('')
const acting = ref(false)

const rejectVisible = ref(false)
const rejectComment = ref('')
const transferVisible = ref(false)
const transferTo = ref('')
const officers = ref<OfficerBrief[]>([])
const officerLoading = ref(false)

const requestId = computed(() => Number(route.params.id))
const rows = computed(() => payloadRows((detail.value?.payload ?? null) as Record<string, unknown> | null))
const remain = computed(() => remainTime(detail.value?.deadline_at))
const canAction = computed(() => Boolean(detail.value?.can_action))
const isFinal = computed(() => Boolean(detail.value?.is_final))
const steps = computed(() => detail.value?.steps ?? [])

async function load(): Promise<void> {
  if (!requestId.value) {
    errorText.value = '单据编号缺失'
    return
  }
  loading.value = true
  errorText.value = ''
  try {
    detail.value = await approvalsApi.detail(requestId.value)
  } catch {
    errorText.value = '此卷宗调阅失败：可能已被归档，或无权调阅'
  } finally {
    loading.value = false
  }
}

async function act(action: ApprovalAction, comment: string, transfer = 0): Promise<void> {
  if (acting.value) return
  acting.value = true
  try {
    await approvalsApi.act(requestId.value, { action, comment, transfer_to: transfer })
    showSuccessToast(action === 'agree' ? '已落印同意' : action === 'reject' ? '已驳回，卷宗退回' : '已转交他人')
    void app.refreshCounters()
    await load()
  } catch {
    showToast('阴律线路中断，动作未生效')
  } finally {
    acting.value = false
  }
}

async function agree(): Promise<void> {
  await act('agree', '')
}

function openReject(): void {
  rejectComment.value = ''
  rejectVisible.value = true
}

async function confirmReject(): Promise<void> {
  if (!rejectComment.value.trim()) {
    showToast('驳回须写明批注')
    return
  }
  rejectVisible.value = false
  await act('reject', rejectComment.value.trim())
}

async function openTransfer(): Promise<void> {
  transferTo.value = ''
  transferVisible.value = true
  if (officers.value.length) return
  officerLoading.value = true
  try {
    const res = await fetchOfficers({ page: 1, page_size: 20 })
    officers.value = res.items ?? []
  } catch {
    officers.value = []
  } finally {
    officerLoading.value = false
  }
}

async function confirmTransfer(): Promise<void> {
  const target = Number(transferTo.value)
  if (!target || Number.isNaN(target)) {
    showToast('请选择或填写转交对象')
    return
  }
  if (target === detail.value?.applicant_id) {
    showToast('不可转交申请人')
    return
  }
  transferVisible.value = false
  await act('transfer', '', target)
}

function goBack(): void {
  if (window.history.length > 1) router.back()
  else void router.push('/inbox')
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="m-page ad">
    <div class="ad__nav">
      <span class="ad__back" @click="goBack">‹ 返回</span>
      <span class="ad__nav-title">卷宗批阅</span>
      <span class="ad__nav-gap" />
    </div>

    <div v-if="errorText" class="m-empty ad__empty">{{ errorText }}</div>

    <template v-else-if="detail">
      <div class="ad__head m-card">
        <div class="ad__head-top">
          <span class="m-badge" :class="bizTone(detail.biz_type)">{{ detail.biz_type }}</span>
          <span class="m-badge" :class="statusTone(detail.status)">{{ detail.status }}</span>
          <span class="ad__no m-mono">#{{ detail.id }}</span>
        </div>
        <h1 class="ad__title">{{ detail.title }}</h1>
        <p v-if="detail.summary" class="ad__summary">{{ detail.summary }}</p>
        <div class="ad__meta">
          <span>申请：{{ detail.applicant_name || '—' }}</span>
          <span>{{ formatDateTime(detail.created_at) }}</span>
        </div>
        <div class="ad__deadline" :class="remain.overdue ? 'm-fire' : remain.urgent ? 'm-gold' : 'm-muted'">
          {{ remain.none ? '此单无时限' : remain.text }}
        </div>
      </div>

      <div class="m-card ad__block">
        <div class="m-card__head">
          <span class="m-card__title">案由明细</span>
          <span class="m-faint">{{ rows.length }} 项</span>
        </div>
        <div v-if="rows.length" class="m-kv">
          <div v-for="row in rows" :key="row.key" class="m-kv__row">
            <span class="m-kv__key">{{ row.label }}</span>
            <span class="m-kv__val">{{ row.value }}</span>
          </div>
        </div>
        <div v-else class="m-empty">此单无附加明细</div>
      </div>

      <div class="m-card ad__block">
        <div class="m-card__head">
          <span class="m-card__title">流转经过</span>
          <span class="m-faint">{{ steps.length }} 环</span>
        </div>
        <div v-if="steps.length" class="m-timeline">
          <div v-for="step in steps" :key="step.id" class="m-timeline__item" :class="`is-${stepTone(step.action, step.action_label)}`">
            <div class="ad__step-dot" />
            <div class="m-timeline__body">
              <div class="m-timeline__head">
                <span class="ad__step-actor">第 {{ step.step_no }} 环 · {{ step.approver_name || '待指派' }}</span>
                <span class="ad__step-action" :class="`is-${stepTone(step.action, step.action_label)}`">
                  {{ step.action_label || step.action || '待处理' }}
                </span>
              </div>
              <p v-if="step.comment" class="ad__step-comment">批注：{{ step.comment }}</p>
              <p class="ad__step-time m-faint">{{ step.acted_at ? formatDateTime(step.acted_at) : '尚未落笔' }}</p>
            </div>
          </div>
        </div>
        <div v-else class="m-empty">尚未开启流转</div>
      </div>

      <div v-if="isFinal" class="ad__final m-teal">此单已归档，无待办动作</div>

      <div v-if="canAction" class="ad__actions">
        <button class="ad__btn ad__btn--reject" :disabled="acting" @click="openReject">驳回</button>
        <button class="ad__btn ad__btn--transfer" :disabled="acting" @click="openTransfer">转办</button>
        <button class="ad__btn ad__btn--agree" :disabled="acting" @click="agree">
          {{ acting ? '落印中…' : '同意' }}
        </button>
      </div>
    </template>

    <div v-else-if="loading" class="m-empty ad__empty">正在调阅卷宗…</div>

    <van-popup v-model:show="rejectVisible" position="bottom" round class="ad__popup">
      <div class="ad__popup-title">驳回批注</div>
      <van-field
        v-model="rejectComment"
        type="textarea"
        rows="3"
        maxlength="200"
        show-word-limit
        placeholder="须写明驳回缘由，回退申请人"
        class="ad__field"
      />
      <div class="ad__popup-actions">
        <button class="ad__btn ad__btn--reject" @click="rejectVisible = false">取消</button>
        <button class="ad__btn ad__btn--agree" @click="confirmReject">确认驳回</button>
      </div>
    </van-popup>

    <van-popup v-model:show="transferVisible" position="bottom" round class="ad__popup">
      <div class="ad__popup-title">转办他人</div>
      <van-field v-model="transferTo" type="digit" label="审批人ID" placeholder="填鬼差名录中的编号" class="ad__field" />
      <div v-if="officerLoading" class="m-empty">正在调取名录…</div>
      <div v-else-if="officers.length" class="ad__officers">
        <span
          v-for="officer in officers"
          :key="officer.id"
          class="ad__officer"
          :class="{ 'is-picked': String(officer.id) === transferTo }"
          @click="transferTo = String(officer.id)"
        >
          {{ officer.real_name || officer.username }}
          <em class="m-faint">{{ officer.role_name || officer.role_code }}</em>
        </span>
      </div>
      <div v-else class="m-faint ad__officer-tip">名录不可调阅，请手工填写审批人ID</div>
      <div class="ad__popup-actions">
        <button class="ad__btn ad__btn--reject" @click="transferVisible = false">取消</button>
        <button class="ad__btn ad__btn--agree" @click="confirmTransfer">确认转办</button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped lang="scss">
.ad {
  padding-bottom: calc(96px + env(safe-area-inset-bottom));
}

.ad__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 13px;
}

.ad__back {
  color: var(--m-gold);
  cursor: pointer;
}

.ad__nav-title {
  color: var(--m-text-1);
  font-family: var(--m-font-serif, serif);
  letter-spacing: 2px;
}

.ad__nav-gap {
  width: 34px;
}

.ad__empty {
  padding: 40px 0;
}

.ad__head {
  padding: 14px;
}

.ad__head-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ad__no {
  margin-left: auto;
  color: var(--m-text-2);
  font-size: 11px;
}

.ad__title {
  margin: 10px 0 0;
  color: var(--m-text-0);
  font-family: var(--m-font-serif, serif);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.45;
}

.ad__summary {
  margin: 7px 0 0;
  color: var(--m-text-1);
  font-size: 12.5px;
  line-height: 1.6;
}

.ad__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  color: var(--m-text-2);
  font-size: 11.5px;
}

.ad__deadline {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
  font-size: 12px;
}

.ad__block {
  margin-top: 11px;
  padding: 12px 13px;
}

.ad__step-dot {
  flex: 0 0 7px;
  width: 7px;
  height: 7px;
  margin: 6px 10px 0 0;
  border-radius: 50%;
  background: rgba(201, 162, 39, 0.45);
}

.is-done .ad__step-dot {
  background: var(--m-gold);
}

.is-reject .ad__step-dot {
  background: var(--m-fire);
}

.ad__step-actor {
  color: var(--m-text-1);
  font-size: 12.5px;
}

.ad__step-action {
  font-size: 11px;
  color: var(--m-gold);

  &.is-done {
    color: var(--m-teal);
  }

  &.is-reject {
    color: var(--m-fire);
  }

  &.is-idle,
  &.is-active {
    color: var(--m-text-2);
  }
}

.ad__step-comment {
  margin: 5px 0 0;
  color: var(--m-text-1);
  font-size: 12px;
  line-height: 1.6;
}

.ad__step-time {
  margin: 3px 0 0;
  font-size: 11px;
}

.ad__final {
  margin-top: 12px;
  padding: 12px;
  border: 1px dashed rgba(76, 224, 195, 0.35);
  border-radius: 10px;
  font-size: 12.5px;
  text-align: center;
}

.ad__actions {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 20;
  display: flex;
  gap: 9px;
  padding: 11px 14px calc(11px + env(safe-area-inset-bottom));
  border-top: 1px solid rgba(201, 162, 39, 0.18);
  background: rgba(13, 15, 20, 0.96);
  backdrop-filter: blur(8px);
}

.ad__btn {
  flex: 1;
  height: 40px;
  border: 1px solid rgba(201, 162, 39, 0.4);
  border-radius: 9px;
  background: rgba(201, 162, 39, 0.1);
  color: var(--m-gold);
  font-size: 14px;
  letter-spacing: 1px;

  &:disabled {
    opacity: 0.55;
  }
}

.ad__btn--agree {
  border-color: rgba(201, 162, 39, 0.75);
  background: linear-gradient(180deg, rgba(201, 162, 39, 0.32), rgba(201, 162, 39, 0.16));
  color: #f3e3b3;
  font-weight: 600;
}

.ad__btn--reject {
  border-color: rgba(212, 85, 63, 0.45);
  background: rgba(212, 85, 63, 0.12);
  color: #e6a294;
}

.ad__btn--transfer {
  border-color: rgba(76, 224, 195, 0.35);
  background: rgba(76, 224, 195, 0.1);
  color: #9fe3d4;
}

.ad__popup {
  padding: 16px 14px calc(16px + env(safe-area-inset-bottom));
  background: var(--m-ink-1, #14161c);
}

.ad__popup-title {
  margin-bottom: 12px;
  color: var(--m-text-0);
  font-family: var(--m-font-serif, serif);
  font-size: 15px;
  text-align: center;
}

.ad__field {
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.04);
}

.ad__popup-actions {
  display: flex;
  gap: 9px;
  margin-top: 14px;
}

.ad__officers {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  max-height: 34vh;
  margin-top: 10px;
  overflow-y: auto;
}

.ad__officer {
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  color: var(--m-text-1);
  font-size: 12px;

  em {
    margin-left: 4px;
    font-size: 10.5px;
    font-style: normal;
  }

  &.is-picked {
    border-color: rgba(201, 162, 39, 0.6);
    background: rgba(201, 162, 39, 0.14);
    color: var(--m-gold);
  }
}

.ad__officer-tip {
  margin-top: 10px;
  font-size: 11.5px;
}
</style>
