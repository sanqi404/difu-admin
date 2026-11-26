/** 移动端业务接口：审批中心 / 消息中心 / 设备绑定 */
import api from './http'
import type {
  ApprovalActionPayload,
  ApprovalItem,
  ApprovalListQuery,
  ApprovalRules,
  DeviceBindPayload,
  DeviceItem,
  MessageItem,
  OfficerBrief,
  PageResult,
  ReadAllResult,
  SummonOrderItem,
  UnreadCount,
} from './types'

// ---------------------------------------------------------------- 审批中心
export const approvalsApi = {
  /** 审批链规则说明 */
  rules() {
    return api.get<ApprovalRules>('/mobile/approvals/rules')
  },
  /** 审批单列表：scope=todo 待我审批 / mine 我发起 / done 我处理过 */
  list(query: ApprovalListQuery = {}) {
    return api.get<PageResult<ApprovalItem>>('/mobile/approvals', { ...query })
  },
  /** 审批单详情 */
  detail(requestId: number) {
    return api.get<ApprovalItem>(`/mobile/approvals/${requestId}`)
  },
  /** 审批动作：同意 / 驳回 / 转办（返回体以服务端最新单据为准，前端以重新拉取详情为准） */
  act(requestId: number, payload: ApprovalActionPayload) {
    return api.post<unknown>(`/mobile/approvals/${requestId}/action`, payload)
  },
}

// ---------------------------------------------------------------- 消息中心
export interface MessageListQuery {
  is_read?: boolean
  type?: string
  page?: number
  page_size?: number
}

export const messagesApi = {
  /** 消息列表 */
  list(query: MessageListQuery = {}) {
    return api.get<PageResult<MessageItem>>('/mobile/messages', { ...query })
  },
  /** 未读统计（总数 + 按类型/优先级） */
  unreadCount() {
    return api.get<UnreadCount>('/mobile/messages/unread-count')
  },
  /** 单条标记已读 */
  read(messageId: number) {
    return api.post<MessageItem>(`/mobile/messages/${messageId}/read`)
  },
  /** 全部标记已读 */
  readAll() {
    return api.post<ReadAllResult>('/mobile/messages/read-all')
  },
}

// ---------------------------------------------------------------- 设备绑定
export const devicesApi = {
  /** 我的设备列表 */
  list() {
    return api.get<DeviceItem[]>('/mobile/devices')
  },
  /** 绑定/更新设备推送令牌 */
  bind(payload: DeviceBindPayload) {
    return api.post<DeviceItem>('/mobile/devices/bind', payload)
  },
  /** 解绑设备 */
  unbind(deviceId: string) {
    return api.delete<unknown>(`/mobile/devices/${deviceId}`)
  },
}

// ---------------------------------------------------------------- 工作台辅助
/** 拘魂工单列表（工作台"在办工单"统计） */
export function fetchSummonOrders(params: { status?: string; page?: number; page_size?: number } = {}) {
  return api.get<PageResult<SummonOrderItem>>('/summon-orders', { ...params })
}

/**
 * 转办候选人（依赖 officer:view 权限）
 * 无权限时后端返回 403，由调用方降级为手工输入审批人 ID
 */
export function fetchOfficers(params: { keyword?: string; page?: number; page_size?: number } = {}) {
  return api.get<PageResult<OfficerBrief>>('/officers', { ...params })
}

export default {
  approvals: approvalsApi,
  messages: messagesApi,
  devices: devicesApi,
}
