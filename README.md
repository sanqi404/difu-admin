# 地府生死铺后台管理系统（difu-admin）

## ⚠️ 许可、品牌与免责说明（必读）

- **版权**：本仓库代码归 sanqi404 独立所有，未经授权不得复制、分发或用于商业项目。本项目按 CC BY-NC（署名 - 非商业性使用）精神开放个人学习与内部自用。任何以「difu-admin」名义进行的收费服务均与本仓库无关，本仓库仅由 sanqi404 独立维护。
- **禁止商用**：禁止将本仓库或其衍生作品用于 SaaS 运营、收取订阅费/会员费、商业产品核心组件出售等盈利行为；引用须标明原作者 sanqi404、项目名称及原始链接。违反商用禁令者将立即终止默示许可并追究法律责任。
- **免责声明**：软件按现状提供，不提供任何保证；作者对因使用产生的损失概不负责。完整条款见 [LICENSE](./LICENSE)。

---

幽冥政务题材的后台管理系统，包含 **后端 API + PC 管理端 + 移动端 H5** 三部分，覆盖生死簿、勾魂令、审判、刑罚、轮回、因果、城隍、文书、审计、移动审批等业务域。

设计要点：

- **双通道运行**：`dev` 通道用 SQLite + 内存缓存，零外部依赖即可跑起来；`prod` 通道用 MySQL + Redis。业务代码只依赖 `DATABASE_URL` 与 `CACHE_BACKEND`，通过 `ENV_MODE` 切换。
- **统一响应**：接口返回 `{code, msg, data}`，列表页为 `{items, total, page, page_size}`，`code=0` 表示成功。
- **四级权限与数据域隔离**：角色 + 权限 + 菜单（含按钮级）三级 RBAC，数据域支持 `ALL` / `REGION` / `SELF` 三档。
- **JWT 鉴权**：访问令牌 + 刷新令牌，登录需图形验证码。

| 层 | 技术栈 |
| --- | --- |
| 后端 | Python 3.12、FastAPI、SQLAlchemy 2.x（async）、Alembic、Pydantic v2 + pydantic-settings |
| 数据库 | 开发 SQLite（aiosqlite）；生产 MySQL 8.0（pymysql） |
| 缓存 | 内存缓存 / Redis（redis-py），`CACHE_BACKEND` 二选一 |
| 鉴权 | python-jose（JWT）、passlib + bcrypt 4.0.1 |
| 其它后端依赖 | loguru、Pillow、openpyxl、python-multipart |
| 前端（PC / 移动） | Vue 3 + TypeScript + Vite，Axios 封装在各自 `src/api/http.ts` |

接口文档：后端启动后访问 `http://127.0.0.1:8000/docs`（Swagger）。

## 2. 目录结构

```
difu-admin/
├── app/                    后端应用
│   ├── api/v1/             路由与接口实现（含 mobile/ 移动端专属子包）
│   ├── cache/              缓存后端（memory / redis）
│   ├── core/               配置常量、依赖注入、统一响应、数据域、安全
│   ├── models/             SQLAlchemy 模型（共 19 张表）
│   ├── schemas/            Pydantic 请求/响应模型
│   ├── services/           业务服务层
│   ├── database.py         异步引擎与会话
│   ├── main.py             应用入口（lifespan、路由注册、CORS）
│   ├── seed.py             种子数据脚本（基础数据 / 业务示例数据）
│   └── config.py           全局配置（Settings，含双通道兜底逻辑）
├── frontend/               PC 管理端（Vue 3 + Vite，端口 5173）
│   └── src/api/http.ts     Axios 实例，baseURL 固定为 /api/v1
├── mobile/                 移动端 H5（Vue 3 + Vite，端口 5174）
│   └── src/api/http.ts     Axios 实例，baseURL 固定为 /api/v1
├── migrations/             Alembic 迁移（当前仅一份初始迁移，见第 9 章说明）
├── sql/                    建表与数据脚本（MySQL / SQLite 双方言）
├── data/                   本地 SQLite 数据库文件所在目录（不入库）
├── requirements.txt        后端依赖
├── alembic.ini             Alembic 配置
├── .env.example            环境变量示例（复制为 .env 后修改）
└── .gitignore
```

## 3. 环境准备

| 依赖 | 版本要求 | 说明 |
| --- | --- | --- |
| Python | 3.12（建议 3.11+） | 后端运行环境 |
| Node.js | ≥ 20.19（建议 22.x） | PC 端与移动端构建 |
| npm | 随 Node 附带 | 两前端各装一次依赖 |
| MySQL / Redis | MySQL 8.0 / Redis 6+ | **可选**，仅 `prod` 通道需要 |

SQLite 模式无需安装任何数据库，Python 自带的 `aiosqlite` 即可。

## 4. SQLite 模式从零启动

以下命令均以**项目根目录**为基准，三块需分别开三个终端窗口。

### 4.1 后端（8000）

```bash
# 1) 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2) 安装依赖
pip install -r requirements.txt

# 3) 生成配置文件（默认即为 dev + SQLite，可直接使用）
cp .env.example .env

# 4) 初始化数据库与基础账号（首次启动前执行一次）
python -m app.seed

# 5) 启动服务
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

启动后：

- 接口地址：`http://127.0.0.1:8000/api/v1`
- 接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`（返回当前运行通道、数据库类型与缓存后端）
- 数据库文件：`data/difu_dev.db`（首次连接时自动创建，`data/` 目录已被 `.gitignore` 排除）

### 4.2 PC 管理端（5173）

```bash
cd frontend
npm install
npm run dev
```

- 访问地址：`http://127.0.0.1:5173`
- 监听地址与端口在 `frontend/vite.config.ts` 中固定为 `127.0.0.1:5173`，并开启 `strictPort`（端口被占用时直接报错，不会自动换端口）
- 开发代理：`/api` → `http://127.0.0.1:8000`，前端代码内 `baseURL` 为 `/api/v1`，因此浏览器端不存在跨域问题

### 4.3 移动端 H5（5174）

```bash
cd mobile
npm install
npm run dev
```

- 访问地址：`http://127.0.0.1:5174`
- 监听地址在 `mobile/vite.config.ts` 中为 `0.0.0.0:5174`，因此同一局域网内的手机可用「电脑 IP + 5174」直接访问
- 开发代理：`/api` → `http://127.0.0.1:8000`；`baseURL` 同为 `/api/v1`
- 生产预览：`npm run preview`，端口 5175

> 两个前端共用同一套令牌键（`difu.access_token` / `difu.refresh_token`），但存储相互独立（不同端口），需各自登录。

## 5. 切换到 MySQL 与 Redis

所有通道切换只改 **`.env`**（由 `.env.example` 复制而来）或同名的系统环境变量，无需改代码。优先级：**环境变量 > .env > `app/config.py` 默认值**。

### 5.1 关键配置项

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `ENV_MODE` | `dev` | 仅 `dev` / `prod` 两个取值，决定兜底通道 |
| `DATABASE_URL` | 空 | 留空时按 `ENV_MODE` 自动取下方两条之一；也可直接填完整连接串 |
| `DEV_DATABASE_URL` | `sqlite+aiosqlite:///./data/difu_dev.db` | 定义在 `app/config.py`，dev 通道兜底值 |
| `PROD_DATABASE_URL` | MySQL 连接串（`app/config.py` 内，含占位主机与口令） | 定义在 `app/config.py`，prod 通道兜底值，**上线前必须替换** |
| `DB_ECHO` | `false` | 是否打印 SQL |
| `CACHE_BACKEND` | 空 | 留空自动选择；可强制填 `memory` 或 `redis` |
| `REDIS_URL` | `redis://<redis_host>:6379/3` | `CACHE_BACKEND=redis` 时必填 |
| `CACHE_PREFIX` | `difu` | 缓存键前缀 |
| `JWT_SECRET` | 示例值 | **必须替换**为随机长字符串（≥32 位） |
| `CAPTCHA_DEV_CODE` | `0000` | 仅 dev 生效的固定验证码，prod 请置空 |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 逗号分隔，见第 9 章注意事项 |

### 5.2 兜底逻辑（`app/config.py` 的 `_fill_defaults`）

1. `DATABASE_URL` 为空 → `ENV_MODE=dev` 用 `DEV_DATABASE_URL`（SQLite 文件），`ENV_MODE=prod` 用 `PROD_DATABASE_URL`（MySQL）。
2. `CACHE_BACKEND` 为空 → `ENV_MODE=dev` 用 `memory`，`ENV_MODE=prod` 用 `redis`。
3. 任一项显式赋值时，以显式值为准，不再兜底。因此「dev 环境连 MySQL」或「prod 环境用内存缓存」都可以靠显式赋值实现。

### 5.3 切换步骤

```bash
# 1) 修改 .env
ENV_MODE=prod
DATABASE_URL=mysql+pymysql://<db_user>:<db_password>@<db_host>:3306/<db_name>?charset=utf8mb4
CACHE_BACKEND=redis
REDIS_URL=redis://<redis_host>:6379/3
JWT_SECRET=<随机长字符串>

# 2) 在 MySQL 中创建空库（字符集必须 utf8mb4）
mysql -u <db_user> -p -e "CREATE DATABASE <db_name> DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"

# 3) 建表 + 灌基础数据（二选一，推荐方式 A）
# 方式 A：直接导入 sql 脚本
mysql -u <db_user> -p <db_name> < sql/01_schema_mysql.sql
mysql -u <db_user> -p <db_name> < sql/03_base_data.sql

# 方式 B：由应用建表（SQLAlchemy metadata 建表 + 种子数据）
python -m app.seed

# 4) 重启后端
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

注意：

- 切换后 `data/difu_dev.db` 不再被使用，但文件可以保留，重新设回 `dev` 即可复用。
- `alembic upgrade head` **不建议**作为建表手段，原因见第 9 章「迁移脚本滞后」。

## 6. `sql/` 目录：四份脚本

四份脚本均为纯 SQL，MySQL 与 SQLite 两套建表语句分开提供，数据脚本双方言通用（`03` / `04` 可直接在两种数据库执行）。

| 文件 | 用途 | 适用数据库 | 前置条件 |
| --- | --- | --- | --- |
| `01_schema_mysql.sql` | 建表 DDL，19 张表 + 索引 + 外键，InnoDB / utf8mb4 | MySQL 8.0 | 目标库已创建 |
| `02_schema_sqlite.sql` | 建表 DDL，同上，末尾带 `PRAGMA foreign_keys=ON` | SQLite 3.x | 无 |
| `03_base_data.sql` | 基础数据：10 角色、58 权限、195 角色权限关系、76 菜单（11 目录 + 23 菜单 + 42 按钮）、8 城隍、20 官员账号；业务表保持零数据 | MySQL 5.7+ / SQLite 3.x | 先执行对应 `01` 或 `02` |
| `04_test_data.sql` | 业务测试数据（生死簿、勾魂令、审判、刑罚、轮回、因果、文书、审批、移动端消息等），供功能演示与联调 | MySQL 5.7+ / SQLite 3.x | 先执行建表脚本 + `03_base_data.sql` |

### 导入命令

SQLite：

```bash
sqlite3 data/difu_dev.db < sql/02_schema_sqlite.sql
sqlite3 data/difu_dev.db < sql/03_base_data.sql
sqlite3 data/difu_dev.db < sql/04_test_data.sql      # 可选，测试数据
```

MySQL：

```bash
mysql -u <db_user> -p <db_name> < sql/01_schema_mysql.sql
mysql -u <db_user> -p <db_name> < sql/03_base_data.sql
mysql -u <db_user> -p <db_name> < sql/04_test_data.sql      # 可选，测试数据
```

执行顺序约束（脚本内部依赖外键）：

1. 建表脚本（`01` 或 `02`）必须先执行，且只能执行与目标数据库匹配的那一份。
2. `03` 中插入顺序为 角色 / 权限 / 菜单 → 角色权限关系 → 城隍 → 官员，手动拆分语句时不可打乱。
3. `04` 依赖 `03` 中的角色、城隍、官员数据；除审计日志外各业务表显式写入主键，**重复导入会因主键冲突失败**，重导前需先清空业务表（或直接删库重建）。
4. `02_schema_sqlite.sql` 建表后，每个连接都要开启外键约束（脚本末尾的 `PRAGMA` 只对当次连接生效，应用层已在连接事件中开启）。

## 7. 默认账号

以下账号由 `sql/03_base_data.sql` 与 `python -m app.seed` 生成，共 20 个。**除 admin 外，其余账号初始密码统一为 `123456`**，上线前请全部修改。

| 用户名 | 初始密码 | 姓名 | 角色（code） | 数据域 |
| --- | --- | --- | --- | --- |
| `admin` | `123123` | 酆都大帝 | SUPER_ADMIN | ALL |
| `fengdu_02` | `123456` | 北阴副帝 | SUPER_ADMIN | ALL |
| `dizang` | `123456` | 地藏王菩萨 | AUDITOR | ALL |
| `dizang_02` | `123456` | 道明和尚 | AUDITOR | ALL |
| `guidi_dong` | `123456` | 东方鬼帝 | REGION_ADMIN | REGION |
| `guidi_xi` | `123456` | 西方鬼帝 | REGION_ADMIN | REGION |
| `yanluo_01` | `123456` | 秦广王 | JUDGE | REGION |
| `yanluo_05` | `123456` | 阎罗王 | JUDGE | REGION |
| `cuiyu` | `123456` | 崔珏 | LIFEBOOK_ADMIN | ALL |
| `cuiyu_02` | `123456` | 掌簿司吏 | LIFEBOOK_ADMIN | ALL |
| `wuchang_hei` | `123456` | 黑无常 | FIELD_OFFICER | SELF |
| `wuchang_bai` | `123456` | 白无常 | FIELD_OFFICER | SELF |
| `niutou` | `123456` | 牛头 | ESCORT | SELF |
| `mamian` | `123456` | 马面 | ESCORT | SELF |
| `chenghuang_dong` | `123456` | 东岳城隍 | BRANCH_ADMIN | REGION |
| `chenghuang_luo` | `123456` | 洛水城隍 | BRANCH_ADMIN | REGION |
| `mengpo` | `123456` | 孟婆 | REINCARNATION_OFFICER | ALL |
| `mengpo_02` | `123456` | 孟婆侍女 | REINCARNATION_OFFICER | ALL |
| `ludong` | `123456` | 迷魂殿录供官 | REGISTRAR | REGION |
| `ludong_02` | `123456` | 孽镜台照镜官 | REGISTRAR | REGION |

角色与数据域对应关系：

| 角色 code | 角色名 | 数据域 |
| --- | --- | --- |
| SUPER_ADMIN | 酆都大帝 | ALL（拥有 `*` 超级权限） |
| AUDITOR | 地藏王 | ALL |
| REGION_ADMIN | 五方鬼帝 | REGION |
| JUDGE | 十殿阎罗 | REGION |
| LIFEBOOK_ADMIN | 崔珏 | ALL |
| FIELD_OFFICER | 黑白无常 | SELF |
| ESCORT | 牛头马面 | SELF |
| BRANCH_ADMIN | 城隍 | REGION |
| REINCARNATION_OFFICER | 孟婆 | ALL |
| REGISTRAR | 迷魂殿录供官 | REGION |

登录时需填写图形验证码，dev 通道可用固定验证码 `0000`（由 `CAPTCHA_DEV_CODE` 控制）。

## 8. 两种初始化方式

### 方式 A：导入 `sql/` 脚本（推荐用于已有数据库 / 生产）

适用于想完全掌控建表与数据内容的场景，见第 6 章命令。特点：

- 建表与数据完全由 SQL 决定，不依赖 Python 运行环境；
- 需要手动执行、手动按顺序导入；
- 只灌基础数据时导入 `01/02` + `03`；需要演示数据再追加 `04`。

### 方式 B：`python -m app.seed`（推荐用于本地快速起项目）

由 SQLAlchemy 模型直接建表，并写入与 `sql/03`（+`sql/04`）一致的数据。

```bash
python -m app.seed                # 建表 + 基础数据（幂等：已有基础数据则跳过并告警）
python -m app.seed --with-demo    # 建表 + 基础数据 + 业务示例数据（已有业务数据则跳过并告警）
python -m app.seed --force        # 清空全库后重建并灌入基础数据
python -m app.seed --force --with-demo   # 清空全库后重建，灌基础数据 + 业务示例数据
```

参数说明：

| 参数 | 作用 |
| --- | --- |
| 无参数 | 建表；库中无角色时灌入基础数据，已有则提示「已有基础数据」并跳过 |
| `--with-demo` | 追加业务示例数据；若业务表（生死簿）已有数据则跳过 |
| `--force` | 先清空全部业务表与基础表，再重新灌入；用于复位环境 |
| 未知参数 | 直接失败退出，不会静默忽略 |

补充：

- 执行完成后日志会打印超管账号（取自 `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD`）。
- 后端启动时若检测到空库，`lifespan` 会自动触发一次基础数据灌入（仅基础数据，不含业务示例数据）。
- 想回到「接近全新」的状态：删除 `data/difu_dev.db`（及其 `-shm` / `-wal`）后重新执行 `python -m app.seed`，即可只保留基础账号，无业务数据。

## 9. 常见问题

**1）端口被占用，前端启动直接报错**

两个前端都开了 `strictPort`，5173 / 5174 被占用时不会自动换端口。先查占用进程（`lsof -i :5173`）并结束，或修改对应 `vite.config.ts` 的 `server.port`（同时注意后端 `CORS_ORIGINS` 是否包含新端口）。后端 8000 端口同理。

**2）依赖安装慢或失败**

可换国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`；前端用 `npm install --registry=https://registry.npmmirror.com`。安装前确认 Node 版本满足 Vite 要求（≥ 20.19），版本过低会报 `crypto.hash is not a function` 之类的错误。

**3）bcrypt 版本导致登录报错**

`requirements.txt` 已把 `bcrypt` 钉在 `4.0.1`。若自行升级到 5.x，`passlib` 会因读取 `bcrypt.__about__` 失败而在登录时报错（`AttributeError: module 'bcrypt' has no attribute '__about__'`），请回退到 4.0.1。

**4）登录时验证码怎么填**

`ENV_MODE=dev` 且 `CAPTCHA_DEV_CODE=0000` 时，验证码填 `0000` 即可通过（仍会走验证码校验逻辑）。生产环境请把 `CAPTCHA_DEV_CODE` 置空，走真实验证码。

**5）SQLite 的 `-shm` / `-wal` 文件与「数据库被锁」**

SQLite 在 WAL 模式运行时会生成 `data/difu_dev.db-shm`、`data/difu_dev.db-wal`，属正常现象，已被 `.gitignore` 排除。出现 `database is locked` 时通常是另一个后端实例或 DBeaver/DB Browser 等工具占用了写锁，关闭多余连接后重试；仅备份数据库时请先停后端，或把三个文件一起复制。

**6）重置本地数据**

停止后端，删除 `data/difu_dev.db`（含 `-shm` / `-wal`），执行 `python -m app.seed` 即可得到只有基础账号、无业务数据的干净库。

**7）移动端（5174）直连后端出现跨域错误**

`.env.example` 中 `CORS_ORIGINS` 默认只包含 PC 端的 5173。移动端通过 Vite 代理访问 `/api`，默认不会有跨域问题；若改为直连 `http://127.0.0.1:8000`，需把 `http://127.0.0.1:5174` 追加进 `CORS_ORIGINS`。

**8）迁移脚本滞后**

`migrations/versions/` 目前只有一份初始迁移（覆盖 15 张表），而当前 ORM 模型共 19 张表（新增了移动端审批、设备、消息等表）。因此**建库请用 `sql/01` / `sql/02` 或 `python -m app.seed`，不要用 `alembic upgrade head`**，否则会缺表。后续若改用 Alembic 管理，需要先生成新的迁移版本。

**9）接口返回 401 / 403**

- 401：令牌缺失、过期或刷新失败，重新登录。
- 403：当前角色无该权限，或数据域（`SELF` / `REGION`）不覆盖目标数据，属正常权限拦截。

**10）上传 GitHub 前的注意点**

`.env`、`data/*.db`、`node_modules/`、`dist/` 均已被 `.gitignore` 排除；`app/config.py` 与 `.env.example` 中仍保留了示例主机/口令占位，请确认已替换为占位符形式（`<db_host>`、`<db_password>` 等），避免真实地址与口令进入仓库。
