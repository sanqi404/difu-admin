"""种子数据脚本：基础数据（起项目必需）+ 可选业务示例数据。

用法：
    python -m app.seed                # 建表 + 只灌基础数据（RBAC/网点/账号，幂等）
    python -m app.seed --with-demo    # 基础数据 + 业务示例数据（演示看效果用）
    python -m app.seed --force        # 先清空全库再按上述规则重灌
    python -m app.seed --force --with-demo   # 清库后灌「基础 + 业务示例」

说明：
    - 基础数据与 sql/03_base_data.sql 口径一致；业务示例数据与 sql/04_test_data.sql 口径一致。
    - 不传 --force 时，已存在的数据不会重复写入（按表分别判断）。
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import (
    APPLICANT_APPROVER,
    APPROVAL_STATUS_AGREED,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STEP_AGREE,
    APPROVAL_STEP_LOCKED,
    APPROVAL_STEP_REJECT,
    APPROVAL_STEP_WAIT,
    DEATH_TYPES,
    GENDERS,
    HELL_NAMES,
    KARMA_CATEGORIES,
    KARMA_SOURCES,
    KARMA_TYPES,
    PERMISSION_DEFS,
    REGIONS,
    REINCARNATION_PATHS,
    ROLE_DEFS,
    ROLE_PERMISSIONS,
    SUPER_ADMIN_ROLE,
    BizType,
    SoulStatus,
    approval_status_label,
    resolve_approval_chain,
)
from app.core.security import hash_password
from app.database import SessionLocal, init_db, utcnow
from app.models import (
    ApprovalRequest,
    ApprovalStep,
    AuditLog,
    CityGod,
    Document,
    KarmaRecord,
    LifeBook,
    Menu,
    MobileDevice,
    MobileMessage,
    Officer,
    Permission,
    Punishment,
    Reincarnation,
    Role,
    RolePermission,
    Soul,
    SummonOrder,
    TrialRecord,
)
from app.services.state_machine import LOCATION_BY_STATUS

RNG = random.Random(20261123)
NOW = utcnow().replace(microsecond=0)

SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜谢邹喻柏水窦章苏潘葛范彭鲁韦昌马苗凤花方俞任袁柳"
GIVEN_M = ["文远", "伯符", "子敬", "玄德", "仲谋", "元直", "孝直", "公瑾", "伯言", "义山",
           "叔宝", "敬德", "仁杰", "怀英", "处机", "青莲", "少陵", "梦得", "乐天", "退之"]
GIVEN_F = ["婉容", "清照", "太真", "文君", "昭君", "飞燕", "合德", "绿珠", "红拂", "素贞",
           "小青", "念奴", "弄玉", "宓妃", "湘君", "湘夫人", "碧霞", "紫鹃", "晴雯", "香菱"]
NATIVE = ["酆都鬼城", "洛阳", "长安", "金陵", "临安", "汴梁", "成都", "太原", "苏州", "扬州",
          "幽州", "泉州", "襄阳", "荆州", "广州", "杭州"]

# 亡魂状态分布（合计 80，状态全集 15 种全部覆盖）
SOUL_PLAN: list[tuple[str, int]] = [
    (SoulStatus.REGISTERED, 6),
    (SoulStatus.SUMMONED, 6),
    (SoulStatus.FILED, 5),
    (SoulStatus.CROSSED, 5),
    (SoulStatus.PENDING_TRIAL, 8),
    (SoulStatus.IN_TRIAL, 6),
    (SoulStatus.CONVICTED, 6),
    (SoulStatus.SERVING, 10),
    (SoulStatus.SERVED, 8),
    (SoulStatus.WAIT_REBIRTH, 6),
    (SoulStatus.REBIRTHED, 6),
    (SoulStatus.WRONGFUL_CITY, 3),
    (SoulStatus.RETURNED_LIFE, 2),
    (SoulStatus.FROZEN, 2),
    (SoulStatus.CANCELLED, 1),
]

CITY_GOD_SEED = [
    ("CG001", "酆都总城隍府", "中央", "都城隍", None, "酆都大帝敕封", "酆都鬼城阴阳界 1 号", "城隍印·总", 6000),
    ("CG002", "东岳泰山府城隍", "东方", "府城隍", "CG001", "东岳大帝属神", "泰山南麓蒿里山", "城隍印·东", 1200),
    ("CG003", "南岳衡山府城隍", "南方", "府城隍", "CG001", "南岳司天昭圣", "衡山祝融峰下", "城隍印·南", 1000),
    ("CG004", "西岳华山府城隍", "西方", "府城隍", "CG001", "西岳金天顺圣", "华阴云台观", "城隍印·西", 900),
    ("CG005", "北岳恒山府城隍", "北方", "府城隍", "CG001", "北岳安天玄圣", "浑源玄武峰", "城隍印·北", 800),
    ("CG006", "中州州城隍庙", "中央", "州城隍", "CG001", "中州巡察使", "洛阳老城十字街", "城隍印·中", 600),
    ("CG007", "洛水县城隍司", "中央", "县城隍", "CG006", "洛水河伯举荐", "洛水北岸柳林渡", "城隍印·洛", 300),
    ("CG008", "黄泉渡县城隍司", "西方", "县城隍", "CG004", "黄泉渡口巡检", "黄泉渡口奈何桥头", "城隍印·渡", 300),
]

OFFICER_SEED = [
    # username, real_name, role_code, region, title, city_god_code, password
    ("admin", "酆都大帝", "SUPER_ADMIN", "中央", "幽冥主宰", "CG001", "123123"),
    ("fengdu_02", "北阴副帝", "SUPER_ADMIN", "中央", "副帝·协理", "CG001", "123456"),
    ("dizang", "地藏王菩萨", "AUDITOR", "中央", "幽冥教主·审计", "CG001", "123456"),
    ("dizang_02", "道明和尚", "AUDITOR", "中央", "地藏侍者·稽核", "CG001", "123456"),
    ("guidi_dong", "东方鬼帝", "REGION_ADMIN", "东方", "五方鬼帝·东", "CG002", "123456"),
    ("guidi_xi", "西方鬼帝", "REGION_ADMIN", "西方", "五方鬼帝·西", "CG004", "123456"),
    ("yanluo_01", "秦广王", "JUDGE", "东方", "一殿阎罗", "CG002", "123456"),
    ("yanluo_05", "阎罗王", "JUDGE", "中央", "五殿阎罗", "CG001", "123456"),
    ("cuiyu", "崔珏", "LIFEBOOK_ADMIN", "中央", "生死簿判官", "CG001", "123456"),
    ("cuiyu_02", "掌簿司吏", "LIFEBOOK_ADMIN", "中央", "生死簿副判", "CG006", "123456"),
    ("wuchang_hei", "黑无常", "FIELD_OFFICER", "中央", "勾魂使者·黑", "CG001", "123456"),
    ("wuchang_bai", "白无常", "FIELD_OFFICER", "东方", "勾魂使者·白", "CG002", "123456"),
    ("niutou", "牛头", "ESCORT", "南方", "押解鬼差·牛", "CG003", "123456"),
    ("mamian", "马面", "ESCORT", "北方", "押解鬼差·马", "CG005", "123456"),
    ("chenghuang_dong", "东岳城隍", "BRANCH_ADMIN", "东方", "府城隍", "CG002", "123456"),
    ("chenghuang_luo", "洛水城隍", "BRANCH_ADMIN", "中央", "县城隍", "CG007", "123456"),
    ("mengpo", "孟婆", "REINCARNATION_OFFICER", "中央", "奈何桥主事", "CG001", "123456"),
    ("mengpo_02", "孟婆侍女", "REINCARNATION_OFFICER", "西方", "孟婆汤执勺", "CG008", "123456"),
    ("ludong", "迷魂殿录供官", "REGISTRAR", "南方", "录供·南", "CG003", "123456"),
    ("ludong_02", "孽镜台照镜官", "REGISTRAR", "北方", "照镜·北", "CG005", "123456"),
]

MENU_SEED = [
    # code, name, parent_code, path, component, icon, type, permission_code, sort
    ("dashboard", "总览", None, "/dashboard", "dashboard/Dashboard", "Odometer", "菜单", None, 1),
    ("soul", "亡魂管理", None, "/soul", "Layout", "User", "目录", None, 2),
    ("soul-list", "亡魂主档", "soul", "/soul/list", "soul/SoulList", "List", "菜单", "soul:view", 1),
    ("soul-flow", "流转台账", "soul", "/soul/flow", "soul/SoulFlow", "Sort", "菜单", "soul:view", 2),
    ("lifebook", "生死簿", None, "/life-book", "Layout", "Notebook", "目录", None, 3),
    ("lifebook-list", "生死簿流水", "lifebook", "/life-book/list", "lifebook/LifeBookList", "Document", "菜单", "lifebook:view", 1),
    ("lifebook-review", "待复核", "lifebook", "/life-book/review", "lifebook/LifeBookReview", "Stamp", "菜单", "lifebook:review", 2),
    ("summon", "勾魂工单", None, "/summon", "Layout", "Bell", "目录", None, 4),
    ("summon-list", "工单列表", "summon", "/summon/list", "summon/SummonList", "Tickets", "菜单", "summon:view", 1),
    ("summon-dispatch", "派单调度", "summon", "/summon/dispatch", "summon/SummonDispatch", "Promotion", "菜单", "summon:dispatch", 2),
    ("gate", "鬼门关", None, "/gate", "Layout", "Lock", "目录", None, 5),
    ("gate-verify", "验引过关", "gate", "/gate/verify", "gate/GateVerify", "Key", "菜单", "doc:verify", 1),
    ("lost", "迷魂殿", None, "/lost", "Layout", "MagicStick", "目录", None, 6),
    ("lost-record", "迷魂录供", "lost", "/lost/record", "lost/LostRecord", "Microphone", "菜单", "soul:view", 1),
    ("lost-karma", "孽镜台评分", "lost", "/lost/karma", "lost/KarmaMirror", "DataAnalysis", "菜单", "karma:score", 2),
    ("trial", "十殿审判", None, "/trial", "Layout", "ScaleToOriginal", "目录", None, 7),
    ("trial-list", "审判台账", "trial", "/trial/list", "trial/TrialList", "Files", "菜单", "trial:view", 1),
    ("trial-court", "十殿会审", "trial", "/trial/court", "trial/TrialCourt", "Suitcase", "菜单", "trial:verdict", 2),
    ("punishment", "刑期执行", None, "/punishment", "Layout", "Chainsaw", "目录", None, 8),
    ("punishment-list", "十八层地狱", "punishment", "/punishment/list", "punishment/PunishmentList", "Grid", "菜单", "punishment:view", 1),
    ("reincarnation", "六道轮回", None, "/reincarnation", "Layout", "RefreshRight", "目录", None, 9),
    ("reincarnation-list", "轮回档案", "reincarnation", "/reincarnation/list", "reincarnation/ReincList", "FolderOpened", "菜单", "reincarnation:view", 1),
    ("reincarnation-soup", "孟婆汤办理", "reincarnation", "/reincarnation/soup", "reincarnation/SoupDesk", "Coffee", "菜单", "reincarnation:soup", 2),
    ("citygod", "城隍网点", None, "/city-god", "Layout", "OfficeBuilding", "目录", None, 10),
    ("citygod-list", "网点台账", "citygod", "/city-god/list", "citygod/CityGodList", "MapLocation", "菜单", "citygod:view", 1),
    ("document", "文书中心", None, "/document", "Layout", "Tickets", "目录", None, 11),
    ("document-list", "文书台账", "document", "/document/list", "document/DocumentList", "Postcard", "菜单", "doc:view", 1),
    ("stats", "统计看板", None, "/stats", "stats/StatsBoard", "TrendCharts", "菜单", "stats:view", 12),
    ("system", "系统管理", None, "/system", "Layout", "Setting", "目录", None, 13),
    ("system-officer", "鬼差账号", "system", "/system/officer", "system/OfficerList", "Avatar", "菜单", "officer:view", 1),
    ("system-role", "角色权限", "system", "/system/role", "system/RoleList", "UserFilled", "菜单", "role:view", 2),
    ("system-menu", "菜单配置", "system", "/system/menu", "system/MenuList", "Menu", "菜单", "menu:view", 3),
    ("system-permission", "权限点", "system", "/system/permission", "system/PermissionList", "Key", "菜单", "permission:view", 4),
    ("system-audit", "阴律日志", "system", "/system/audit", "system/AuditLogList", "Notebook", "菜单", "audit:view", 5),
]

# 按钮级菜单（三级菜单的第三级）：type="按钮"，本身不占路由（/auth/menus 接口会过滤），
# 仅用于把「菜单 ↔ 按钮权限点」的归属关系落库，供菜单配置页展示与维护。
# (父菜单编码, 按钮编码, 按钮名称, 所需权限编码, 排序)
BUTTON_MENU_SEED: list[tuple[str, str, str, str, int]] = [
    ("soul-list", "btn-soul-create", "新增亡魂", "soul:create", 1),
    ("soul-list", "btn-soul-update", "编辑亡魂", "soul:update", 2),
    ("soul-list", "btn-soul-delete", "注销亡魂", "soul:delete", 3),
    ("soul-list", "btn-soul-transfer", "亡魂状态流转", "soul:transfer", 4),
    ("soul-list", "btn-soul-freeze", "异常冻结/解冻", "soul:freeze", 5),
    ("soul-list", "btn-soul-export", "导出亡魂台账", "soul:export", 6),
    ("lifebook-list", "btn-lifebook-create", "生死簿录入", "lifebook:create", 1),
    ("lifebook-list", "btn-lifebook-update", "生死簿修改", "lifebook:update", 2),
    ("lifebook-review", "btn-lifebook-review", "生死簿复核", "lifebook:review", 1),
    ("lifebook-review", "btn-lifebook-reject", "生死簿驳回", "lifebook:reject", 2),
    ("summon-list", "btn-summon-create", "创建拘魂工单", "summon:create", 1),
    ("summon-list", "btn-summon-execute", "执行勾魂", "summon:execute", 2),
    ("summon-list", "btn-summon-finish", "完成工单", "summon:finish", 3),
    ("summon-list", "btn-summon-exception", "工单异常登记", "summon:exception", 4),
    ("summon-dispatch", "btn-summon-dispatch", "派发工单", "summon:dispatch", 1),
    ("trial-list", "btn-trial-create", "立案送审", "trial:create", 1),
    ("trial-list", "btn-trial-handle", "开庭审理", "trial:handle", 2),
    ("trial-list", "btn-trial-return", "打回重审", "trial:return", 3),
    ("trial-court", "btn-trial-verdict", "宣读判决", "trial:verdict", 1),
    ("punishment-list", "btn-punishment-execute", "刑期执行", "punishment:execute", 1),
    ("punishment-list", "btn-punishment-adjust", "刑期减免/调整", "punishment:adjust", 2),
    ("reincarnation-list", "btn-reincarnation-create", "轮回立案", "reincarnation:create", 1),
    ("reincarnation-list", "btn-reincarnation-confirm", "投胎确认", "reincarnation:confirm", 2),
    ("reincarnation-soup", "btn-reincarnation-soup", "孟婆汤确认", "reincarnation:soup", 1),
    ("lost-karma", "btn-karma-create", "业力录入", "karma:create", 1),
    ("lost-karma", "btn-karma-score", "孽镜台评分", "karma:score", 2),
    ("system-officer", "btn-officer-create", "新增鬼差", "officer:create", 1),
    ("system-officer", "btn-officer-update", "编辑鬼差", "officer:update", 2),
    ("system-officer", "btn-officer-reset", "重置密码", "officer:reset", 3),
    ("system-officer", "btn-officer-status", "启停用鬼差", "officer:status", 4),
    ("system-role", "btn-role-create", "新增角色", "role:create", 1),
    ("system-role", "btn-role-update", "编辑角色", "role:update", 2),
    ("system-role", "btn-role-assign", "角色授权", "role:assign", 3),
    ("system-menu", "btn-menu-create", "新增菜单", "menu:create", 1),
    ("system-menu", "btn-menu-update", "编辑菜单", "menu:update", 2),
    ("citygod-list", "btn-citygod-create", "新增网点", "citygod:create", 1),
    ("citygod-list", "btn-citygod-update", "编辑网点", "citygod:update", 2),
    ("document-list", "btn-doc-issue", "签发文书", "doc:issue", 1),
    ("document-list", "btn-doc-verify", "核验文书", "doc:verify", 2),
    ("document-list", "btn-doc-void", "作废文书", "doc:void", 3),
    ("system-audit", "btn-audit-export", "导出审计日志", "audit:export", 1),
    ("stats", "btn-stats-export", "导出统计报表", "stats:export", 1),
]


def _name(gender: str) -> str:
    surname = RNG.choice(SURNAMES)
    given = RNG.choice(GIVEN_M if gender == "男" else GIVEN_F)
    return f"{surname}{given}"


def _sin_level(score: int) -> str:
    if score <= -80:
        return "极重"
    if score <= -50:
        return "重"
    if score <= -20:
        return "中"
    if score < 0:
        return "轻"
    return "无"


def _pad(prefix: str, idx: int, width: int = 5) -> str:
    return f"{prefix}{NOW.year}{idx:0{width}d}"


async def seed_base(session: AsyncSession) -> dict:
    """写入起项目必需的最小基础数据（与 sql/03_base_data.sql 口径一致）。

    只含：角色 / 权限点 / 菜单（目录+菜单+按钮三级）/ 角色-权限 / 城隍网点 / 基础账号。
    业务表（亡魂、生死簿、工单……）一律不写数据。返回 ctx，供 seed_demo 复用已写入对象。
    """
    stats: dict[str, int] = {}

    # ---------------- 1. 角色 / 权限 / 菜单 ----------------
    roles: dict[str, Role] = {}
    for rd in ROLE_DEFS:
        role = Role(
            code=rd.code,
            name=rd.name,
            description=rd.description,
            data_scope=rd.data_scope,
            is_builtin=True,
            sort=len(roles) + 1,
            status="正常",
        )
        session.add(role)
        roles[rd.code] = role
    await session.flush()

    perms: dict[str, Permission] = {}
    for pd in PERMISSION_DEFS:
        perm = Permission(
            code=pd.code,
            name=pd.name,
            module=pd.module,
            type=pd.type,
            method=pd.method,
            path=pd.path,
        )
        session.add(perm)
        perms[pd.code] = perm
    await session.flush()

    for code, perm_codes in ROLE_PERMISSIONS.items():
        role = roles[code]
        for pc in perm_codes:
            perm = perms.get(pc)
            if perm is not None:
                session.add(RolePermission(role_id=role.id, permission_id=perm.id))
    await session.flush()
    stats["role"] = len(roles)
    stats["permission"] = len(perms)
    stats["role_permission"] = sum(len(v) for v in ROLE_PERMISSIONS.values())

    menus: dict[str, Menu] = {}
    for code, name, parent_code, path, component, icon, mtype, perm_code, sort in MENU_SEED:
        parent_id = menus[parent_code].id if parent_code else None
        menu = Menu(
            parent_id=parent_id,
            code=code,
            name=name,
            path=path,
            component=component,
            icon=icon,
            type=mtype,
            permission_code=perm_code,
            sort=sort,
            visible=True,
            status="启用",
        )
        session.add(menu)
        await session.flush()  # 需先拿到自增 id，子菜单才能正确挂到父级
        menus[code] = menu

    # 第三级：按钮菜单（仅承载"菜单 ↔ 按钮权限点"归属，不占路由）
    for parent_code, btn_code, btn_name, perm_code, sort in BUTTON_MENU_SEED:
        menu = Menu(
            parent_id=menus[parent_code].id,
            code=btn_code,
            name=btn_name,
            path="",
            component="",
            icon="",
            type="按钮",
            permission_code=perm_code,
            sort=sort,
            visible=True,
            status="启用",
        )
        session.add(menu)
        await session.flush()
        menus[btn_code] = menu
    stats["menu"] = len(menus)

    # ---------------- 2. 城隍网点 ----------------
    city_gods: list[CityGod] = []
    cg_map: dict[str, CityGod] = {}
    for code, name, region, level, parent_code, god_name, address, contact, capacity in CITY_GOD_SEED:
        node = CityGod(
            code=code,
            name=name,
            region=region,
            level=level,
            parent_id=cg_map[parent_code].id if parent_code else None,
            city_god_name=god_name,
            address=address,
            contact=contact,
            soul_capacity=capacity,
            soul_count=0,
            status="在职",
            remark=f"{region}{level}，掌一方亡魂勾押与路引签发。",
        )
        session.add(node)
        await session.flush()
        city_gods.append(node)
        cg_map[code] = node
    stats["city_god"] = len(city_gods)

    # ---------------- 3. 鬼差账号 ----------------
    officers: dict[str, Officer] = {}
    officer_list: list[Officer] = []
    officer_role_names: dict[int, str] = {}
    for username, real_name, role_code, region, title, cg_code, pwd in OFFICER_SEED:
        officer = Officer(
            username=username,
            password_hash=hash_password(pwd),
            real_name=real_name,
            title=title,
            role_id=roles[role_code].id,
            region=region,
            city_god_id=cg_map[cg_code].id,
            data_scope=roles[role_code].data_scope,
            phone=f"138{RNG.randint(10000000, 99999999)}",
            email=f"{username}@difu.gov",
            status="在职",
            remark=f"{roles[role_code].name}·{title}",
        )
        session.add(officer)
        await session.flush()
        officers[username] = officer
        officer_list.append(officer)
        officer_role_names[officer.id] = roles[role_code].name
    stats["officer"] = len(officer_list)

    await session.commit()
    return {
        "stats": stats,
        "roles": roles,
        "officers": officers,
        "officer_list": officer_list,
        "officer_role_names": officer_role_names,
        "city_gods": city_gods,
        "cg_map": cg_map,
    }


async def load_base_ctx(session: AsyncSession) -> dict | None:
    """从库里读取已有基础数据，装配成与 seed_base 相同结构的 ctx；库中无角色时返回 None。"""
    roles = {r.code: r for r in (await session.execute(select(Role))).scalars().all()}
    if not roles:
        return None
    role_name_by_id = {r.id: r.name for r in roles.values()}
    officers = {o.username: o for o in (await session.execute(select(Officer))).scalars().all()}
    officer_list = list(officers.values())
    city_gods = list((await session.execute(select(CityGod).order_by(CityGod.id))).scalars().all())
    return {
        "stats": {},
        "roles": roles,
        "officers": officers,
        "officer_list": officer_list,
        "officer_role_names": {o.id: role_name_by_id.get(o.role_id, "") for o in officer_list},
        "city_gods": city_gods,
        "cg_map": {c.code: c for c in city_gods},
    }


async def seed_demo(session: AsyncSession, ctx: dict | None = None) -> dict:
    """写入业务示例数据（与 sql/04_test_data.sql 口径一致）。

    ctx 为空时先补基础数据。覆盖：亡魂 / 生死簿 / 勾魂工单 / 审判 / 刑期 / 轮回 /
    业力 / 文书 / 移动端审批与消息 / 阴律日志，导入后 PC 端与移动端各列表页均有内容。
    """
    if ctx is None:
        ctx = await seed_base(session)
    officers = ctx["officers"]
    officer_list = ctx["officer_list"]
    officer_role_names = ctx["officer_role_names"]
    city_gods = ctx["city_gods"]
    stats: dict[str, int] = {}

    field_officers = [o for o in officer_list if o.username in ("wuchang_hei", "wuchang_bai", "niutou", "mamian")]
    judges = [o for o in officer_list if o.username.startswith("yanluo")]
    lifebook_officers = [o for o in officer_list if o.username.startswith("cuiyu")]
    mengpo_officers = [o for o in officer_list if o.username.startswith("mengpo")]
    registrars = [o for o in officer_list if o.username.startswith("ludong")]
    branch_admins = [o for o in officer_list if o.username.startswith("chenghuang")]

    # ---------------- 4. 亡魂主档（80） ----------------
    souls: list[Soul] = []
    idx = 0
    for status, count in SOUL_PLAN:
        for _ in range(count):
            idx += 1
            gender = RNG.choice(GENDERS)
            region = REGIONS[(idx - 1) % len(REGIONS)]
            region_nodes = [c for c in city_gods if c.region == region] or city_gods
            node = RNG.choice(region_nodes)
            death_days_ago = RNG.randint(0, 29)
            death_at = NOW - timedelta(days=death_days_ago, hours=RNG.randint(0, 20))
            age = RNG.randint(18, 88)
            birth_at = datetime(death_at.year - age, RNG.randint(1, 12), RNG.randint(1, 28))
            score = RNG.randint(-95, 45)
            soul = Soul(
                soul_no=_pad("SN", idx),
                name=_name(gender),
                gender=gender,
                age=age,
                birth_date=birth_at,
                death_date=death_at - timedelta(days=1) if status != SoulStatus.REGISTERED else None,
                native_place=RNG.choice(NATIVE),
                region=region,
                status=status,
                prev_status="",
                karma_score=score,
                sin_level=_sin_level(score),
                death_type=RNG.choice(DEATH_TYPES),
                life_book_no=_pad("SB", idx),
                city_god_id=node.id,
                current_location=LOCATION_BY_STATUS.get(status, "阴司在册"),
                is_deleted=status == SoulStatus.CANCELLED,
                remark="",
                created_at=NOW - timedelta(days=death_days_ago, minutes=RNG.randint(0, 600)),
                updated_at=NOW - timedelta(days=max(0, death_days_ago - RNG.randint(0, 3))),
            )
            session.add(soul)
            souls.append(soul)
    await session.flush()
    stats["soul"] = len(souls)

    by_status: dict[str, list[Soul]] = {}
    for soul in souls:
        by_status.setdefault(soul.status, []).append(soul)

    # ---------------- 5. 生死簿（120） ----------------
    life_books: list[LifeBook] = []
    lb_status_plan = ["待复核"] * 8 + ["已驳回"] * 3
    for i in range(120):
        soul = souls[i % len(souls)]
        if i < len(lb_status_plan):
            review_status = lb_status_plan[i]
        else:
            review_status = "已复核"
        action = "录入" if i % 2 == 0 else RNG.choice(["修改", "复核", "注销"])
        before_years = RNG.randint(30, 90)
        after_years = before_years + RNG.choice([-8, -3, 0, 2, 5])
        operator = RNG.choice(lifebook_officers)
        book = LifeBook(
            book_no=_pad("SB", 1000 + i, 6),
            soul_id=soul.id,
            soul_name=soul.name,
            action=action,
            lifespan_years=after_years,
            before_content=f"原判阳寿 {before_years} 年，卒于 {soul.native_place}。",
            after_content=f"改判阳寿 {after_years} 年，寿终正寝。",
            diff_desc=f"阳寿 {before_years} → {after_years} 年（{after_years - before_years:+d}）",
            review_status=review_status,
            operator_id=operator.id,
            reviewer_id=RNG.choice(lifebook_officers).id if review_status != "待复核" else None,
            reviewer_name=lifebook_officers[0].real_name if review_status != "待复核" else "",
            reviewed_at=NOW - timedelta(days=RNG.randint(0, 20)) if review_status != "待复核" else None,
            review_comment="" if review_status == "待复核" else ("核准，准予勾录。" if review_status == "已复核" else "改判无据，驳回重审。"),
            is_tampered=(review_status == "已驳回" and i % 3 == 0),
            created_at=NOW - timedelta(days=RNG.randint(0, 29), minutes=RNG.randint(0, 800)),
        )
        session.add(book)
        life_books.append(book)
    await session.flush()
    stats["life_book"] = len(life_books)

    # ---------------- 6. 勾魂工单（25） ----------------
    summon_plan = (
        [("已完成", 15)] + [("执行中", 5)] + [("已超时", 3)] + [("异常", 2)]
    )
    summon_orders: list[SummonOrder] = []
    oi = 0
    summon_souls = souls[:25]
    for status, count in summon_plan:
        for _ in range(count):
            soul = summon_souls[oi]
            oi += 1
            assignee = field_officers[oi % len(field_officers)]
            deadline = NOW - timedelta(hours=RNG.randint(-48, 72))
            started = deadline - timedelta(hours=6)
            finished = started + timedelta(hours=RNG.randint(2, 20)) if status == "已完成" else None
            order = SummonOrder(
                order_no=_pad("GH", oi, 5),
                soul_id=soul.id,
                soul_name=soul.name,
                region=soul.region,
                city_god_id=soul.city_god_id,
                assignee_id=assignee.id,
                assignee_name=assignee.real_name,
                priority=RNG.choice(["普通", "普通", "加急", "特急"]),
                status=status,
                death_type=soul.death_type,
                location=f"{soul.native_place}·{RNG.choice(['东街', '西巷', '城南', '北门外', '渡口'])}",
                deadline_at=deadline,
                started_at=started,
                finished_at=finished,
                result="勾魂完成，魂已押至城隍庙备案。" if status == "已完成" else "",
                abnormal_reason="阳寿未尽，魂体不稳，暂缓勾取。" if status == "异常" else "",
                created_at=NOW - timedelta(days=RNG.randint(0, 29), minutes=RNG.randint(0, 900)),
            )
            session.add(order)
            summon_orders.append(order)
            soul.summon_order_id = None
    await session.flush()
    for order in summon_orders:
        for soul in summon_souls:
            if soul.id == order.soul_id:
                soul.summon_order_id = order.id
    stats["summon_order"] = len(summon_orders)

    # ---------------- 7. 十殿审判（40） ----------------
    court_names = ["一殿秦广王", "二殿楚江王", "三殿宋帝王", "四殿仵官王", "五殿阎罗王",
                   "六殿卞城王", "七殿泰山王", "八殿都市王", "九殿平等王", "十殿转轮王"]
    trials: list[TrialRecord] = []
    trial_souls: list[tuple[Soul, str]] = []
    for soul in by_status.get(SoulStatus.PENDING_TRIAL, []):
        trial_souls.append((soul, "待审"))
    in_trial = by_status.get(SoulStatus.IN_TRIAL, [])
    for i, soul in enumerate(in_trial):
        trial_souls.append((soul, "打回重审" if i < 2 else "审理中"))
    closed_pool: list[Soul] = (
        by_status.get(SoulStatus.CONVICTED, [])
        + by_status.get(SoulStatus.SERVING, [])[:10]
        + by_status.get(SoulStatus.SERVED, [])[:8]
        + by_status.get(SoulStatus.WAIT_REBIRTH, [])[:2]
    )
    for soul in closed_pool[:22]:
        trial_souls.append((soul, "已结案"))
    returned = by_status.get(SoulStatus.RETURNED_LIFE, [])
    if returned:
        trial_souls.append((returned[0], "已结案"))
    for soul in by_status.get(SoulStatus.WRONGFUL_CITY, [])[:2]:
        trial_souls.append((soul, "已结案"))
    innocent = by_status.get(SoulStatus.RETURNED_LIFE, [])
    if len(innocent) > 1:
        trial_souls.append((innocent[1], "已结案"))
    trial_souls = trial_souls[:40]

    for i, (soul, status) in enumerate(trial_souls):
        court_level = (i % 10) + 1
        judge = judges[i % len(judges)]
        if status == "已结案":
            if soul.status == SoulStatus.RETURNED_LIFE and i % 2 == 0:
                verdict, detail, years, hell = "还阳", "查阳寿未尽，系误勾，准予还阳复位。", 0, 0
            elif soul.status == SoulStatus.RETURNED_LIFE:
                verdict, detail, years, hell = "无罪", "孽镜无恶，六道随业，判无罪释放。", 0, 0
            elif soul.status == SoulStatus.WRONGFUL_CITY:
                verdict, detail, years, hell = "发配枉死城", "枉死之魂，怨气未消，发配枉死城待城隍超度。", 0, 0
            else:
                years = RNG.randint(3, 90)
                hell = RNG.randint(1, 18)
                verdict = "有罪"
                detail = f"孽镜照见生前{soul.sin_level}罪业，判入第{hell}层{HELL_NAMES[hell - 1]}，刑期 {years} 年。"
            closed_at = NOW - timedelta(days=RNG.randint(0, 25))
        elif status == "打回重审":
            verdict, detail, years, hell = "打回重审", "供词前后矛盾，卷宗发还迷魂殿重新录供。", 0, 0
            closed_at = NOW - timedelta(days=RNG.randint(0, 6))
        else:
            verdict, detail, years, hell = "", "", 0, 0
            closed_at = None
        trial = TrialRecord(
            trial_no=_pad("SP", i + 1, 5),
            soul_id=soul.id,
            soul_name=soul.name,
            court_level=court_level,
            region=soul.region,
            judge_id=judge.id,
            judge_name=court_names[court_level - 1],
            karma_snapshot=soul.karma_score,
            guilt_desc=f"{soul.death_type}而亡，身前业力 {soul.karma_score} 分（{soul.sin_level}）。",
            status=status,
            verdict=verdict,
            verdict_detail=detail,
            sentence_years=years,
            hell_level=hell,
            next_court_level=min(court_level + 1, 10) if verdict == "有罪" and court_level < 10 else 0,
            started_at=NOW - timedelta(days=RNG.randint(3, 29)),
            closed_at=closed_at,
            created_at=NOW - timedelta(days=RNG.randint(3, 29), minutes=RNG.randint(0, 900)),
        )
        session.add(trial)
        trials.append(trial)
    await session.flush()
    stats["trial_record"] = len(trials)

    # ---------------- 8. 刑期台账（18，十八层地狱全覆盖） ----------------
    punishments: list[Punishment] = []
    closed_trials = [t for t in trials if t.verdict == "有罪"]
    serving_souls = by_status.get(SoulStatus.SERVING, [])
    served_souls = by_status.get(SoulStatus.SERVED, [])
    wait_rebirth_souls = by_status.get(SoulStatus.WAIT_REBIRTH, [])
    punish_plan: list[tuple[Soul, str]] = (
        [(s, "服刑中") for s in serving_souls[:10]]
        + [(s, "已刑满") for s in served_souls[:5]]
        + [(s, "已刑满") for s in wait_rebirth_souls[:3]]
    )
    for i, (soul, pstatus) in enumerate(punish_plan, start=1):
        hell_level = i
        trial = next((t for t in closed_trials if t.soul_id == soul.id), None)
        years = trial.sentence_years if trial and trial.sentence_years else RNG.randint(5, 60)
        start_at = NOW - timedelta(days=RNG.randint(30, 400))
        end_at = start_at + timedelta(days=years * 30)
        punishment = Punishment(
            punish_no=_pad("XQ", i, 5),
            soul_id=soul.id,
            soul_name=soul.name,
            trial_record_id=trial.id if trial else None,
            region=soul.region,
            hell_level=hell_level,
            hell_name=HELL_NAMES[hell_level - 1],
            sentence_years=years,
            reduced_years=0,
            start_at=start_at,
            end_at=end_at,
            status=pstatus,
            progress=(
                f"已刑满释放，押赴奈何桥等候孟婆汤。"
                if pstatus == "已刑满"
                else f"服刑 {RNG.randint(10, 80)}%，狱卒轮值正常。"
            ),
            executor_name=(officers["niutou"].real_name if i % 2 else officers["mamian"].real_name),
            remark=f"第{hell_level}层{HELL_NAMES[hell_level - 1]}",
            created_at=NOW - timedelta(days=RNG.randint(0, 29), minutes=RNG.randint(0, 900)),
        )
        session.add(punishment)
        punishments.append(punishment)
    await session.flush()
    stats["punishment"] = len(punishments)

    # ---------------- 9. 轮回档案（12，六道各 2） ----------------
    reincarnations: list[Reincarnation] = []
    reinc_souls = by_status.get(SoulStatus.REBIRTHED, []) + by_status.get(SoulStatus.WAIT_REBIRTH, [])
    mengpo = mengpo_officers[0]
    ri = 0
    for path in REINCARNATION_PATHS:
        for k in range(2):
            soul = reinc_souls[ri % len(reinc_souls)] if reinc_souls else souls[ri]
            ri += 1
            if k == 0 and path in ("天道", "人道", "阿修罗道"):
                rstatus = "已投胎" if soul.status == SoulStatus.REBIRTHED else "待投胎"
            elif path == "地狱道" and k == 1:
                rstatus = "已归档"
            else:
                rstatus = "待办理" if k == 1 else "待投胎"
            soup_confirmed = not (path == "饿鬼道" and k == 1)  # 唯一一条未确认孟婆汤
            rec = Reincarnation(
                reinc_no=_pad("LH", ri, 5),
                soul_id=soul.id,
                soul_name=soul.name,
                region=soul.region,
                path=path,
                target_world={
                    "天道": "三十三天·忉利天",
                    "人道": "南赡部洲·中土",
                    "阿修罗道": "须弥山北·修罗界",
                    "畜生道": "人间·禽兽道",
                    "饿鬼道": "幽冥·饿鬼城",
                    "地狱道": "无间地狱·外围",
                }[path],
                karma_score=soul.karma_score,
                soup_confirmed=soup_confirmed,
                soup_at=NOW - timedelta(days=RNG.randint(0, 12)) if soup_confirmed else None,
                soup_operator=mengpo.real_name if soup_confirmed else "",
                status=rstatus,
                scheduled_at=NOW + timedelta(days=RNG.randint(-10, 10)),
                reincarnated_at=NOW - timedelta(days=RNG.randint(0, 10)) if rstatus == "已投胎" else None,
                operator_id=mengpo.id,
                remark="前世记忆已尽消。" if soup_confirmed else "孟婆汤尚未饮尽，暂缓投胎。",
                created_at=NOW - timedelta(days=RNG.randint(0, 29), minutes=RNG.randint(0, 900)),
            )
            session.add(rec)
            reincarnations.append(rec)
    await session.flush()
    stats["reincarnation"] = len(reincarnations)

    # ---------------- 10. 业力记录（60） ----------------
    karma_records: list[KarmaRecord] = []
    for i in range(60):
        soul = souls[(i * 3) % len(souls)]
        ktype = KARMA_TYPES[i % len(KARMA_TYPES)]
        record = KarmaRecord(
            karma_no=_pad("YL", i + 1, 5),
            soul_id=soul.id,
            soul_name=soul.name,
            region=soul.region,
            karma_type=ktype,
            category=RNG.choice(KARMA_CATEGORIES),
            score=RNG.randint(5, 80),
            source=RNG.choice(KARMA_SOURCES),
            occurred_at=NOW - timedelta(days=RNG.randint(0, 29)),
            recorder_id=RNG.choice(registrars).id,
            recorder_name=RNG.choice(registrars).real_name,
            description=f"孽镜所照：{ktype}业一桩。",
            created_at=NOW - timedelta(days=RNG.randint(0, 29), minutes=RNG.randint(0, 900)),
        )
        session.add(record)
        karma_records.append(record)
    await session.flush()
    stats["karma_record"] = len(karma_records)

    # ---------------- 11. 文书（30） ----------------
    documents: list[Document] = []
    doc_plan = [("路引", 16, "已核验"), ("拘票", 6, "已签发"), ("判决书", 4, "已签发"),
                ("轮回文书", 2, "已核验"), ("还阳令", 1, "已签发"), ("冻结令", 1, "草稿")]
    di = 0
    for doc_type, count, dstatus in doc_plan:
        prefix = {"路引": "LY", "拘票": "JP", "判决书": "PJ", "轮回文书": "LH", "还阳令": "HY", "冻结令": "DJ"}[doc_type]
        for _ in range(count):
            di += 1
            soul = souls[(di * 5) % len(souls)]
            doc = Document(
                doc_no=_pad(prefix, di, 5),
                doc_type=doc_type,
                title=f"{doc_type}·{soul.name}",
                soul_id=soul.id,
                soul_name=soul.name,
                summon_order_id=None,
                city_god_id=soul.city_god_id,
                content=(
                    f"兹有亡魂{soul.name}，{soul.gender}，卒年{soul.age}，"
                    f"籍贯{soul.native_place}，属{soul.region}鬼域，准予凭此文过关。"
                ),
                status=dstatus,
                issued_by=RNG.choice(branch_admins).real_name if dstatus != "草稿" else "",
                issued_at=NOW - timedelta(days=RNG.randint(0, 20)) if dstatus != "草稿" else None,
                verified_by=officers["niutou"].real_name if dstatus == "已核验" else "",
                verified_at=NOW - timedelta(days=RNG.randint(0, 15)) if dstatus == "已核验" else None,
                created_at=NOW - timedelta(days=RNG.randint(0, 29), minutes=RNG.randint(0, 900)),
            )
            session.add(doc)
            documents.append(doc)
    await session.flush()
    stats["document"] = len(documents)

    # ---------------- 12. 移动端：审批单 / 审批环节 / 消息 / 设备 ----------------
    stats.update(await seed_mobile(session, officers, souls, summon_orders))

    # ---------------- 13. 阴律日志（300，近 30 天，含 3 条篡改告警） ----------------
    modules = ["亡魂主档", "生死簿", "勾魂工单", "十殿审判", "刑期执行", "六道轮回",
               "业力记录", "鬼差账号", "角色管理", "城隍网点", "文书管理"]
    actions = ["view", "create", "update", "delete", "transition", "review", "verdict",
               "dispatch", "finish", "score", "export", "login", "issue", "verify"]
    audit_logs: list[AuditLog] = []
    for i in range(300):
        officer = officer_list[i % len(officer_list)]
        is_tamper = i < 3
        level = "篡改告警" if is_tamper else ("告警" if i % 37 == 0 else "正常")
        module = "生死簿" if is_tamper else modules[i % len(modules)]
        action = "update" if is_tamper else actions[i % len(actions)]
        detail = (
            f"检测到生死簿阳寿字段被非授权改写：{souls[i].name} 阳寿 +{RNG.randint(3, 20)} 年，已回滚并追责。"
            if is_tamper
            else f"{modules[i % len(modules)]} {action} 操作留痕，影响 {RNG.randint(1, 9)} 条记录。"
        )
        log = AuditLog(
            officer_id=officer.id,
            officer_name=officer.real_name,
            role_name=officer_role_names.get(officer.id, ""),
            action=action,
            module=module,
            resource=module,
            resource_id=str(RNG.randint(1, 120)),
            detail=detail,
            level=level,
            ip=f"10.13.{RNG.randint(0, 9)}.{RNG.randint(1, 250)}",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Marvis-Admin/1.0",
            created_at=NOW - timedelta(days=RNG.randint(0, 29), minutes=RNG.randint(0, 1400), seconds=RNG.randint(0, 59)),
        )
        session.add(log)
        audit_logs.append(log)
    await session.flush()
    stats["audit_log"] = len(audit_logs)

    # ---------------- 14. 回填网点亡魂数 / 亡魂-工单关联 ----------------
    for node in city_gods:
        node.soul_count = sum(1 for s in souls if s.city_god_id == node.id)

    await session.commit()
    logger.info(f"业务示例数据灌入完成：{stats}")
    return stats


async def seed_all(session: AsyncSession) -> dict:
    """基础数据 + 业务示例数据（等价于 python -m app.seed --with-demo）。"""
    ctx = await seed_base(session)
    stats = await seed_demo(session, ctx)
    stats.update(ctx["stats"])
    return stats


async def seed_mobile(
    session: AsyncSession,
    officers: dict[str, Officer],
    souls: list[Soul],
    summon_orders: list[SummonOrder],
) -> dict[str, int]:
    """移动端 H5 专属数据：审批单 / 审批环节 / 站内消息 / 设备绑定。"""
    stats: dict[str, int] = {}
    approver_by_role: dict[str, Officer] = {
        SUPER_ADMIN_ROLE: officers["admin"],
        "LIFEBOOK_ADMIN": officers["cuiyu"],
        "JUDGE": officers["yanluo_05"],
        "AUDITOR": officers["dizang"],
        "BRANCH_ADMIN": officers["chenghuang_dong"],
    }
    # (biz_type, years, applicant_key, progress)
    # progress: open=停在首环节待审；half=会签中间态；l2=停在末环节；agree=全部通过；reject=首环节驳回
    approval_plan = [
        (BizType.LIFE_EXTEND.value, 5, "wuchang_hei", "open"),
        (BizType.LIFE_EXTEND.value, 8, "niutou", "agree"),
        (BizType.LIFE_EXTEND.value, 10, "wuchang_bai", "open"),
        (BizType.LIFE_EXTEND.value, 12, "chenghuang_luo", "l2"),
        (BizType.LIFE_EXTEND.value, 20, "yanluo_01", "open"),
        (BizType.LIFE_EXTEND.value, 30, "chenghuang_dong", "reject"),
        (BizType.VERDICT_REVIVE.value, 0, "yanluo_05", "l2"),
        (BizType.VERDICT_REVIVE.value, 0, "yanluo_01", "open"),
        (BizType.VERDICT_REVIVE.value, 0, "yanluo_05", "agree"),
        (BizType.VERDICT_REVIVE.value, 0, "yanluo_01", "reject"),
        (BizType.PUNISH_REDUCE.value, 5, "yanluo_05", "half"),
        (BizType.PUNISH_REDUCE.value, 8, "yanluo_01", "l2"),
        (BizType.PUNISH_REDUCE.value, 3, "yanluo_05", "agree"),
        (BizType.ABNORMAL_REPORT.value, 0, "wuchang_hei", "open"),
        (BizType.ABNORMAL_REPORT.value, 0, "wuchang_bai", "agree"),
        (BizType.ABNORMAL_REPORT.value, 0, "niutou", "reject"),
        (BizType.ABNORMAL_REPORT.value, 0, "mamian", "open"),
        (BizType.ORDER_CANCEL.value, 0, "chenghuang_dong", "open"),
        (BizType.ORDER_CANCEL.value, 0, "wuchang_hei", "agree"),
        (BizType.ORDER_CANCEL.value, 0, "ludong", "open"),
    ]
    approvals: list[ApprovalRequest] = []
    steps: list[ApprovalStep] = []
    messages: list[MobileMessage] = []

    for idx, (biz_type, years, applicant_key, progress) in enumerate(approval_plan):
        applicant = officers[applicant_key]
        soul = souls[(idx * 7) % len(souls)]
        if biz_type == BizType.ORDER_CANCEL.value:
            order = summon_orders[idx % len(summon_orders)]
            biz_id = order.id
            payload = {"order_no": order.order_no, "soul_name": order.soul_name, "region": order.region}
            title = f"工单撤销 · {order.order_no}"
            summary = f"{applicant.real_name} 申请撤销对 {order.soul_name} 的拘魂工单 {order.order_no}，需 L1 派单人确认。"
        elif biz_type == BizType.ABNORMAL_REPORT.value:
            biz_id = soul.id
            payload = {"soul_id": soul.id, "soul_name": soul.name, "region": soul.region, "abnormal": "定位偏离、勾押超时"}
            title = f"异常上报 · {soul.name} 拘押受阻"
            summary = f"{applicant.real_name} 上报 {soul.region} 辖区 {soul.name} 勾押异常，由 L1 直属判官裁定。"
        elif biz_type == BizType.PUNISH_REDUCE.value:
            biz_id = soul.id
            payload = {"soul_id": soul.id, "soul_name": soul.name, "region": soul.region, "reduce_years": years}
            title = f"减刑赦免 {years} 年 · {soul.name}"
            summary = f"{soul.name} 服刑表现良好，申请减免刑期 {years} 年，需殿主与监刑官依次会签后报 L2。"
        elif biz_type == BizType.VERDICT_REVIVE.value:
            biz_id = soul.id
            payload = {"soul_id": soul.id, "soul_name": soul.name, "region": soul.region, "verdict": "判令还阳"}
            title = f"判令还阳 · {soul.name}"
            summary = f"十殿审判认定 {soul.name} 阳寿未尽，判令还阳，需 L1 殿主报 L2 酆都大帝核准。"
        else:
            biz_id = soul.id
            payload = {"soul_id": soul.id, "soul_name": soul.name, "region": soul.region, "years": years}
            title = f"生死簿添寿 {years} 年 · {soul.name}"
            if years <= 10:
                summary = f"{soul.name}（{soul.region}）申请增补阳寿 {years} 年，未超阈值，由 L1 城隍审批，不上报。"
            else:
                summary = f"{soul.name}（{soul.region}）申请增补阳寿 {years} 年，超阈值，需 L1 崔珏上报 L2 酆都大帝。"

        chain = resolve_approval_chain(biz_type, years=years)
        current_stage: int | None
        if progress == "agree":
            current_stage = None
            status = APPROVAL_STATUS_AGREED
        elif progress == "reject":
            current_stage = 0
            status = APPROVAL_STATUS_REJECTED
        elif progress == "half":
            current_stage = min(1, len(chain) - 1)
            status = approval_status_label(chain[current_stage])
        elif progress == "l2":
            current_stage = len(chain) - 1
            status = approval_status_label(chain[current_stage])
        else:
            current_stage = 0
            status = approval_status_label(chain[0])

        created_at = NOW - timedelta(days=idx % 18, hours=RNG.randint(1, 10))
        request = ApprovalRequest(
            biz_type=biz_type,
            biz_id=biz_id,
            title=title,
            summary=summary,
            payload_json=json.dumps(payload, ensure_ascii=False),
            applicant_id=applicant.id,
            status=status,
            deadline_at=created_at + timedelta(days=2 + idx % 3),
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(request)
        await session.flush()
        approvals.append(request)

        request_steps: list[ApprovalStep] = []
        for stage_idx, approvers in enumerate(chain):
            for person_idx, person_def in enumerate(approvers):
                actor = applicant if person_def.role_code == APPLICANT_APPROVER else approver_by_role.get(person_def.role_code, officers["admin"])
                action = APPROVAL_STEP_LOCKED
                comment = ""
                acted_at = None
                if progress == "agree":
                    action = APPROVAL_STEP_AGREE
                elif progress == "reject" and stage_idx == 0 and person_idx == 0:
                    action = APPROVAL_STEP_REJECT
                elif progress != "reject" and current_stage is not None:
                    if stage_idx < current_stage:
                        action = APPROVAL_STEP_AGREE
                    elif stage_idx == current_stage:
                        action = APPROVAL_STEP_WAIT
                if action == APPROVAL_STEP_AGREE:
                    comment = "已核，同意呈报。" if stage_idx == 0 else "复核无误，同意。"
                elif action == APPROVAL_STEP_REJECT:
                    comment = "材料不足，添寿依据与孽镜台评分不符，驳回重报。"
                if action in (APPROVAL_STEP_AGREE, APPROVAL_STEP_REJECT):
                    acted_at = created_at + timedelta(hours=stage_idx + RNG.randint(1, 6))
                step = ApprovalStep(
                    request_id=request.id,
                    step_no=stage_idx + 1,
                    approver_id=actor.id,
                    action=action,
                    comment=comment,
                    acted_at=acted_at,
                )
                session.add(step)
                request_steps.append(step)
        await session.flush()
        steps.extend(request_steps)

        deadline_text = request.deadline_at.strftime("%m-%d %H:%M")
        for step in request_steps:
            if step.action != APPROVAL_STEP_WAIT:
                continue
            messages.append(
                MobileMessage(
                    receiver_id=step.approver_id,
                    type="审批待办",
                    title=f"待审批：{title}",
                    content=f"{applicant.real_name} 提交「{title}」，请您在 {deadline_text} 前处理。",
                    biz_ref=f"approval:{request.id}",
                    is_read=False,
                    priority="紧急" if idx % 5 == 0 else "普通",
                    created_at=created_at + timedelta(minutes=5),
                )
            )
        if status in (APPROVAL_STATUS_AGREED, APPROVAL_STATUS_REJECTED):
            messages.append(
                MobileMessage(
                    receiver_id=applicant.id,
                    type="审批结果",
                    title=f"{status}：{title}",
                    content=f"您提交的「{title}」审批结果：{status}。",
                    biz_ref=f"approval:{request.id}",
                    is_read=idx % 3 == 0,
                    priority="普通",
                    created_at=created_at + timedelta(hours=RNG.randint(3, 12)),
                )
            )

    extra_messages = [
        ("admin", "紧急通告", "十殿联席会：季度审判质效通报", "本季度审判质效通报已发布，请各殿主三日内阅知并反馈整改意见。", "notice:quarterly", False, "紧急"),
        ("admin", "系统通知", "移动端 H5 已上线", "幽冥政务中台移动端已开放，支持待办审批、消息中心与外勤工单处理。", "system:mobile", True, "普通"),
        ("cuiyu", "审批提醒", "生死簿复核积压 12 条", "待复核流水累计 12 条，其中 3 条涉及阳寿异常，请优先处理。", "lifebook:review", False, "紧急"),
        ("yanluo_05", "系统通知", "判令还阳待报 L2", "本殿 2 条判令还阳已过 L1，等待酆都大帝核准。", "trial:revive", False, "普通"),
        ("wuchang_hei", "工单派发", "新增拘魂工单 3 单", "东方辖区新增 3 单拘魂任务，最近一单 24 小时内到期，请及时领取。", "summon:new", False, "紧急"),
        ("wuchang_hei", "考勤提醒", "外勤打卡未完成", "您今日尚有一次到场打卡未完成，请在离场前补录。", "device:checkin", True, "普通"),
        ("niutou", "工单派发", "押解任务变更", "原定南线押解路线调整，请查收最新路引与交接点。", "summon:route", False, "普通"),
        ("dizang", "审计通知", "监刑稽核待签 2 单", "2 单减刑赦免待监刑官会签，请核对刑期台账后处理。", "punishment:audit", False, "普通"),
        ("chenghuang_dong", "系统通知", "网点容量告警", "东岳城隍网点在押亡魂已达容量 85%，建议申请分流。", "citygod:capacity", True, "普通"),
        ("mengpo", "业务提醒", "孟婆汤待办 5 例", "今日 5 例投胎待饮孟婆汤，请核对轮回档案后办理。", "reincarnation:soup", False, "普通"),
    ]
    for receiver_key, msg_type, msg_title, content, biz_ref, is_read, priority in extra_messages:
        messages.append(
            MobileMessage(
                receiver_id=officers[receiver_key].id,
                type=msg_type,
                title=msg_title,
                content=content,
                biz_ref=biz_ref,
                is_read=is_read,
                priority=priority,
                created_at=NOW - timedelta(hours=RNG.randint(1, 60)),
            )
        )
    for message in messages:
        session.add(message)
    await session.flush()
    stats["approval_request"] = len(approvals)
    stats["approval_step"] = len(steps)
    stats["mobile_message"] = len(messages)

    devices: list[MobileDevice] = []
    device_seed = [
        ("admin", "H5-ADMIN-0001", "pushtoken-admin-0001", "ios", 12),
        ("wuchang_hei", "H5-WC-0001", "pushtoken-wc-0001", "android", 3),
        ("cuiyu", "H5-CUIYU-0001", "pushtoken-cuiyu-0001", "h5", 320),
        ("yanluo_05", "H5-YL05-0001", "pushtoken-yl05-0001", "android", 55),
    ]
    for user_key, device_id, push_token, platform, minutes_ago in device_seed:
        device = MobileDevice(
            user_id=officers[user_key].id,
            device_id=device_id,
            push_token=push_token,
            platform=platform,
            last_active_at=NOW - timedelta(minutes=minutes_ago),
        )
        session.add(device)
        devices.append(device)
    await session.flush()
    stats["mobile_device"] = len(devices)
    return stats


async def seed_once(session: AsyncSession) -> bool:
    """空库才灌基础数据（服务启动时自动调用）；返回是否实际执行。"""
    exists = (await session.execute(select(func.count(Role.id)))).scalar_one()
    if exists:
        return False
    ctx = await seed_base(session)
    logger.info(f"基础数据灌入完成：{ctx['stats']}")
    return True


async def reset_all(session: AsyncSession) -> None:
    """清空业务表（仅 dev 演示用，按外键逆序删除）。"""
    for model in (
        ApprovalStep,
        ApprovalRequest,
        MobileMessage,
        MobileDevice,
        AuditLog,
        Document,
        KarmaRecord,
        Reincarnation,
        Punishment,
        TrialRecord,
        SummonOrder,
        LifeBook,
        Soul,
        Officer,
        RolePermission,
        Menu,
        Permission,
        Role,
        CityGod,
    ):
        await session.execute(delete(model))
    await session.commit()


async def main() -> None:
    argv = sys.argv[1:]
    unknown = [a for a in argv if a not in ("--force", "--with-demo")]
    if unknown:
        raise SystemExit(f"未知参数：{' '.join(unknown)}\n用法：python -m app.seed [--with-demo] [--force]")
    force = "--force" in argv
    with_demo = "--with-demo" in argv

    logger.info(f"开始初始化数据库：{settings.DATABASE_URL}")
    await init_db()
    async with SessionLocal() as session:
        if force:
            await reset_all(session)
            logger.info("已清空全库（--force）")

        ctx = await load_base_ctx(session)
        if ctx is None:
            ctx = await seed_base(session)
            logger.info(f"基础数据灌入完成：{ctx['stats']}")
        else:
            logger.warning("检测到已有基础数据，跳过。需重灌请加 --force")

        if with_demo:
            soul_count = (await session.execute(select(func.count(Soul.id)))).scalar_one()
            if soul_count:
                logger.warning("检测到已有业务数据，跳过示例数据。需重灌请加 --force")
            else:
                stats = await seed_demo(session, ctx)
                logger.info(f"业务示例数据灌入完成：{stats}")

        logger.info(f"超管账号：{settings.SEED_ADMIN_USERNAME} / {settings.SEED_ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
