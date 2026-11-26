/** 移动端接口数据类型定义（与后端 app/api/v1 实际返回字段对齐） */

// ---------------- 通用 ----------------
export interface PageMeta {
  page: number
  page_size: number
  total: number
  pages: number
}

export interface PageResult<T> {
  items: T[]
  meta: PageMeta
}

// ---------------- 认证 ----------------
export interface CaptchaData {
  captcha_id: string
  image: string
}

export interface LoginPayload {
  username: string
  password: string
  captcha_id: string
  captcha_code: string
}

export interface LoginResult {
  access_token: string
  refresh_token?: string
  token_type?: string
  expires_in?: number
}

export interface OfficerProfile {
  id: number
  username: string
  real_name: string
  title?: string | null
  role_id?: number | null
  role_code?: string | null
  role_name?: string | null
  region?: string | null
  city_god_id?: number | null
  data_scope?: string | null
  avatar?: string | null
  status?: string | null
  permissions?: string[]
  is_super?: boolean
  last_login_at?: string | null
}

export interface PermissionResult {
  is_super: boolean
  data_scope: string
  codes: string[]
}

// ---------------- 审批 ----------------
export type ApprovalScope = 'todo' | 'mine' | 'done'

export interface ApprovalStepItem {
  id: number
  request_id: number
  step_no: number
  approver_id: number | null
  approver_name: string
  action: string
  action_label: string
  comment?: string | null
  acted_at?: string | null
  created_at?: string | null
}

export type ApprovalPayload = Record<string, unknown> | null

export interface ApprovalItem {
  id: number
  biz_type: string
  biz_id?: number | null
  title: string
  summary?: string | null
  payload_json?: string | null
  payload?: ApprovalPayload
  applicant_id?: number | null
  applicant_name: string
  status: string
  deadline_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  current_step: number
  is_final: boolean
  can_action: boolean
  biz_permission?: string
  steps: ApprovalStepItem[]
}

export interface ApprovalListQuery {
  scope?: ApprovalScope
  biz_type?: string
  keyword?: string
  page?: number
  page_size?: number
}

export type ApprovalAction = 'agree' | 'reject' | 'transfer'

export interface ApprovalActionPayload {
  action: ApprovalAction
  comment?: string
  transfer_to?: number
}

export interface ApprovalRules {
  biz_types: string[]
  rules: Record<string, string[]>
  actions: Record<string, string>
  status_final: string[]
}

// ---------------- 消息 ----------------
export type MessageType = '审批待办' | '审批结果' | '工单派发' | '系统通知' | '紧急通告'
export type MessagePriority = '普通' | '重要' | '紧急'

export interface MessageItem {
  id: number
  receiver_id?: number
  type: MessageType | string
  title: string
  content?: string | null
  biz_ref?: string | null
  is_read: boolean
  priority: MessagePriority | string
  created_at?: string | null
}

export interface UnreadCount {
  unread: number
  by_type: Record<string, number>
  by_priority: Record<string, number>
}

export interface ReadAllResult {
  updated: number
  at?: string | null
}

// ---------------- 设备 ----------------
export interface DeviceItem {
  id: number
  user_id?: number
  device_id: string
  push_token?: string | null
  platform?: string | null
  last_active_at?: string | null
  created_at?: string | null
}

export interface DeviceBindPayload {
  device_id: string
  push_token?: string
  platform?: 'ios' | 'android' | 'h5'
}

// ---------------- 拘魂工单（工作台统计用） ----------------
export interface SummonOrderItem {
  id: number
  order_no?: string | null
  soul_id?: number | null
  status?: string | null
  priority?: string | null
  region?: string | null
  assignee_id?: number | null
  hunter_name?: string | null
  issued_at?: string | null
  created_at?: string | null
}

// ---------------- 人员（转办选人用） ----------------
export interface OfficerBrief {
  id: number
  username: string
  real_name: string
  role_code?: string | null
  role_name?: string | null
  region?: string | null
  status?: string | null
}
