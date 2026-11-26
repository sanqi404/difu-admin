"""领域常量与状态机定义（亡魂全生命周期）。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ============================================================
# 亡魂状态
# ============================================================
class SoulStatus(str, Enum):
    REGISTERED = "在册"
    SUMMONED = "已勾魂"
    FILED = "已备案"
    CROSSED = "已过境"
    PENDING_TRIAL = "待审"
    IN_TRIAL = "审判中"
    CONVICTED = "已定罪"
    SERVING = "服刑中"
    SERVED = "刑满"
    WAIT_REBIRTH = "待投胎"
    REBIRTHED = "已投胎"
    WRONGFUL_CITY = "枉死城"
    RETURNED_LIFE = "还阳"
    FROZEN = "异常冻结"
    CANCELLED = "已注销"


SOUL_STATUS_LIST: list[str] = [s.value for s in SoulStatus]

# 主流程顺序（用于前端步骤条 / 进度计算）
SOUL_MAIN_FLOW: list[str] = [
    SoulStatus.REGISTERED.value,
    SoulStatus.SUMMONED.value,
    SoulStatus.FILED.value,
    SoulStatus.CROSSED.value,
    SoulStatus.PENDING_TRIAL.value,
    SoulStatus.IN_TRIAL.value,
    SoulStatus.CONVICTED.value,
    SoulStatus.SERVING.value,
    SoulStatus.SERVED.value,
    SoulStatus.WAIT_REBIRTH.value,
    SoulStatus.REBIRTHED.value,
    SoulStatus.CANCELLED.value,
]

# 终态（不可再流转）
SOUL_FINAL_STATUS: set[str] = {SoulStatus.CANCELLED.value}

# 特殊/旁路状态
SOUL_SPECIAL_STATUS: set[str] = {
    SoulStatus.WRONGFUL_CITY.value,
    SoulStatus.RETURNED_LIFE.value,
    SoulStatus.FROZEN.value,
}


@dataclass(frozen=True)
class Transition:
    src: str
    dst: str
    action: str
    action_name: str
    permission: str


# 状态流转白名单：未列出的边一律禁止（禁止跳步 / 回退）
_SOUL_EDGES: list[Transition] = [
    # 勾魂工单链路
    Transition("在册", "已勾魂", "summon", "勾魂", "soul:transfer"),
    Transition("已勾魂", "已备案", "file", "城隍备案签路引", "soul:transfer"),
    Transition("已备案", "已过境", "cross", "鬼门关验引", "soul:transfer"),
    Transition("已过境", "待审", "confess", "迷魂殿录供", "soul:transfer"),
    # 审判链路
    Transition("待审", "审判中", "start_trial", "提审开堂", "soul:transfer"),
    Transition("审判中", "已定罪", "convict", "十殿定罪", "soul:transfer"),
    Transition("审判中", "还阳", "grant_return", "判令还阳", "soul:transfer"),
    Transition("审判中", "待投胎", "acquit_rebirth", "无罪释放转轮回", "soul:transfer"),
    # 刑期链路
    Transition("已定罪", "服刑中", "sentence", "交付刑期执行", "soul:transfer"),
    Transition("已定罪", "待投胎", "waive_punishment", "免刑转轮回", "soul:transfer"),
    Transition("服刑中", "刑满", "serve_out", "刑满释放", "soul:transfer"),
    Transition("服刑中", "枉死城", "to_wrongful", "押入枉死城", "soul:transfer"),
    # 轮回链路
    Transition("刑满", "待投胎", "to_rebirth", "刑满转轮回", "soul:transfer"),
    Transition("待投胎", "已投胎", "reincarnate", "六道投胎", "soul:transfer"),
    Transition("已投胎", "已注销", "archive", "归档注销", "soul:transfer"),
    # 枉死 / 还阳旁路
    Transition("枉死城", "还阳", "wrongful_return", "枉死还阳", "soul:transfer"),
    Transition("枉死城", "待投胎", "wrongful_rebirth", "枉死转轮回", "soul:transfer"),
    Transition("还阳", "已注销", "archive_return", "还阳归档", "soul:transfer"),
    # 误录注销
    Transition("在册", "已注销", "cancel", "误录注销", "soul:delete"),
]

# 异常冻结：可从任意非终态进入，解冻回到冻结前的状态
_FREEZE_EDGE = Transition("*", "异常冻结", "freeze", "异常冻结", "soul:freeze")

SOUL_TRANSITIONS: list[Transition] = _SOUL_EDGES

# {src: {dst: Transition}}
SOUL_EDGE_MAP: dict[str, dict[str, Transition]] = {}
for _t in SOUL_TRANSITIONS:
    SOUL_EDGE_MAP.setdefault(_t.src, {})[_t.dst] = _t

SOUL_ACTIONS: dict[str, Transition] = {t.action: t for t in SOUL_TRANSITIONS}
SOUL_ACTIONS[_FREEZE_EDGE.action] = _FREEZE_EDGE
SOUL_ACTIONS["unfreeze"] = Transition("异常冻结", "*", "unfreeze", "异常解冻", "soul:freeze")


def allowed_next_status(current: str) -> list[dict[str, str]]:
    """给定当前状态，返回允许流转到的目标状态与动作。"""
    result: list[dict[str, str]] = []
    if current in SOUL_FINAL_STATUS:
        return result
    for dst, t in SOUL_EDGE_MAP.get(current, {}).items():
        result.append({"status": dst, "action": t.action, "action_name": t.action_name})
    if current != SoulStatus.FROZEN.value:
        result.append(
            {
                "status": SoulStatus.FROZEN.value,
                "action": _FREEZE_EDGE.action,
                "action_name": _FREEZE_EDGE.action_name,
            }
        )
    return result


def resolve_transition(current: str, action: str) -> Transition | None:
    """按动作解析目标状态；返回 None 表示当前状态不允许该动作。"""
    if current in SOUL_FINAL_STATUS:
        return None
    if action == _FREEZE_EDGE.action:
        return None if current == SoulStatus.FROZEN.value else _FREEZE_EDGE
    if action == "unfreeze":
        return SOUL_ACTIONS["unfreeze"] if current == SoulStatus.FROZEN.value else None
    return _find_by_action(current, action)


def _find_by_action(current: str, action: str) -> Transition | None:
    for t in SOUL_EDGE_MAP.get(current, {}).values():
        if t.action == action:
            return t
    return None


# ============================================================
# 业务枚举（一律 String(32) 落库，避免 MySQL ENUM 迁移困难）
# ============================================================
REGIONS: list[str] = ["东方", "南方", "西方", "北方", "中央"]

GENDERS: list[str] = ["男", "女"]

DEATH_TYPES: list[str] = ["寿终正寝", "疾病", "意外", "自尽", "刑戮", "战乱", "溺水", "枉死"]

SIN_LEVELS: list[str] = ["无", "轻", "中", "重", "极重"]

SUMMON_STATUS: list[str] = ["待派发", "执行中", "已完成", "已超时", "异常"]

SUMMON_PRIORITY: list[str] = ["普通", "加急", "特急"]

LIFE_BOOK_ACTIONS: list[str] = ["录入", "修改", "复核", "驳回", "注销"]

LIFE_BOOK_REVIEW: list[str] = ["待复核", "已复核", "已驳回"]

TRIAL_STATUS: list[str] = ["待审", "审理中", "已结案", "打回重审"]

VERDICTS: list[str] = ["有罪", "无罪", "打回重审", "还阳", "发配枉死城"]

PUNISH_STATUS: list[str] = ["待执行", "服刑中", "已刑满", "已转出", "已减免"]

REINCARNATION_STATUS: list[str] = ["待办理", "待投胎", "已投胎", "已归档", "已撤销"]

REINCARNATION_PATHS: list[str] = ["天道", "人道", "阿修罗道", "畜生道", "饿鬼道", "地狱道"]

HELL_NAMES: list[str] = [
    "拔舌地狱", "剪刀地狱", "铁树地狱", "孽镜地狱", "蒸笼地狱", "铜柱地狱",
    "刀山地狱", "冰山地狱", "油锅地狱", "牛坑地狱", "石压地狱", "舂臼地狱",
    "血池地狱", "枉死地狱", "磔刑地狱", "火山地狱", "石磨地狱", "刀锯地狱",
]

KARMA_TYPES: list[str] = ["善", "恶", "中性"]
KARMA_CATEGORIES: list[str] = [
    "杀生", "偷盗", "邪淫", "妄语", "两舌", "恶口", "绮语", "贪欲", "嗔恚", "邪见",
    "布施", "持戒", "放生", "孝养", "救人", "修桥补路",
]
KARMA_SOURCES: list[str] = ["孽镜台", "城隍上报", "生死簿核定", "人工录入"]

DOC_TYPES: list[str] = ["路引", "拘票", "判决书", "轮回文书", "还阳令", "冻结令"]
DOC_STATUS: list[str] = ["草稿", "已签发", "已核验", "已作废"]

OFFICER_STATUS: list[str] = ["在职", "停用", "冻结"]

AUDIT_LEVELS: list[str] = ["正常", "告警", "篡改告警"]

CITY_GOD_LEVELS: list[str] = ["都城隍", "府城隍", "州城隍", "县城隍"]


class DataScope(str, Enum):
    """数据域（RBAC 第 4 级）：按鬼域隔离。"""

    ALL = "ALL"
    REGION = "REGION"
    SELF = "SELF"


# ============================================================
# 角色定义（10 类）
# ============================================================
@dataclass(frozen=True)
class RoleDef:
    code: str
    name: str
    description: str
    data_scope: str


ROLE_DEFS: list[RoleDef] = [
    RoleDef("SUPER_ADMIN", "酆都大帝", "阴曹地府最高主宰，拥有全部菜单、按钮、接口与全鬼域数据", DataScope.ALL.value),
    RoleDef("AUDITOR", "地藏王", "幽冥教主，审计只读：可查全部阴律日志与业务台账，不可增删改", DataScope.ALL.value),
    RoleDef("REGION_ADMIN", "五方鬼帝", "大区管理员，管理本鬼域全部网点与亡魂业务", DataScope.REGION.value),
    RoleDef("JUDGE", "十殿阎罗", "十殿审判官，负责本域 1~10 殿多级审判与定罪", DataScope.REGION.value),
    RoleDef("LIFEBOOK_ADMIN", "崔珏", "生死簿判官，负责阳寿录入、修改与复核", DataScope.ALL.value),
    RoleDef("FIELD_OFFICER", "黑白无常", "外勤拘魂执行员，按勾魂工单执行勾魂", DataScope.SELF.value),
    RoleDef("ESCORT", "牛头马面", "押解鬼差，负责过境押送与鬼门关值守", DataScope.SELF.value),
    RoleDef("BRANCH_ADMIN", "城隍", "分支网点管理员，负责亡魂备案、路引签发与网点台账", DataScope.REGION.value),
    RoleDef("REINCARNATION_OFFICER", "孟婆", "轮回办理员，负责孟婆汤确认与六道投胎办理", DataScope.ALL.value),
    RoleDef("REGISTRAR", "迷魂殿录供官", "负责迷魂殿录供与孽镜台业力评分", DataScope.REGION.value),
]

SUPER_ADMIN_ROLE = "SUPER_ADMIN"
AUDITOR_ROLE = "AUDITOR"


# ============================================================
# 权限点（接口 + 按钮两级共用一张 permission 表）
# ============================================================
@dataclass(frozen=True)
class PermDef:
    code: str
    name: str
    module: str
    type: str  # api / button
    method: str = ""
    path: str = ""


def _p(code: str, name: str, module: str, ptype: str = "api", method: str = "", path: str = "") -> PermDef:
    return PermDef(code, name, module, ptype, method, path)


PERMISSION_DEFS: list[PermDef] = [
    # 认证 / 个人
    _p("auth:profile", "查看个人资料", "auth"),
    # 亡魂
    _p("soul:view", "查看亡魂", "soul", "api", "GET", "/souls"),
    _p("soul:create", "新增亡魂", "soul", "button", "POST", "/souls"),
    _p("soul:update", "编辑亡魂", "soul", "button", "PUT", "/souls/{id}"),
    _p("soul:delete", "注销亡魂", "soul", "button", "DELETE", "/souls/{id}"),
    _p("soul:transfer", "亡魂状态流转", "soul", "button", "POST", "/souls/{id}/transition"),
    _p("soul:freeze", "异常冻结/解冻", "soul", "button", "POST", "/souls/{id}/freeze"),
    _p("soul:export", "导出亡魂台账", "soul", "button", "GET", "/souls/export"),
    # 生死簿
    _p("lifebook:view", "查看生死簿", "life_book", "api", "GET", "/life-books"),
    _p("lifebook:create", "生死簿录入", "life_book", "button", "POST", "/life-books"),
    _p("lifebook:update", "生死簿修改", "life_book", "button", "PUT", "/life-books/{id}"),
    _p("lifebook:review", "生死簿复核", "life_book", "button", "POST", "/life-books/{id}/review"),
    _p("lifebook:reject", "生死簿驳回", "life_book", "button", "POST", "/life-books/{id}/reject"),
    # 拘魂工单
    _p("summon:view", "查看拘魂工单", "summon", "api", "GET", "/summon-orders"),
    _p("summon:create", "创建拘魂工单", "summon", "button", "POST", "/summon-orders"),
    _p("summon:dispatch", "派发工单", "summon", "button", "POST", "/summon-orders/{id}/dispatch"),
    _p("summon:execute", "执行勾魂", "summon", "button", "POST", "/summon-orders/{id}/execute"),
    _p("summon:finish", "完成工单", "summon", "button", "POST", "/summon-orders/{id}/finish"),
    _p("summon:exception", "工单异常登记", "summon", "button", "POST", "/summon-orders/{id}/exception"),
    # 审判
    _p("trial:view", "查看审判记录", "trial", "api", "GET", "/trials"),
    _p("trial:create", "立案送审", "trial", "button", "POST", "/trials"),
    _p("trial:handle", "开庭审理", "trial", "button", "POST", "/trials/{id}/handle"),
    _p("trial:verdict", "宣读判决", "trial", "button", "POST", "/trials/{id}/verdict"),
    _p("trial:return", "打回重审", "trial", "button", "POST", "/trials/{id}/return"),
    # 刑期
    _p("punishment:view", "查看刑期台账", "punishment", "api", "GET", "/punishments"),
    _p("punishment:execute", "刑期执行", "punishment", "button", "POST", "/punishments/{id}/execute"),
    _p("punishment:adjust", "刑期减免/调整", "punishment", "button", "POST", "/punishments/{id}/adjust"),
    # 轮回
    _p("reincarnation:view", "查看轮回档案", "reincarnation", "api", "GET", "/reincarnations"),
    _p("reincarnation:create", "轮回立案", "reincarnation", "button", "POST", "/reincarnations"),
    _p("reincarnation:soup", "孟婆汤确认", "reincarnation", "button", "POST", "/reincarnations/{id}/soup"),
    _p("reincarnation:confirm", "投胎确认", "reincarnation", "button", "POST", "/reincarnations/{id}/reincarnate"),
    # 业力
    _p("karma:view", "查看业力记录", "karma", "api", "GET", "/karma-records"),
    _p("karma:create", "业力录入", "karma", "button", "POST", "/karma-records"),
    _p("karma:score", "孽镜台评分", "karma", "button", "POST", "/karma-records/score"),
    # 鬼差
    _p("officer:view", "查看鬼差账号", "officer", "api", "GET", "/officers"),
    _p("officer:create", "新增鬼差", "officer", "button", "POST", "/officers"),
    _p("officer:update", "编辑鬼差", "officer", "button", "PUT", "/officers/{id}"),
    _p("officer:reset", "重置密码", "officer", "button", "POST", "/officers/{id}/reset-password"),
    _p("officer:status", "启停用鬼差", "officer", "button", "POST", "/officers/{id}/status"),
    # 角色 / 菜单 / 权限
    _p("role:view", "查看角色", "role", "api", "GET", "/roles"),
    _p("role:create", "新增角色", "role", "button", "POST", "/roles"),
    _p("role:update", "编辑角色", "role", "button", "PUT", "/roles/{id}"),
    _p("role:assign", "角色授权", "role", "button", "POST", "/roles/{id}/permissions"),
    _p("menu:view", "查看菜单", "menu", "api", "GET", "/menus"),
    _p("menu:create", "新增菜单", "menu", "button", "POST", "/menus"),
    _p("menu:update", "编辑菜单", "menu", "button", "PUT", "/menus/{id}"),
    _p("permission:view", "查看权限点", "permission", "api", "GET", "/permissions"),
    # 城隍网点
    _p("citygod:view", "查看城隍网点", "city_god", "api", "GET", "/city-gods"),
    _p("citygod:create", "新增网点", "city_god", "button", "POST", "/city-gods"),
    _p("citygod:update", "编辑网点", "city_god", "button", "PUT", "/city-gods/{id}"),
    # 文书
    _p("doc:view", "查看文书", "document", "api", "GET", "/documents"),
    _p("doc:issue", "签发文书", "document", "button", "POST", "/documents/{id}/issue"),
    _p("doc:verify", "核验文书", "document", "button", "POST", "/documents/{id}/verify"),
    _p("doc:void", "作废文书", "document", "button", "POST", "/documents/{id}/void"),
    # 审计
    _p("audit:view", "查看阴律日志", "audit", "api", "GET", "/audit-logs"),
    _p("audit:export", "导出审计日志", "audit", "button", "GET", "/audit-logs/export"),
    # 统计
    _p("stats:view", "查看统计大盘", "stats", "api", "GET", "/stats"),
    _p("stats:export", "导出统计报表", "stats", "button", "GET", "/stats/export"),
]

ALL_PERMISSION_CODES: list[str] = [p.code for p in PERMISSION_DEFS]

# 角色 → 权限（SUPER_ADMIN 由代码层直接放行全部）
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "SUPER_ADMIN": ALL_PERMISSION_CODES,
    "AUDITOR": [
        "auth:profile",
        "soul:view",
        "lifebook:view",
        "summon:view",
        "trial:view",
        "punishment:view",
        "reincarnation:view",
        "karma:view",
        "officer:view",
        "role:view",
        "menu:view",
        "permission:view",
        "citygod:view",
        "doc:view",
        "audit:view",
        "audit:export",
        "stats:view",
        "stats:export",
    ],
    "REGION_ADMIN": [
        "auth:profile",
        "soul:view", "soul:create", "soul:update", "soul:transfer", "soul:freeze", "soul:export",
        "lifebook:view",
        "summon:view", "summon:create", "summon:dispatch", "summon:finish", "summon:exception",
        "trial:view", "trial:create",
        "punishment:view", "punishment:execute",
        "reincarnation:view",
        "karma:view", "karma:create",
        "officer:view",
        "citygod:view", "citygod:create", "citygod:update",
        "doc:view", "doc:issue", "doc:verify",
        "audit:view",
        "stats:view",
    ],
    "JUDGE": [
        "auth:profile",
        "soul:view", "soul:transfer",
        "summon:view",
        "trial:view", "trial:create", "trial:handle", "trial:verdict", "trial:return",
        "punishment:view", "punishment:execute",
        "karma:view", "karma:create", "karma:score",
        "doc:view", "doc:issue",
        "stats:view",
    ],
    "LIFEBOOK_ADMIN": [
        "auth:profile",
        "soul:view", "soul:create", "soul:update", "soul:export",
        "lifebook:view", "lifebook:create", "lifebook:update", "lifebook:review", "lifebook:reject",
        "summon:view",
        "karma:view",
        "doc:view",
        "audit:view",
        "stats:view",
    ],
    "FIELD_OFFICER": [
        "auth:profile",
        "soul:view",
        "summon:view", "summon:execute", "summon:finish", "summon:exception",
        "doc:view",
    ],
    "ESCORT": [
        "auth:profile",
        "soul:view", "soul:transfer",
        "summon:view", "summon:execute",
        "doc:view", "doc:verify",
    ],
    "BRANCH_ADMIN": [
        "auth:profile",
        "soul:view", "soul:create", "soul:update", "soul:transfer", "soul:freeze",
        "lifebook:view",
        "summon:view", "summon:create", "summon:dispatch", "summon:finish",
        "trial:view",
        "punishment:view",
        "reincarnation:view",
        "karma:view", "karma:create",
        "citygod:view", "citygod:update",
        "doc:view", "doc:issue", "doc:verify", "doc:void",
        "stats:view",
    ],
    "REINCARNATION_OFFICER": [
        "auth:profile",
        "soul:view", "soul:transfer",
        "reincarnation:view", "reincarnation:create", "reincarnation:soup", "reincarnation:confirm",
        "punishment:view",
        "karma:view",
        "doc:view", "doc:issue",
        "stats:view",
    ],
    "REGISTRAR": [
        "auth:profile",
        "soul:view", "soul:update", "soul:transfer",
        "karma:view", "karma:create", "karma:score",
        "summon:view",
        "doc:view",
    ],
}


# ============================================================================
# 移动端 H5 审批中心：审批链规则
# ============================================================================

class BizType(str, Enum):
    """移动审批业务类型。"""

    LIFE_EXTEND = "生死簿添寿"
    VERDICT_REVIVE = "判令还阳"
    PUNISH_REDUCE = "减刑赦免"
    ABNORMAL_REPORT = "异常上报"
    ORDER_CANCEL = "工单撤销"


BIZ_TYPE_LIST: list[str] = [b.value for b in BizType]

# 生死簿添寿的层级阈值：≤10 年只需城隍 L1，>10 年由崔珏 L1 上报酆都大帝 L2
LIFE_EXTEND_THRESHOLD_YEARS = 10

# 审批环节动作（approval_step.action）
APPROVAL_STEP_WAIT = "wait"          # 已轮到、待审批
APPROVAL_STEP_LOCKED = "pending"     # 尚未轮到的后续环节
APPROVAL_STEP_AGREE = "agree"
APPROVAL_STEP_REJECT = "reject"
APPROVAL_STEP_TRANSFER = "transfer"
APPROVAL_ACTIONS: list[str] = [APPROVAL_STEP_AGREE, APPROVAL_STEP_REJECT, APPROVAL_STEP_TRANSFER]
APPROVAL_ACTION_LABELS: dict[str, str] = {
    APPROVAL_STEP_WAIT: "待审批",
    APPROVAL_STEP_LOCKED: "未启动",
    APPROVAL_STEP_AGREE: "同意",
    APPROVAL_STEP_REJECT: "驳回",
    APPROVAL_STEP_TRANSFER: "转交",
}

# 审批单终态（approval_request.status）
APPROVAL_STATUS_AGREED = "已通过"
APPROVAL_STATUS_REJECTED = "已驳回"
APPROVAL_STATUS_CANCELLED = "已撤销"
APPROVAL_STATUS_FINAL: list[str] = [
    APPROVAL_STATUS_AGREED,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STATUS_CANCELLED,
]

# 申请单可撤销的状态（尚未有人处理）
APPROVAL_STATUS_OPENABLE: list[str] = []

# 特殊审批人占位：工单撤销的 L1 审批人为「派单人」即申请人本人
APPLICANT_APPROVER = "__APPLICANT__"

# 各业务类型对应的业务查看权限点（移动端跳转与动作鉴权提示）
APPROVAL_BIZ_PERMISSION: dict[str, str] = {
    BizType.LIFE_EXTEND.value: "lifebook:view",
    BizType.VERDICT_REVIVE.value: "trial:view",
    BizType.PUNISH_REDUCE.value: "punishment:view",
    BizType.ABNORMAL_REPORT.value: "summon:view",
    BizType.ORDER_CANCEL.value: "summon:view",
}

# 审批链文字规则（供移动端「审批规则说明」页直接展示）
APPROVAL_CHAIN_RULES: list[dict[str, str]] = [
    {"biz_type": BizType.LIFE_EXTEND.value, "rule": "添寿 ≤10 年：L1 城隍审批，不上报；>10 年：L1 崔珏 → L2 酆都大帝"},
    {"biz_type": BizType.VERDICT_REVIVE.value, "rule": "判令还阳：L1 殿主 → L2 酆都大帝"},
    {"biz_type": BizType.PUNISH_REDUCE.value, "rule": "减刑赦免：L1 殿主 + 监刑官双人会签 → L2 酆都大帝"},
    {"biz_type": BizType.ABNORMAL_REPORT.value, "rule": "异常上报：L1 直属判官审批，不上报"},
    {"biz_type": BizType.ORDER_CANCEL.value, "rule": "工单撤销：L1 派单人审批，不上报"},
]


@dataclass(frozen=True)
class ApprovalApprover:
    """审批链上的一个审批角色位。"""

    role_code: str
    role_name: str
    level: int
    report_upper: bool = False

    @property
    def label(self) -> str:
        return f"L{self.level}-{self.role_name}"


def resolve_approval_chain(biz_type: str, years: int | None = None) -> list[list[ApprovalApprover]]:
    """按业务类型解析审批链。

    返回值为「环节列表」，外层下标即环节顺序，内层为该环节需要会签的审批角色
    （多个角色 = 双人/多人会签，全部同意才推进下一环节）。
    """
    if biz_type == BizType.LIFE_EXTEND.value:
        if years is not None and years <= LIFE_EXTEND_THRESHOLD_YEARS:
            # ≤10 年：城隍 L1 独立审批，不上报
            return [[ApprovalApprover("BRANCH_ADMIN", "城隍", 1, False)]]
        # >10 年：崔珏 L1 上报酆都大帝 L2
        return [
            [ApprovalApprover("LIFEBOOK_ADMIN", "崔珏", 1, True)],
            [ApprovalApprover(SUPER_ADMIN_ROLE, "酆都大帝", 2, False)],
        ]
    if biz_type == BizType.VERDICT_REVIVE.value:
        # 判令还阳：殿主 L1 上报酆都大帝 L2
        return [
            [ApprovalApprover("JUDGE", "殿主", 1, True)],
            [ApprovalApprover(SUPER_ADMIN_ROLE, "酆都大帝", 2, False)],
        ]
    if biz_type == BizType.PUNISH_REDUCE.value:
        # 减刑赦免：殿主 + 监刑官双人会签 L1，再上报酆都大帝 L2
        return [
            [ApprovalApprover("JUDGE", "殿主", 1, True), ApprovalApprover("AUDITOR", "监刑官", 1, True)],
            [ApprovalApprover(SUPER_ADMIN_ROLE, "酆都大帝", 2, False)],
        ]
    if biz_type == BizType.ABNORMAL_REPORT.value:
        # 异常上报：直属判官 L1 审批，不上报
        return [[ApprovalApprover("JUDGE", "直属判官", 1, False)]]
    if biz_type == BizType.ORDER_CANCEL.value:
        # 工单撤销：派单人（即申请人本人）L1 审批，不上报
        return [[ApprovalApprover(APPLICANT_APPROVER, "派单人", 1, False)]]
    raise ValueError(f"未知的审批业务类型：{biz_type}")


def approval_status_label(approvers: list[ApprovalApprover]) -> str:
    """把某一环节的审批角色拼成审批单 status（即 current_step）。"""
    if not approvers:
        return APPROVAL_STATUS_AGREED
    first = approvers[0]
    names = " + ".join(a.role_name for a in approvers)
    return f"L{first.level}-{names}"
