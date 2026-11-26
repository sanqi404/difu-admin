export interface Profile {
  id: number
  username: string
  real_name: string
  title: string
  role_id: number
  role_code: string
  role_name: string
  region: string
  city_god_id: number | null
  data_scope: string
  avatar: string
  status: string
  permissions: string[]
  is_super: boolean
  last_login_at: string | null
}

export interface CaptchaData {
  captcha_id: string
  image: string
  expires_in: number
}

export interface LoginResult {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  profile: Profile
}

export interface PermissionResult {
  is_super: boolean
  data_scope: string
  codes: string[]
}

export interface MenuNode {
  id: number
  parent_id: number | null
  code: string
  name: string
  path: string
  component: string | null
  icon: string | null
  type: string
  permission_code: string
  sort: number
  visible: boolean
  status: string
  children?: MenuNode[]
}

export interface PageMeta {
  total: number
  page: number
  page_size: number
  pages: number
}

export interface PageData<T> {
  items: T[]
  meta: PageMeta
}

export interface AllowedAction {
  action: string
  name: string
  to: string
}

export interface SoulItem {
  id: number
  soul_no: string
  name: string
  gender: string
  age: number
  birth_date: string | null
  death_date: string | null
  native_place: string
  region: string
  status: string
  prev_status: string
  karma_score: number
  sin_level: string
  death_type: string
  life_book_no: string
  city_god_id: number | null
  summon_order_id: number | null
  current_location: string
  is_deleted: boolean
  remark: string
  created_at: string
  updated_at: string
  allowed_actions?: AllowedAction[]
}

export interface LifeBookRecord {
  id: number
  book_no: string
  soul_id: number
  soul_name: string
  action: string
  lifespan_years: number
  before_content: string
  after_content: string
  diff_desc: string
  review_status: string
  operator_name: string
  reviewer_name: string
  reviewed_at: string | null
  review_comment: string
  is_tampered?: number
  created_at?: string
}

export interface SummonOrderRecord {
  id: number
  order_no: string
  soul_id: number
  soul_name: string
  region: string
  city_god_id?: number | null
  assignee_id?: number | null
  assignee_name: string
  priority?: string
  order_status?: string
  status?: string
  death_type?: string
  location?: string
  deadline_at?: string | null
  started_at?: string | null
  finished_at?: string | null
  summon_at?: string | null
  result?: string
  abnormal_reason?: string
  created_at?: string
  remark?: string
}

export interface TrialRecord {
  id: number
  trial_no: string
  soul_id: number
  soul_name: string
  court_level: number
  region: string
  judge_name: string
  karma_snapshot?: number
  guilt_desc?: string
  status?: string
  verdict?: string
  verdict_detail?: string
  sentence_years?: number
  hell_level?: number
  next_court_level?: number
  started_at?: string | null
  closed_at?: string | null
  created_at?: string
  remark?: string
}

export interface KarmaRecord {
  id: number
  karma_no: string
  soul_id: number
  soul_name: string
  region?: string
  karma_type: string
  category: string
  score: number
  source?: string
  occurred_at?: string
  recorder_name?: string
  describ?: string
  description?: string
  created_at?: string
}

export interface PunishmentRecord {
  id: number
  punish_no?: string
  soul_id: number
  soul_name: string
  hell_level?: number
  hell_name?: string
  sentence_years?: number
  reduced_years?: number
  start_at?: string
  end_at?: string
  status?: string
  progress?: number
  region?: string
  executor_name?: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export interface HellCount {
  level: number
  hell: string
  count: number
}

export interface PunishmentSummary {
  total: number
  by_hell: HellCount[]
  by_status: CountByStatus[]
  serving: number
  served: number
}

export interface PathCount {
  path: string
  count: number
}

export interface ReincarnationSummary {
  total: number
  by_path: PathCount[]
  by_status: CountByStatus[]
  soup_pending: number
}

export interface KarmaSummary {
  total: number
  by_type: { type: string; count: number }[]
  by_category: { category: string; count: number }[]
}

export interface KarmaScoreResult {
  soul_id: number
  soul_name: string
  before: { score: number; sin_level: string }
  after: { score: number; sin_level: string }
  record_count: number
}

export interface ReincarnationRecord {
  id: number
  reinc_no?: string
  soul_id: number
  soul_name: string
  path?: string
  target_world?: string
  karma_score?: number
  soup_confirmed?: boolean
  soup_at?: string | null
  soup_operator?: string
  status?: string
  scheduled_at?: string | null
  reincarnated_at?: string | null
  remark?: string
  created_at?: string
}

export interface CountByStatus {
  status: string
  count: number
}

export interface LifeBookSummary {
  total: number
  by_review_status: CountByStatus[]
  pending: number
  tampered: number
}

export interface SummonSummary {
  total: number
  by_status: CountByStatus[]
  finished: number
  running: number
  timeout: number
  abnormal: number
}

export interface TrialSummary {
  total: number
  by_court: { level: number; court: string; count: number }[]
  by_status: CountByStatus[]
  reopened: number
}

export interface OfficerItem {
  id: number
  username: string
  real_name: string
  role_id: number
  role_code?: string
  role_name?: string
  title: string
  region: string
  city_god_id?: number | null
  status: string
  avatar?: string
}

export interface SoulTimeline {
  soul: SoulItem
  life_books: LifeBookRecord[]
  summon_orders: SummonOrderRecord[]
  trials: TrialRecord[]
  punishments: PunishmentRecord[]
  karmas: KarmaRecord[]
  reincarnations: ReincarnationRecord[]
}

export interface StatusOptions {
  statuses: string[]
  final_status: string[]
  actions: { name: string; code: string; from: string[]; to: string }[]
}

export interface OverviewSector {
  total: number
  [key: string]: number | Record<string, number> | unknown
}

export interface OverviewData {
  soul: { total: number; today_new: number; frozen: number; by_status: Record<string, number>; by_region: Record<string, number> }
  summon: { total: number; by_status: Record<string, number> }
  trial: { total: number; pending: number; in_progress: number; closed: number }
  punishment: { total: number; by_status: Record<string, number> }
  reincarnation: { total: number; by_status: Record<string, number> }
  life_book: { total: number; pending_review: number; rejected: number; tampered: number }
  karma: { total: number; good: number; evil: number }
  base: { officer: number; online_officer: number; city_god: number; document: number; audit: number; tamper_audit: number }
}

export interface TrendPoint {
  date: string
  new_soul: number
  summon_order: number
  trial: number
  reincarnation: number
  audit: number
}

export interface TrendData {
  days: number
  series: TrendPoint[]
  total: { new_soul: number; summon_order: number; trial: number; reincarnation: number; audit: number }
}

export interface AuditLogItem {
  id: number
  officer_id: number
  officer_name: string
  role_name: string
  action: string
  module: string
  resource: string
  resource_id: string
  detail: string
  level: string
  ip: string
  user_agent: string
  created_at: string
}

export interface CityGodNode {
  id: number
  code: string
  name: string
  region: string
  level: string
  parent_id: number | null
  city_god_name: string
  address: string
  contact: string
  soul_capacity: number
  soul_count: number
  status: string
  remark: string
  created_at?: string
  updated_at?: string
}

export interface DocumentItem {
  id: number
  doc_no: string
  doc_type: string
  title: string
  soul_id: number | null
  soul_name: string
  summon_order_id: number | null
  city_god_id: number | null
  content: string
  status: string
  issued_by: string
  issued_at: string | null
  verified_by: string
  verified_at: string | null
  created_at?: string
  updated_at?: string
}

/* ---------------- 系统管理 · 角色 / 权限点 / 鬼差账号 ---------------- */
export interface RoleItem {
  id: number
  code: string
  name: string
  description: string
  data_scope: string
  is_builtin: boolean
  sort: number
  status: string
  permissions: string[]
  permission_count: number
}

export interface PermissionItem {
  id: number
  code: string
  name: string
  module: string
  type: string
  description: string
  status: string
}

export interface PermissionGroupResult {
  total: number
  modules: { module: string; items: PermissionItem[] }[]
  flat: PermissionItem[]
}

export interface OfficerRecord {
  id: number
  username: string
  real_name: string
  role_id: number
  role_code?: string
  role_name?: string
  title: string
  region: string
  city_god_id: number | null
  data_scope: string
  phone: string
  email: string
  status: string
  last_login_at: string | null
  login_count: number
  remark: string
  created_at?: string
  updated_at?: string
}

export interface AuditStatistics {
  by_module: { module: string; count: number }[]
  by_level: { level: string; count: number }[]
  top_actions: { action: string; count: number }[]
  tamper_count: number
}
