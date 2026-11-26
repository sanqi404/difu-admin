-- =============================================================
-- difu-admin 建表脚本 / MySQL 8.0
-- 由 SQLAlchemy Base.metadata 自动编译生成，请勿手工修改；
-- 使用：mysql -u root -p < sql/01_schema_mysql.sql
-- 存储引擎 InnoDB，字符集 utf8mb4 / utf8mb4_unicode_ci
-- 说明：列级常量默认值编译为 DEFAULT；Python 侧 callable 默认值
--      （created_at / updated_at 的 utcnow 等）由应用层写入，DDL 不声明。
-- 说明：MySQL 的 TEXT/BLOB 不允许字面默认值，这些列的常量默认值省略。
-- =============================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `difu_admin` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `difu_admin`;

-- ----------------------------
-- Table: city_god
-- ----------------------------
CREATE TABLE `city_god` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`code` VARCHAR(32) NOT NULL COMMENT '网点编码', 
	`name` VARCHAR(64) NOT NULL COMMENT '网点名称', 
	`region` VARCHAR(32) NOT NULL COMMENT '所属鬼域', 
	`level` VARCHAR(32) NOT NULL DEFAULT '县城隍' COMMENT '网点级别', 
	`parent_id` INTEGER COMMENT '上级网点ID', 
	`city_god_name` VARCHAR(64) NOT NULL COMMENT '城隍神姓名', 
	`address` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '辖境地址', 
	`contact` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '联络方式', 
	`soul_capacity` INTEGER NOT NULL DEFAULT 1000 COMMENT '亡魂容量', 
	`soul_count` INTEGER NOT NULL DEFAULT 0 COMMENT '在册亡魂数', 
	`status` VARCHAR(32) NOT NULL DEFAULT '在职' COMMENT '网点状态', 
	`remark` TEXT NOT NULL COMMENT '备注', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_city_god` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_city_god_code` UNIQUE (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: menu
-- ----------------------------
CREATE TABLE `menu` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`parent_id` INTEGER COMMENT '父菜单ID', 
	`code` VARCHAR(64) NOT NULL COMMENT '菜单编码', 
	`name` VARCHAR(64) NOT NULL COMMENT '菜单名称', 
	`path` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '前端路由', 
	`component` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '组件路径', 
	`icon` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '图标', 
	`type` VARCHAR(32) NOT NULL DEFAULT '菜单' COMMENT '类型：目录/菜单', 
	`permission_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '访问所需权限编码', 
	`sort` INTEGER NOT NULL DEFAULT 0 COMMENT '排序', 
	`visible` BOOL NOT NULL DEFAULT 1 COMMENT '是否可见', 
	`status` VARCHAR(32) NOT NULL DEFAULT '启用' COMMENT '状态', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_menu` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_menu_code` UNIQUE (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: permission
-- ----------------------------
CREATE TABLE `permission` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`code` VARCHAR(64) NOT NULL COMMENT '权限编码', 
	`name` VARCHAR(64) NOT NULL COMMENT '权限名称', 
	`module` VARCHAR(32) NOT NULL COMMENT '所属模块', 
	`type` VARCHAR(32) NOT NULL DEFAULT 'api' COMMENT '类型：api/button', 
	`method` VARCHAR(16) NOT NULL DEFAULT '' COMMENT 'HTTP 方法', 
	`path` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '接口路径', 
	`description` TEXT NOT NULL COMMENT '说明', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_permission` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_permission_code` UNIQUE (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: role
-- ----------------------------
CREATE TABLE `role` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`code` VARCHAR(32) NOT NULL COMMENT '角色编码', 
	`name` VARCHAR(64) NOT NULL COMMENT '角色名称', 
	`description` TEXT NOT NULL COMMENT '角色描述', 
	`data_scope` VARCHAR(32) NOT NULL DEFAULT 'REGION' COMMENT '数据域：ALL/REGION/SELF', 
	`is_builtin` BOOL NOT NULL DEFAULT 0 COMMENT '是否内置', 
	`sort` INTEGER NOT NULL DEFAULT 0 COMMENT '排序', 
	`status` VARCHAR(32) NOT NULL DEFAULT '启用' COMMENT '状态', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_role` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_role_code` UNIQUE (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: officer
-- ----------------------------
CREATE TABLE `officer` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`username` VARCHAR(64) NOT NULL COMMENT '登录账号', 
	`password_hash` VARCHAR(255) NOT NULL COMMENT '密码散列', 
	`real_name` VARCHAR(64) NOT NULL COMMENT '姓名', 
	`title` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '仙职/岗位', 
	`role_id` INTEGER NOT NULL COMMENT '所属角色', 
	`region` VARCHAR(32) NOT NULL DEFAULT '中央' COMMENT '所属鬼域', 
	`city_god_id` INTEGER COMMENT '所属城隍网点', 
	`data_scope` VARCHAR(32) NOT NULL DEFAULT 'REGION' COMMENT '数据域：ALL/REGION/SELF', 
	`phone` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '联络方式', 
	`email` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '阴司信邮', 
	`status` VARCHAR(32) NOT NULL DEFAULT '在职' COMMENT '在职/停用/冻结', 
	`last_login_at` DATETIME COMMENT '最后登录(UTC)', 
	`last_login_ip` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '最后登录IP', 
	`remark` TEXT NOT NULL COMMENT '备注', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_officer` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_officer_username` UNIQUE (`username`), 
	CONSTRAINT `fk_officer_role_id_role` FOREIGN KEY(`role_id`) REFERENCES `role` (`id`), 
	CONSTRAINT `fk_officer_city_god_id_city_god` FOREIGN KEY(`city_god_id`) REFERENCES `city_god` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: role_permission
-- ----------------------------
CREATE TABLE `role_permission` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`role_id` INTEGER NOT NULL COMMENT '角色ID', 
	`permission_id` INTEGER NOT NULL COMMENT '权限ID', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_role_permission` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_role_permission_pair` UNIQUE (`role_id`, `permission_id`), 
	CONSTRAINT `fk_role_permission_role_id_role` FOREIGN KEY(`role_id`) REFERENCES `role` (`id`) ON DELETE CASCADE, 
	CONSTRAINT `fk_role_permission_permission_id_permission` FOREIGN KEY(`permission_id`) REFERENCES `permission` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: soul
-- ----------------------------
CREATE TABLE `soul` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`soul_no` VARCHAR(32) NOT NULL COMMENT '亡魂编号', 
	`name` VARCHAR(64) NOT NULL COMMENT '姓名', 
	`gender` VARCHAR(8) NOT NULL DEFAULT '男' COMMENT '性别', 
	`age` INTEGER NOT NULL DEFAULT 0 COMMENT '卒年', 
	`birth_date` DATETIME COMMENT '生辰', 
	`death_date` DATETIME COMMENT '死亡时间', 
	`native_place` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '籍贯', 
	`region` VARCHAR(32) NOT NULL DEFAULT '中央' COMMENT '所属鬼域（数据域隔离依据）', 
	`status` VARCHAR(32) NOT NULL DEFAULT '在册' COMMENT '亡魂状态', 
	`prev_status` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '冻结前状态（解冻回退用）', 
	`karma_score` INTEGER NOT NULL DEFAULT 0 COMMENT '孽镜台业力评分', 
	`sin_level` VARCHAR(32) NOT NULL DEFAULT '无' COMMENT '罪业等级', 
	`death_type` VARCHAR(32) NOT NULL DEFAULT '寿终正寝' COMMENT '死因类别', 
	`life_book_no` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '生死簿编号', 
	`city_god_id` INTEGER COMMENT '归属城隍网点', 
	`summon_order_id` INTEGER COMMENT '当前拘魂工单ID', 
	`current_location` VARCHAR(64) NOT NULL DEFAULT '阴司在册' COMMENT '当前所在（殿/狱/关）', 
	`is_deleted` BOOL NOT NULL DEFAULT 0 COMMENT '软删除标记', 
	`remark` TEXT NOT NULL COMMENT '备注', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_soul` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_soul_soul_no` UNIQUE (`soul_no`), 
	CONSTRAINT `fk_soul_city_god_id_city_god` FOREIGN KEY(`city_god_id`) REFERENCES `city_god` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: approval_request
-- ----------------------------
CREATE TABLE `approval_request` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`biz_type` VARCHAR(32) NOT NULL COMMENT '业务类型：生死簿添寿/判令还阳/减刑赦免/异常上报/工单撤销', 
	`biz_id` INTEGER NOT NULL DEFAULT 0 COMMENT '关联业务主键', 
	`title` VARCHAR(128) NOT NULL COMMENT '审批标题', 
	`summary` TEXT NOT NULL COMMENT '审批摘要', 
	`payload_json` TEXT NOT NULL COMMENT '业务载荷(JSON 字符串)', 
	`applicant_id` INTEGER COMMENT '申请人鬼差', 
	`status` VARCHAR(32) NOT NULL DEFAULT '审批中' COMMENT '当前环节，如 L1-城隍 / L2-酆都大帝；终态 已通过/已驳回/已撤销', 
	`deadline_at` DATETIME COMMENT '审批截止时间(UTC)', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_approval_request` PRIMARY KEY (`id`), 
	CONSTRAINT `fk_approval_request_applicant_id_officer` FOREIGN KEY(`applicant_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: audit_log
-- ----------------------------
CREATE TABLE `audit_log` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`officer_id` INTEGER COMMENT '操作鬼差', 
	`officer_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '操作鬼差姓名', 
	`role_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '操作角色', 
	`action` VARCHAR(64) NOT NULL COMMENT '动作：login/create/update/delete/transition...', 
	`module` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务模块', 
	`resource` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '资源类型', 
	`resource_id` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '资源ID', 
	`detail` TEXT NOT NULL COMMENT '操作详情', 
	`level` VARCHAR(32) NOT NULL DEFAULT '正常' COMMENT '正常/告警/篡改告警', 
	`ip` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '来源IP', 
	`user_agent` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '客户端标识', 
	`created_at` DATETIME NOT NULL COMMENT '操作时间(UTC)', 
	CONSTRAINT `pk_audit_log` PRIMARY KEY (`id`), 
	CONSTRAINT `fk_audit_log_officer_id_officer` FOREIGN KEY(`officer_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: karma_record
-- ----------------------------
CREATE TABLE `karma_record` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`karma_no` VARCHAR(32) NOT NULL COMMENT '业力编号', 
	`soul_id` INTEGER COMMENT '关联亡魂', 
	`soul_name` VARCHAR(64) NOT NULL COMMENT '亡魂姓名', 
	`region` VARCHAR(32) NOT NULL DEFAULT '中央' COMMENT '鬼域', 
	`karma_type` VARCHAR(32) NOT NULL DEFAULT '恶' COMMENT '善/恶/中性', 
	`category` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '业力类别', 
	`score` INTEGER NOT NULL DEFAULT 0 COMMENT '业力分值（正善负恶）', 
	`source` VARCHAR(32) NOT NULL DEFAULT '孽镜台' COMMENT '孽镜台/城隍上报/生死簿核定/人工录入', 
	`occurred_at` DATETIME COMMENT '业力发生时间(UTC)', 
	`recorder_id` INTEGER COMMENT '记录人', 
	`recorder_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '记录人姓名', 
	`description` TEXT NOT NULL COMMENT '业力描述', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_karma_record` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_karma_record_karma_no` UNIQUE (`karma_no`), 
	CONSTRAINT `fk_karma_record_soul_id_soul` FOREIGN KEY(`soul_id`) REFERENCES `soul` (`id`), 
	CONSTRAINT `fk_karma_record_recorder_id_officer` FOREIGN KEY(`recorder_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: life_book
-- ----------------------------
CREATE TABLE `life_book` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`book_no` VARCHAR(32) NOT NULL COMMENT '流水号', 
	`soul_id` INTEGER COMMENT '关联亡魂', 
	`soul_name` VARCHAR(64) NOT NULL COMMENT '亡魂姓名', 
	`action` VARCHAR(32) NOT NULL COMMENT '操作类型：录入/修改/复核/驳回/注销', 
	`lifespan_years` INTEGER NOT NULL DEFAULT 0 COMMENT '核定阳寿（年）', 
	`before_content` TEXT NOT NULL COMMENT '变更前内容', 
	`after_content` TEXT NOT NULL COMMENT '变更后内容', 
	`diff_desc` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '变更摘要', 
	`review_status` VARCHAR(32) NOT NULL DEFAULT '待复核' COMMENT '待复核/已复核/已驳回', 
	`operator_id` INTEGER COMMENT '录入人', 
	`operator_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '录入人姓名', 
	`reviewer_id` INTEGER COMMENT '复核人', 
	`reviewer_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '复核人姓名', 
	`reviewed_at` DATETIME COMMENT '复核时间(UTC)', 
	`review_comment` TEXT NOT NULL COMMENT '复核意见', 
	`is_tampered` INTEGER NOT NULL DEFAULT 0 COMMENT '疑似篡改标记', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_life_book` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_life_book_book_no` UNIQUE (`book_no`), 
	CONSTRAINT `fk_life_book_soul_id_soul` FOREIGN KEY(`soul_id`) REFERENCES `soul` (`id`), 
	CONSTRAINT `fk_life_book_operator_id_officer` FOREIGN KEY(`operator_id`) REFERENCES `officer` (`id`), 
	CONSTRAINT `fk_life_book_reviewer_id_officer` FOREIGN KEY(`reviewer_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: mobile_device
-- ----------------------------
CREATE TABLE `mobile_device` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`user_id` INTEGER COMMENT '绑定鬼差', 
	`device_id` VARCHAR(128) NOT NULL COMMENT '设备唯一标识', 
	`push_token` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '推送令牌', 
	`platform` VARCHAR(16) NOT NULL DEFAULT 'h5' COMMENT '平台：ios/android/h5', 
	`last_active_at` DATETIME NOT NULL COMMENT '最近活跃时间(UTC)', 
	CONSTRAINT `pk_mobile_device` PRIMARY KEY (`id`), 
	CONSTRAINT `fk_mobile_device_user_id_officer` FOREIGN KEY(`user_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: mobile_message
-- ----------------------------
CREATE TABLE `mobile_message` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`receiver_id` INTEGER COMMENT '接收鬼差', 
	`type` VARCHAR(32) NOT NULL DEFAULT '系统通知' COMMENT '消息类型：审批待办/审批结果/工单派发/系统通知', 
	`title` VARCHAR(128) NOT NULL COMMENT '消息标题', 
	`content` TEXT NOT NULL COMMENT '消息正文', 
	`biz_ref` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '业务引用，如 approval:12 / summon:3', 
	`is_read` BOOL NOT NULL DEFAULT 0 COMMENT '是否已读', 
	`priority` VARCHAR(16) NOT NULL DEFAULT '普通' COMMENT '优先级：普通/重要/紧急', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	CONSTRAINT `pk_mobile_message` PRIMARY KEY (`id`), 
	CONSTRAINT `fk_mobile_message_receiver_id_officer` FOREIGN KEY(`receiver_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: reincarnation
-- ----------------------------
CREATE TABLE `reincarnation` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`reinc_no` VARCHAR(32) NOT NULL COMMENT '轮回编号', 
	`soul_id` INTEGER COMMENT '投胎亡魂', 
	`soul_name` VARCHAR(64) NOT NULL COMMENT '亡魂姓名', 
	`region` VARCHAR(32) NOT NULL DEFAULT '中央' COMMENT '鬼域', 
	`path` VARCHAR(32) NOT NULL DEFAULT '人道' COMMENT '六道：天道/人道/阿修罗道/畜生道/饿鬼道/地狱道', 
	`target_world` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '投胎去向', 
	`karma_score` INTEGER NOT NULL DEFAULT 0 COMMENT '业力评分快照', 
	`soup_confirmed` BOOL NOT NULL DEFAULT 0 COMMENT '孟婆汤是否已饮（确认）', 
	`soup_at` DATETIME COMMENT '饮汤时间(UTC)', 
	`soup_operator` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '孟婆经办人', 
	`status` VARCHAR(32) NOT NULL DEFAULT '待办理' COMMENT '待办理/待投胎/已投胎/已归档/已撤销', 
	`scheduled_at` DATETIME COMMENT '预约投胎时间(UTC)', 
	`reincarnated_at` DATETIME COMMENT '实际投胎时间(UTC)', 
	`operator_id` INTEGER COMMENT '经办鬼差', 
	`remark` TEXT NOT NULL COMMENT '备注', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_reincarnation` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_reincarnation_reinc_no` UNIQUE (`reinc_no`), 
	CONSTRAINT `fk_reincarnation_soul_id_soul` FOREIGN KEY(`soul_id`) REFERENCES `soul` (`id`), 
	CONSTRAINT `fk_reincarnation_operator_id_officer` FOREIGN KEY(`operator_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: summon_order
-- ----------------------------
CREATE TABLE `summon_order` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`order_no` VARCHAR(32) NOT NULL COMMENT '工单号', 
	`soul_id` INTEGER COMMENT '目标亡魂', 
	`soul_name` VARCHAR(64) NOT NULL COMMENT '亡魂姓名', 
	`region` VARCHAR(32) NOT NULL DEFAULT '中央' COMMENT '鬼域', 
	`city_god_id` INTEGER COMMENT '归属城隍网点', 
	`assignee_id` INTEGER COMMENT '执行鬼差', 
	`assignee_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '执行鬼差姓名', 
	`priority` VARCHAR(32) NOT NULL DEFAULT '普通' COMMENT '普通/加急/特急', 
	`status` VARCHAR(32) NOT NULL DEFAULT '待派发' COMMENT '待派发/执行中/已完成/已超时/异常', 
	`death_type` VARCHAR(32) NOT NULL DEFAULT '寿终正寝' COMMENT '死因', 
	`location` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '拘魂地点', 
	`deadline_at` DATETIME COMMENT '限办期限(UTC)', 
	`started_at` DATETIME COMMENT '开始执行(UTC)', 
	`finished_at` DATETIME COMMENT '完成时间(UTC)', 
	`result` TEXT NOT NULL COMMENT '执行结果', 
	`abnormal_reason` TEXT NOT NULL COMMENT '异常说明', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_summon_order` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_summon_order_order_no` UNIQUE (`order_no`), 
	CONSTRAINT `fk_summon_order_soul_id_soul` FOREIGN KEY(`soul_id`) REFERENCES `soul` (`id`), 
	CONSTRAINT `fk_summon_order_city_god_id_city_god` FOREIGN KEY(`city_god_id`) REFERENCES `city_god` (`id`), 
	CONSTRAINT `fk_summon_order_assignee_id_officer` FOREIGN KEY(`assignee_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: trial_record
-- ----------------------------
CREATE TABLE `trial_record` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`trial_no` VARCHAR(32) NOT NULL COMMENT '审判编号', 
	`soul_id` INTEGER COMMENT '受审亡魂', 
	`soul_name` VARCHAR(64) NOT NULL COMMENT '亡魂姓名', 
	`court_level` INTEGER NOT NULL DEFAULT 1 COMMENT '殿级 1~10', 
	`region` VARCHAR(32) NOT NULL DEFAULT '中央' COMMENT '鬼域', 
	`judge_id` INTEGER COMMENT '主审阎罗', 
	`judge_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '主审阎罗姓名', 
	`karma_snapshot` INTEGER NOT NULL DEFAULT 0 COMMENT '孽镜台评分快照', 
	`guilt_desc` TEXT NOT NULL COMMENT '罪状详述', 
	`status` VARCHAR(32) NOT NULL DEFAULT '待审' COMMENT '待审/审理中/已结案/打回重审', 
	`verdict` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '判决', 
	`verdict_detail` TEXT NOT NULL COMMENT '判决详情', 
	`sentence_years` INTEGER NOT NULL DEFAULT 0 COMMENT '判处刑期（年）', 
	`hell_level` INTEGER NOT NULL DEFAULT 0 COMMENT '发配地狱层级 1~18', 
	`next_court_level` INTEGER NOT NULL DEFAULT 0 COMMENT '移送下一殿', 
	`started_at` DATETIME COMMENT '开庭时间(UTC)', 
	`closed_at` DATETIME COMMENT '结案时间(UTC)', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_trial_record` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_trial_record_trial_no` UNIQUE (`trial_no`), 
	CONSTRAINT `fk_trial_record_soul_id_soul` FOREIGN KEY(`soul_id`) REFERENCES `soul` (`id`), 
	CONSTRAINT `fk_trial_record_judge_id_officer` FOREIGN KEY(`judge_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: approval_step
-- ----------------------------
CREATE TABLE `approval_step` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`request_id` INTEGER NOT NULL COMMENT '审批单', 
	`step_no` INTEGER NOT NULL DEFAULT 1 COMMENT '环节序号', 
	`approver_id` INTEGER COMMENT '审批人', 
	`action` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT 'pending 未激活 / wait 待审批 / agree / reject / transfer', 
	`comment` TEXT NOT NULL COMMENT '批注', 
	`acted_at` DATETIME COMMENT '处理时间(UTC)', 
	CONSTRAINT `pk_approval_step` PRIMARY KEY (`id`), 
	CONSTRAINT `fk_approval_step_request_id_approval_request` FOREIGN KEY(`request_id`) REFERENCES `approval_request` (`id`), 
	CONSTRAINT `fk_approval_step_approver_id_officer` FOREIGN KEY(`approver_id`) REFERENCES `officer` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: document
-- ----------------------------
CREATE TABLE `document` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`doc_no` VARCHAR(32) NOT NULL COMMENT '文书编号', 
	`doc_type` VARCHAR(32) NOT NULL DEFAULT '路引' COMMENT '路引/拘票/判决书/轮回文书/还阳令/冻结令', 
	`title` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '文书标题', 
	`soul_id` INTEGER COMMENT '关联亡魂', 
	`soul_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '亡魂姓名', 
	`summon_order_id` INTEGER COMMENT '关联拘魂工单', 
	`city_god_id` INTEGER COMMENT '签发网点', 
	`content` TEXT NOT NULL COMMENT '文书正文', 
	`status` VARCHAR(32) NOT NULL DEFAULT '草稿' COMMENT '草稿/已签发/已核验/已作废', 
	`issued_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '签发人', 
	`issued_at` DATETIME COMMENT '签发时间(UTC)', 
	`verified_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '核验人', 
	`verified_at` DATETIME COMMENT '核验时间(UTC)', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_document` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_document_doc_no` UNIQUE (`doc_no`), 
	CONSTRAINT `fk_document_soul_id_soul` FOREIGN KEY(`soul_id`) REFERENCES `soul` (`id`), 
	CONSTRAINT `fk_document_summon_order_id_summon_order` FOREIGN KEY(`summon_order_id`) REFERENCES `summon_order` (`id`), 
	CONSTRAINT `fk_document_city_god_id_city_god` FOREIGN KEY(`city_god_id`) REFERENCES `city_god` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table: punishment
-- ----------------------------
CREATE TABLE `punishment` (
	`id` INTEGER NOT NULL AUTO_INCREMENT, 
	`punish_no` VARCHAR(32) NOT NULL COMMENT '刑期编号', 
	`soul_id` INTEGER COMMENT '服刑亡魂', 
	`soul_name` VARCHAR(64) NOT NULL COMMENT '亡魂姓名', 
	`trial_record_id` INTEGER COMMENT '来源判决', 
	`region` VARCHAR(32) NOT NULL DEFAULT '中央' COMMENT '鬼域', 
	`hell_level` INTEGER NOT NULL DEFAULT 1 COMMENT '地狱层级 1~18', 
	`hell_name` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '地狱名称', 
	`sentence_years` INTEGER NOT NULL DEFAULT 0 COMMENT '刑期（年）', 
	`reduced_years` INTEGER NOT NULL DEFAULT 0 COMMENT '已减免（年）', 
	`start_at` DATETIME COMMENT '起刑时间(UTC)', 
	`end_at` DATETIME COMMENT '刑满时间(UTC)', 
	`status` VARCHAR(32) NOT NULL DEFAULT '待执行' COMMENT '待执行/服刑中/已刑满/已转出/已减免', 
	`progress` INTEGER NOT NULL DEFAULT 0 COMMENT '服刑进度 0~100', 
	`executor_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '执刑鬼差', 
	`remark` TEXT NOT NULL COMMENT '备注', 
	`created_at` DATETIME NOT NULL COMMENT '创建时间(UTC)', 
	`updated_at` DATETIME NOT NULL COMMENT '更新时间(UTC)', 
	CONSTRAINT `pk_punishment` PRIMARY KEY (`id`), 
	CONSTRAINT `uq_punishment_punish_no` UNIQUE (`punish_no`), 
	CONSTRAINT `fk_punishment_soul_id_soul` FOREIGN KEY(`soul_id`) REFERENCES `soul` (`id`), 
	CONSTRAINT `fk_punishment_trial_record_id_trial_record` FOREIGN KEY(`trial_record_id`) REFERENCES `trial_record` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Indexes
-- ----------------------------
CREATE INDEX `ix_city_god_region` ON `city_god` (`region`);
CREATE INDEX `ix_menu_parent_id` ON `menu` (`parent_id`);
CREATE INDEX `ix_permission_module` ON `permission` (`module`);
CREATE INDEX `ix_officer_region` ON `officer` (`region`);
CREATE INDEX `ix_officer_role_id` ON `officer` (`role_id`);
CREATE INDEX `ix_role_permission_permission_id` ON `role_permission` (`permission_id`);
CREATE INDEX `ix_role_permission_role_id` ON `role_permission` (`role_id`);
CREATE INDEX `ix_soul_city_god_id` ON `soul` (`city_god_id`);
CREATE INDEX `ix_soul_death_date` ON `soul` (`death_date`);
CREATE INDEX `ix_soul_name` ON `soul` (`name`);
CREATE INDEX `ix_soul_region` ON `soul` (`region`);
CREATE INDEX `ix_soul_status` ON `soul` (`status`);
CREATE INDEX `ix_approval_request_applicant_id` ON `approval_request` (`applicant_id`);
CREATE INDEX `ix_approval_request_biz_id` ON `approval_request` (`biz_id`);
CREATE INDEX `ix_approval_request_biz_type` ON `approval_request` (`biz_type`);
CREATE INDEX `ix_approval_request_status` ON `approval_request` (`status`);
CREATE INDEX `ix_audit_log_created_at` ON `audit_log` (`created_at`);
CREATE INDEX `ix_audit_log_level` ON `audit_log` (`level`);
CREATE INDEX `ix_audit_log_module` ON `audit_log` (`module`);
CREATE INDEX `ix_audit_log_officer_id` ON `audit_log` (`officer_id`);
CREATE INDEX `ix_karma_record_category` ON `karma_record` (`category`);
CREATE INDEX `ix_karma_record_region` ON `karma_record` (`region`);
CREATE INDEX `ix_karma_record_soul_id` ON `karma_record` (`soul_id`);
CREATE INDEX `ix_karma_record_soul_name` ON `karma_record` (`soul_name`);
CREATE INDEX `ix_life_book_review_status` ON `life_book` (`review_status`);
CREATE INDEX `ix_life_book_soul_id` ON `life_book` (`soul_id`);
CREATE INDEX `ix_life_book_soul_name` ON `life_book` (`soul_name`);
CREATE UNIQUE INDEX `ix_mobile_device_device_id` ON `mobile_device` (`device_id`);
CREATE INDEX `ix_mobile_device_user_id` ON `mobile_device` (`user_id`);
CREATE INDEX `ix_mobile_message_biz_ref` ON `mobile_message` (`biz_ref`);
CREATE INDEX `ix_mobile_message_is_read` ON `mobile_message` (`is_read`);
CREATE INDEX `ix_mobile_message_receiver_id` ON `mobile_message` (`receiver_id`);
CREATE INDEX `ix_mobile_message_type` ON `mobile_message` (`type`);
CREATE INDEX `ix_reincarnation_path` ON `reincarnation` (`path`);
CREATE INDEX `ix_reincarnation_region` ON `reincarnation` (`region`);
CREATE INDEX `ix_reincarnation_soul_id` ON `reincarnation` (`soul_id`);
CREATE INDEX `ix_reincarnation_soul_name` ON `reincarnation` (`soul_name`);
CREATE INDEX `ix_reincarnation_status` ON `reincarnation` (`status`);
CREATE INDEX `ix_summon_order_assignee_id` ON `summon_order` (`assignee_id`);
CREATE INDEX `ix_summon_order_region` ON `summon_order` (`region`);
CREATE INDEX `ix_summon_order_soul_id` ON `summon_order` (`soul_id`);
CREATE INDEX `ix_summon_order_soul_name` ON `summon_order` (`soul_name`);
CREATE INDEX `ix_summon_order_status` ON `summon_order` (`status`);
CREATE INDEX `ix_trial_record_court_level` ON `trial_record` (`court_level`);
CREATE INDEX `ix_trial_record_region` ON `trial_record` (`region`);
CREATE INDEX `ix_trial_record_soul_id` ON `trial_record` (`soul_id`);
CREATE INDEX `ix_trial_record_soul_name` ON `trial_record` (`soul_name`);
CREATE INDEX `ix_trial_record_status` ON `trial_record` (`status`);
CREATE INDEX `ix_approval_step_action` ON `approval_step` (`action`);
CREATE INDEX `ix_approval_step_approver_id` ON `approval_step` (`approver_id`);
CREATE INDEX `ix_approval_step_request_id` ON `approval_step` (`request_id`);
CREATE INDEX `ix_approval_step_step_no` ON `approval_step` (`step_no`);
CREATE INDEX `ix_document_doc_type` ON `document` (`doc_type`);
CREATE INDEX `ix_document_soul_id` ON `document` (`soul_id`);
CREATE INDEX `ix_document_status` ON `document` (`status`);
CREATE INDEX `ix_punishment_hell_level` ON `punishment` (`hell_level`);
CREATE INDEX `ix_punishment_region` ON `punishment` (`region`);
CREATE INDEX `ix_punishment_soul_id` ON `punishment` (`soul_id`);
CREATE INDEX `ix_punishment_soul_name` ON `punishment` (`soul_name`);
CREATE INDEX `ix_punishment_status` ON `punishment` (`status`);

SET FOREIGN_KEY_CHECKS = 1;

