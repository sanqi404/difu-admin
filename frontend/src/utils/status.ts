export interface StatusStyle {
  color: string
  bg: string
  border: string
  desc: string
}

/** 十五种冥府状态 → 色标（幽冥国风配色：朱砂 / 鎏金 / 磷火青 / 纸灰白） */
const STATUS_STYLES: Record<string, StatusStyle> = {
  在册: { color: '#cfc8b8', bg: 'rgba(232,227,214,0.08)', border: 'rgba(232,227,214,0.28)', desc: '阳寿已尽，待勾魂' },
  已勾魂: { color: '#d7bd6a', bg: 'rgba(201,162,39,0.12)', border: 'rgba(201,162,39,0.4)', desc: '无常已至，魂已拘回' },
  已备案: { color: '#c9a227', bg: 'rgba(201,162,39,0.16)', border: 'rgba(201,162,39,0.5)', desc: '城隍签押，路引已备' },
  已过境: { color: '#9adfd0', bg: 'rgba(76,224,195,0.1)', border: 'rgba(76,224,195,0.35)', desc: '鬼门关验引通过' },
  待审: { color: '#e0b86a', bg: 'rgba(224,184,106,0.12)', border: 'rgba(224,184,106,0.42)', desc: '迷魂殿录供毕，待开堂' },
  审判中: { color: '#e0725f', bg: 'rgba(179,38,30,0.18)', border: 'rgba(224,114,95,0.5)', desc: '十殿会审进行中' },
  已定罪: { color: '#d4553f', bg: 'rgba(179,38,30,0.26)', border: 'rgba(212,85,63,0.62)', desc: '罪业判定，待交付刑期' },
  服刑中: { color: '#cf7a48', bg: 'rgba(207,122,72,0.16)', border: 'rgba(207,122,72,0.48)', desc: '十八层地狱服刑' },
  刑满: { color: '#c9a227', bg: 'rgba(201,162,39,0.18)', border: 'rgba(201,162,39,0.55)', desc: '刑期已满，待转轮回' },
  待投胎: { color: '#4ce0c3', bg: 'rgba(76,224,195,0.14)', border: 'rgba(76,224,195,0.45)', desc: '六道已定，待饮孟婆汤' },
  已投胎: { color: '#7fd6a8', bg: 'rgba(127,214,168,0.12)', border: 'rgba(127,214,168,0.4)', desc: '已入轮回' },
  枉死城: { color: '#a793c9', bg: 'rgba(167,147,201,0.14)', border: 'rgba(167,147,201,0.42)', desc: '押入枉死城待勘' },
  还阳: { color: '#79c5e8', bg: 'rgba(121,197,232,0.12)', border: 'rgba(121,197,232,0.4)', desc: '判令还阳续命' },
  异常冻结: { color: '#8fa3b8', bg: 'rgba(143,163,184,0.14)', border: 'rgba(143,163,184,0.42)', desc: '卷宗封存，禁止流转' },
  已注销: { color: '#6b665c', bg: 'rgba(107,102,92,0.14)', border: 'rgba(107,102,92,0.4)', desc: '魂飞魄散，档案注销' },
}

export function statusStyle(status?: string | null): StatusStyle {
  return STATUS_STYLES[status || ''] || {
    color: '#a9a294',
    bg: 'rgba(169,162,148,0.1)',
    border: 'rgba(169,162,148,0.32)',
    desc: '',
  }
}

export function karmaStyle(score: number): { color: string; label: string } {
  if (score >= 60) return { color: '#4ce0c3', label: '善业深重' }
  if (score >= 20) return { color: '#7fd6a8', label: '小善' }
  if (score > -20) return { color: '#c9a227', label: '功过相抵' }
  if (score > -60) return { color: '#e0b86a', label: '有孽' }
  return { color: '#d4553f', label: '孽障深重' }
}

export function formatDateTime(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function formatDate(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
