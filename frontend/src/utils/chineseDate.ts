const DAYS = [
  '初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
  '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
  '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十',
]

const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

/** 生成形如「丙午年 十月初四 · 周一」的阴历日期 */
export function lunarDate(date: Date = new Date()): string {
  try {
    const fmt = new Intl.DateTimeFormat('zh-CN-u-ca-chinese', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
    const parts = fmt.formatToParts(date)
    const pick = (type: string) => parts.find((p) => p.type === type)?.value || ''
    const yearPart = pick('year')
    const monthPart = pick('month')
    const dayNum = Number(pick('day'))
    const dayPart = Number.isFinite(dayNum) && dayNum >= 1 && dayNum <= 30 ? DAYS[dayNum - 1] : pick('day')
    return `${yearPart} ${monthPart}${dayPart} · ${WEEK[date.getDay()]}`
  } catch {
    return `${date.getFullYear()} 年 ${date.getMonth() + 1} 月 ${date.getDate()} 日`
  }
}

export function clockText(date: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}
