/** 展示层格式化：时间、剩余时限、业务类型配色、payload 键值展开 */

const pad = (n: number): string => String(n).padStart(2, '0')

/** 后端统一返回 "YYYY-MM-DDTHH:mm:ssZ"（UTC），转为本地时间展示 */
export function toDate(value?: string | null): Date | null {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

/** 2026-11-25 08:30 */
export function formatDateTime(value?: string | null): string {
  const d = toDate(value)
  if (!d) return '—'
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 11-25 08:30 */
export function formatShortTime(value?: string | null): string {
  const d = toDate(value)
  if (!d) return '—'
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 相对时间：刚刚 / 3 分钟前 / 昨天 12:00 */
export function fromNow(value?: string | null): string {
  const d = toDate(value)
  if (!d) return '—'
  const diff = Date.now() - d.getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  if (diff < 172_800_000) return `昨天 ${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)} 天前`
  return formatShortTime(value)
}

export interface RemainInfo {
  /** 倒计时文案，如 "剩 2 小时 12 分" / "已逾期 3 小时" */
  text: string
  /** 是否已逾期 */
  overdue: boolean
  /** 是否进入紧急区间（< 2 小时） */
  urgent: boolean
  /** 是否无时限 */
  none: boolean
}

/** 审批剩余时限 */
export function remainTime(deadline?: string | null): RemainInfo {
  const d = toDate(deadline)
  if (!d) return { text: '无时限', overdue: false, urgent: false, none: true }
  const diff = d.getTime() - Date.now()
  const abs = Math.abs(diff)
  const day = Math.floor(abs / 86_400_000)
  const hour = Math.floor((abs % 86_400_000) / 3_600_000)
  const minute = Math.floor((abs % 3_600_000) / 60_000)
  const span = day > 0 ? `${day} 天 ${hour} 小时` : hour > 0 ? `${hour} 小时 ${minute} 分` : `${minute} 分钟`
  if (diff <= 0) return { text: `已逾期 ${span}`, overdue: true, urgent: true, none: false }
  return { text: `剩 ${span}`, overdue: false, urgent: diff < 7_200_000, none: false }
}

/** 业务类型 → 徽章色 */
export function bizTone(bizType?: string | null): 'gold' | 'teal' | 'fire' | 'warn' | 'plain' {
  switch (bizType) {
    case '生死簿添寿':
    case '添寿':
      return 'teal'
    case '判决改判':
    case '改判':
      return 'warn'
    case '刑罚减免':
      return 'gold'
    case '异常上报':
      return 'fire'
    case '工单取消':
      return 'plain'
    default:
      return 'gold'
  }
}

/** 审批环节 → 时间轴状态（优先后端中文 action_label，回退英文 action） */
export function stepTone(action?: string | null, actionLabel?: string | null): 'done' | 'active' | 'reject' | 'idle' {
  const label = actionLabel || ''
  if (label.includes('驳回') || label.includes('拒绝')) return 'reject'
  if (label.includes('同意') || label.includes('通过') || label.includes('转交') || label.includes('转办')) return 'done'
  if (label.includes('审批中') || label.includes('待') || label.includes('处理中')) return 'active'
  if (label.includes('等待') || label.includes('未开始')) return 'idle'

  switch (action) {
    case 'agree':
    case 'transfer':
      return 'done'
    case 'reject':
      return 'reject'
    case 'wait':
    case 'pending':
      return 'active'
    default:
      return 'idle'
  }
}

/** 状态 → 徽章色 */
export function statusTone(status?: string | null): 'gold' | 'teal' | 'fire' | 'warn' | 'plain' {
  if (!status) return 'plain'
  if (status.includes('通过')) return 'teal'
  if (status.includes('驳回') || status.includes('撤销')) return 'fire'
  if (status.includes('待') || status.startsWith('L')) return 'gold'
  return 'plain'
}

// payload 键名中文映射（后端 payload_json 为业务自定义字典）
const PAYLOAD_LABELS: Record<string, string> = {
  soul_name: '亡魂姓名',
  soul_id: '亡魂编号',
  native_place: '籍贯',
  death_type: '死因',
  lifespan: '阳寿',
  old_lifespan: '原阳寿',
  new_lifespan: '新增阳寿',
  years: '年限',
  add_years: '加寿年数',
  reason: '事由',
  remark: '备注',
  note: '说明',
  verdict: '原判',
  new_verdict: '改判结果',
  sentence: '量刑',
  hell_name: '地狱',
  duration_years: '刑期(年)',
  reduce_years: '减免年数',
  order_no: '工单编号',
  hunter_name: '拘魂使',
  region: '辖区',
  level: '紧急程度',
  abnormal_type: '异常类型',
  description: '描述',
  applicant: '申请人',
}

export interface PayloadRow {
  key: string
  label: string
  value: string
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map((v) => stringifyValue(v)).join('、')
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

/** 把 payload 对象摊平成键值行，键名优先走中文映射 */
export function payloadRows(payload: Record<string, unknown> | null | undefined): PayloadRow[] {
  if (!payload) return []
  return Object.entries(payload).map(([key, value]) => ({
    key,
    label: PAYLOAD_LABELS[key] || key,
    value: stringifyValue(value),
  }))
}
