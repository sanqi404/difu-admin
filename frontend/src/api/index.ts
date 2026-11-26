import http from './http'
import type {
  AuditLogItem,
  AuditStatistics,
  CaptchaData,
  CityGodNode,
  DocumentItem,
  KarmaRecord,
  KarmaScoreResult,
  KarmaSummary,
  LifeBookRecord,
  LifeBookSummary,
  LoginResult,
  MenuNode,
  OfficerItem,
  OfficerRecord,
  OverviewData,
  PageData,
  PermissionGroupResult,
  PermissionResult,
  Profile,
  PunishmentRecord,
  PunishmentSummary,
  ReincarnationRecord,
  ReincarnationSummary,
  RoleItem,
  SoulItem,
  SoulTimeline,
  StatusOptions,
  SummonOrderRecord,
  SummonSummary,
  TrendData,
  TrialRecord,
  TrialSummary,
} from './types'

/* ---------------- 认证 ---------------- */
export const fetchCaptcha = () => http.get<CaptchaData>('/auth/captcha')

export const login = (payload: {
  username: string
  password: string
  captcha_id: string
  captcha_code: string
}) => http.post<LoginResult>('/auth/login', payload)

export const logout = () => http.post<null>('/auth/logout')

export const fetchProfile = () => http.get<Profile>('/auth/profile')

export const fetchPermissions = () => http.get<PermissionResult>('/auth/permissions')

export const fetchMenus = () => http.get<{ items: MenuNode[]; total: number }>('/auth/menus')

/* ---------------- 统计 ---------------- */
export const fetchOverview = () => http.get<OverviewData>('/stats/overview')

export const fetchTrend = (days = 30) => http.get<TrendData>('/stats/trend', { params: { days } })

/* ---------------- 亡魂 ---------------- */
export const fetchSouls = (params: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  region?: string
}) => http.get<PageData<SoulItem>>('/souls', { params })

export const fetchSoul = (id: number) => http.get<SoulItem>(`/souls/${id}`)

export const fetchSoulTimeline = (id: number) => http.get<SoulTimeline>(`/souls/${id}/timeline`)

export const fetchSoulStatusOptions = () => http.get<StatusOptions>('/souls/status-options')

export const transitionSoul = (
  id: number,
  payload: { action: string; reason?: string; remark?: string },
) => http.post<SoulItem>(`/souls/${id}/transition`, payload)

/* ---------------- 阴律日志 ---------------- */
export const fetchAuditLogs = (params: {
  page?: number
  page_size?: number
  level?: string
  module?: string
  action?: string
  keyword?: string
  officer_id?: number
  start?: string
  end?: string
}) => http.get<PageData<AuditLogItem>>('/audit-logs', { params })

/* ---------------- 阴律司 · 生死簿 ---------------- */
export interface LifeBookQuery {
  keyword?: string
  review_status?: string
  action?: string
  region?: string
  is_tampered?: number
  page?: number
  page_size?: number
}

export const fetchLifeBooks = (params: LifeBookQuery) =>
  http.get<PageData<LifeBookRecord>>('/life-books', { params })

export const fetchLifeBookSummary = () => http.get<LifeBookSummary>('/life-books/summary')

export const fetchLifeBook = (id: number) => http.get<LifeBookRecord>(`/life-books/${id}`)

export const createLifeBook = (payload: {
  soul_id?: number | null
  soul_name: string
  action: string
  lifespan_years: number
  before_content?: string
  after_content?: string
  diff_desc?: string
}) => http.post<LifeBookRecord>('/life-books', payload)

export const updateLifeBook = (
  id: number,
  payload: { lifespan_years?: number; after_content?: string; diff_desc?: string },
) => http.put<LifeBookRecord>(`/life-books/${id}`, payload)

export const reviewLifeBook = (id: number, comment: string) =>
  http.post<LifeBookRecord>(`/life-books/${id}/review`, { comment })

export const rejectLifeBook = (id: number, comment: string) =>
  http.post<LifeBookRecord>(`/life-books/${id}/reject`, { comment })

/* ---------------- 拘魂司 · 勾魂工单 ---------------- */
export interface SummonQuery {
  keyword?: string
  status?: string
  priority?: string
  region?: string
  assignee_id?: number
  page?: number
  page_size?: number
}

export const fetchSummonOrders = (params: SummonQuery) =>
  http.get<PageData<SummonOrderRecord>>('/summon-orders', { params })

export const fetchSummonSummary = () => http.get<SummonSummary>('/summon-orders/summary')

export const fetchSummonOrder = (id: number) =>
  http.get<SummonOrderRecord>(`/summon-orders/${id}`)

export const createSummonOrder = (payload: {
  soul_id: number
  priority?: string
  deadline_at?: string | null
  location?: string
  death_type?: string
  city_god_id?: number | null
}) => http.post<SummonOrderRecord>('/summon-orders', payload)

export const dispatchSummonOrder = (id: number, assignee_id: number) =>
  http.post<SummonOrderRecord>(`/summon-orders/${id}/dispatch`, { assignee_id })

export const finishSummonOrder = (id: number, result: string) =>
  http.post<{ order: SummonOrderRecord }>(`/summon-orders/${id}/finish`, { result })

export const exceptionSummonOrder = (id: number, reason: string) =>
  http.post<SummonOrderRecord>(`/summon-orders/${id}/exception`, { reason })

export const cancelSummonOrder = (id: number) =>
  http.post<SummonOrderRecord>(`/summon-orders/${id}/cancel`)

/* ---------------- 判官司 · 十殿审判 ---------------- */
export interface TrialQuery {
  keyword?: string
  court_level?: number
  status?: string
  verdict?: string
  region?: string
  page?: number
  page_size?: number
}

export const fetchTrials = (params: TrialQuery) =>
  http.get<PageData<TrialRecord>>('/trials', { params })

export const fetchTrialSummary = () => http.get<TrialSummary>('/trials/summary')

export const fetchTrial = (id: number) => http.get<TrialRecord>(`/trials/${id}`)

export const createTrial = (payload: { soul_id: number; court_level?: number; guilt_desc?: string }) =>
  http.post<TrialRecord>('/trials', payload)

export const handleTrial = (id: number) => http.post<TrialRecord>(`/trials/${id}/handle`)

export const verdictTrial = (
  id: number,
  payload: {
    verdict: string
    verdict_detail?: string
    sentence_years?: number
    hell_level?: number
    next_court_level?: number
  },
) => http.post<{ trial: TrialRecord; soul_status: string }>(`/trials/${id}/verdict`, payload)

/* ---------------- 鬼差名录 · 孽镜台业力 ---------------- */
export const fetchOfficers = (params: {
  keyword?: string
  role_id?: number
  region?: string
  status?: string
  page?: number
  page_size?: number
}) => http.get<PageData<OfficerItem>>('/officers', { params })

export const fetchKarmaRecords = (params: {
  soul_id?: number
  keyword?: string
  page?: number
  page_size?: number
}) => http.get<PageData<KarmaRecord>>('/karma-records', { params })

/* ---------------- 刑狱司 · 十八层地狱与刑期台账 ---------------- */
export interface PunishmentQuery {
  keyword?: string
  hell_level?: number
  status?: string
  region?: string
  page?: number
  page_size?: number
}

export const fetchPunishments = (params: PunishmentQuery) =>
  http.get<PageData<PunishmentRecord>>('/punishments', { params })

export const fetchPunishmentSummary = () => http.get<PunishmentSummary>('/punishments/summary')

export const fetchPunishment = (id: number) => http.get<PunishmentRecord>(`/punishments/${id}`)

export const executePunishment = (id: number) => http.post<PunishmentRecord>(`/punishments/${id}/execute`)

export const adjustPunishment = (id: number, payload: { reduced_years: number; reason: string }) =>
  http.post<PunishmentRecord>(`/punishments/${id}/adjust`, payload)

export const finishPunishment = (id: number) => http.post<PunishmentRecord>(`/punishments/${id}/finish`)

/* ---------------- 轮回司 · 六道轮回与孟婆汤 ---------------- */
export interface ReincarnationQuery {
  keyword?: string
  status?: string
  path?: string
  region?: string
  page?: number
  page_size?: number
}

export const fetchReincarnations = (params: ReincarnationQuery) =>
  http.get<PageData<ReincarnationRecord>>('/reincarnations', { params })

export const fetchReincarnationSummary = () =>
  http.get<ReincarnationSummary>('/reincarnations/summary')

export const fetchReincarnation = (id: number) =>
  http.get<ReincarnationRecord>(`/reincarnations/${id}`)

export const createReincarnation = (payload: {
  soul_id: number
  path?: string
  target_world?: string
  scheduled_at?: string
  remark?: string
}) => http.post<ReincarnationRecord>('/reincarnations', payload)

export const confirmSoup = (id: number) =>
  http.post<ReincarnationRecord>(`/reincarnations/${id}/soup`)

export const confirmReincarnation = (id: number) =>
  http.post<ReincarnationRecord>(`/reincarnations/${id}/reincarnate`)

export const archiveReincarnation = (id: number) =>
  http.post<ReincarnationRecord>(`/reincarnations/${id}/archive`)

/* ---------------- 赏善罚恶司 · 功德罪业与托梦 ---------------- */
export const fetchKarmaSummary = () => http.get<KarmaSummary>('/karma-records/summary')

export const createKarmaRecord = (payload: {
  soul_id: number
  karma_type?: string
  category?: string
  score?: number
  source?: string
  description?: string
  occurred_at?: string
}) => http.post<KarmaRecord>('/karma-records', payload)

export const scoreKarma = (soul_id: number) =>
  http.post<KarmaScoreResult>('/karma-records/score', { soul_id })

export const fetchSoulKarma = (soulId: number) =>
  http.get<{
    soul?: { id: number; name: string; karma_score: number; sin_level: string }
    items?: KarmaRecord[]
    computed_score?: number
  }>(`/karma-records/soul/${soulId}`)

/* ---------------- 城隍司 · 网点与辖境 ---------------- */
export const fetchCityGods = (params?: {
  keyword?: string
  region?: string
  level?: string
  status?: string
}) => http.get<CityGodNode[]>('/city-gods', { params })

export const fetchCityGod = (id: number) => http.get<CityGodNode>(`/city-gods/${id}`)

export const createCityGod = (payload: {
  code: string
  name: string
  region?: string
  level?: string
  parent_id?: number | null
  city_god_name: string
  address?: string
  contact?: string
  soul_capacity?: number
  status?: string
  remark?: string
}) => http.post<CityGodNode>('/city-gods', payload)

export const updateCityGod = (
  id: number,
  payload: {
    name?: string
    region?: string
    level?: string
    city_god_name?: string
    address?: string
    contact?: string
    soul_capacity?: number
    status?: string
    remark?: string
  },
) => http.put<CityGodNode>(`/city-gods/${id}`, payload)

/* ---------------- 文书司 · 文书台账与验引 ---------------- */
export interface DocumentQuery {
  keyword?: string
  doc_type?: string
  status?: string
  soul_id?: number
  city_god_id?: number
  page?: number
  page_size?: number
}

export const fetchDocuments = (params: DocumentQuery) =>
  http.get<PageData<DocumentItem>>('/documents', { params })

export const fetchDocument = (id: number) => http.get<DocumentItem>(`/documents/${id}`)

export const createDocument = (payload: {
  doc_type: string
  title?: string
  soul_id?: number | null
  summon_order_id?: number | null
  city_god_id?: number | null
  content?: string
}) => http.post<DocumentItem>('/documents', payload)

export const issueDocument = (id: number) => http.post<DocumentItem>(`/documents/${id}/issue`)

export const verifyDocument = (id: number) => http.post<DocumentItem>(`/documents/${id}/verify`)

export const voidDocument = (id: number) => http.post<DocumentItem>(`/documents/${id}/void`)

/* ---------------- 系统管理 · 角色 / 权限点 / 菜单 / 鬼差 / 日志 ---------------- */
export const fetchRoles = () => http.get<RoleItem[]>('/roles')

export const createRole = (payload: {
  code: string
  name: string
  description?: string
  data_scope?: string
  sort?: number
}) => http.post<RoleItem>('/roles', payload)

export const updateRole = (
  id: number,
  payload: { name?: string; description?: string; data_scope?: string; sort?: number; status?: string },
) => http.put<RoleItem>(`/roles/${id}`, payload)

export const assignRolePermissions = (id: number, permission_ids: number[]) =>
  http.post<{ role_id: number; permission_count: number }>(`/roles/${id}/permissions`, { permission_ids })

export const fetchPermissionGroups = (params?: { module?: string; type?: string }) =>
  http.get<PermissionGroupResult>('/permissions', { params })

export const fetchAdminMenus = () => http.get<MenuNode[]>('/menus')

export const createMenu = (payload: {
  parent_id?: number | null
  code: string
  name: string
  path?: string
  component?: string
  icon?: string
  type?: string
  permission_code?: string
  sort?: number
  visible?: boolean
}) => http.post<MenuNode>('/menus', payload)

export const updateMenu = (
  id: number,
  payload: {
    parent_id?: number | null
    name?: string
    path?: string
    component?: string
    icon?: string
    type?: string
    permission_code?: string
    sort?: number
    visible?: boolean
  },
) => http.put<MenuNode>(`/menus/${id}`, payload)

export const fetchOfficer = (id: number) => http.get<OfficerRecord>(`/officers/${id}`)

export const createOfficer = (payload: {
  username: string
  password: string
  real_name: string
  title?: string
  role_id: number
  region?: string
  city_god_id?: number | null
  data_scope?: string
  phone?: string
  email?: string
  status?: string
  remark?: string
}) => http.post<OfficerRecord>('/officers', payload)

export const updateOfficer = (
  id: number,
  payload: {
    real_name?: string
    title?: string
    role_id?: number
    region?: string
    city_god_id?: number | null
    data_scope?: string
    phone?: string
    email?: string
    remark?: string
  },
) => http.put<OfficerRecord>(`/officers/${id}`, payload)

export const resetOfficerPassword = (id: number, new_password: string) =>
  http.post<null>(`/officers/${id}/reset-password`, { new_password })

export const setOfficerStatus = (id: number, status: string) =>
  http.post<OfficerRecord>(`/officers/${id}/status`, { status })

export const fetchAuditStatistics = (params?: { start?: string; end?: string }) =>
  http.get<AuditStatistics>('/audit-logs/statistics', { params })

export const fetchOfficerPage = (params: {
  keyword?: string
  role_id?: number
  region?: string
  status?: string
  city_god_id?: number
  page?: number
  page_size?: number
}) => http.get<PageData<OfficerRecord>>('/officers', { params })
