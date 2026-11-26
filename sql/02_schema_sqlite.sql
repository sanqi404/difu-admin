-- =============================================================
-- difu-admin 建表脚本 / SQLite 3
-- 由 SQLAlchemy Base.metadata 自动编译生成，请勿手工修改；
-- 使用：sqlite3 data/difu_dev.db < sql/02_schema_sqlite.sql
-- 说明：列级常量默认值编译为 DEFAULT；Python 侧 callable 默认值
--      （created_at / updated_at 的 utcnow 等）由应用层写入，DDL 不声明。
-- =============================================================
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ----------------------------
-- Table: city_god
-- ----------------------------
CREATE TABLE "city_god" (
	"id" INTEGER NOT NULL, 
	"code" VARCHAR(32) NOT NULL, 
	"name" VARCHAR(64) NOT NULL, 
	"region" VARCHAR(32) NOT NULL, 
	"level" VARCHAR(32) NOT NULL DEFAULT '县城隍', 
	"parent_id" INTEGER, 
	"city_god_name" VARCHAR(64) NOT NULL, 
	"address" VARCHAR(255) NOT NULL DEFAULT '', 
	"contact" VARCHAR(64) NOT NULL DEFAULT '', 
	"soul_capacity" INTEGER NOT NULL DEFAULT 1000, 
	"soul_count" INTEGER NOT NULL DEFAULT 0, 
	"status" VARCHAR(32) NOT NULL DEFAULT '在职', 
	"remark" TEXT NOT NULL DEFAULT '', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_city_god" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_city_god_code" UNIQUE ("code")
);

-- ----------------------------
-- Table: menu
-- ----------------------------
CREATE TABLE "menu" (
	"id" INTEGER NOT NULL, 
	"parent_id" INTEGER, 
	"code" VARCHAR(64) NOT NULL, 
	"name" VARCHAR(64) NOT NULL, 
	"path" VARCHAR(255) NOT NULL DEFAULT '', 
	"component" VARCHAR(255) NOT NULL DEFAULT '', 
	"icon" VARCHAR(64) NOT NULL DEFAULT '', 
	"type" VARCHAR(32) NOT NULL DEFAULT '菜单', 
	"permission_code" VARCHAR(64) NOT NULL DEFAULT '', 
	"sort" INTEGER NOT NULL DEFAULT 0, 
	"visible" BOOLEAN NOT NULL DEFAULT 1, 
	"status" VARCHAR(32) NOT NULL DEFAULT '启用', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_menu" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_menu_code" UNIQUE ("code")
);

-- ----------------------------
-- Table: permission
-- ----------------------------
CREATE TABLE "permission" (
	"id" INTEGER NOT NULL, 
	"code" VARCHAR(64) NOT NULL, 
	"name" VARCHAR(64) NOT NULL, 
	"module" VARCHAR(32) NOT NULL, 
	"type" VARCHAR(32) NOT NULL DEFAULT 'api', 
	"method" VARCHAR(16) NOT NULL DEFAULT '', 
	"path" VARCHAR(255) NOT NULL DEFAULT '', 
	"description" TEXT NOT NULL DEFAULT '', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_permission" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_permission_code" UNIQUE ("code")
);

-- ----------------------------
-- Table: role
-- ----------------------------
CREATE TABLE "role" (
	"id" INTEGER NOT NULL, 
	"code" VARCHAR(32) NOT NULL, 
	"name" VARCHAR(64) NOT NULL, 
	"description" TEXT NOT NULL DEFAULT '', 
	"data_scope" VARCHAR(32) NOT NULL DEFAULT 'REGION', 
	"is_builtin" BOOLEAN NOT NULL DEFAULT 0, 
	"sort" INTEGER NOT NULL DEFAULT 0, 
	"status" VARCHAR(32) NOT NULL DEFAULT '启用', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_role" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_role_code" UNIQUE ("code")
);

-- ----------------------------
-- Table: officer
-- ----------------------------
CREATE TABLE "officer" (
	"id" INTEGER NOT NULL, 
	"username" VARCHAR(64) NOT NULL, 
	"password_hash" VARCHAR(255) NOT NULL, 
	"real_name" VARCHAR(64) NOT NULL, 
	"title" VARCHAR(64) NOT NULL DEFAULT '', 
	"role_id" INTEGER NOT NULL, 
	"region" VARCHAR(32) NOT NULL DEFAULT '中央', 
	"city_god_id" INTEGER, 
	"data_scope" VARCHAR(32) NOT NULL DEFAULT 'REGION', 
	"phone" VARCHAR(32) NOT NULL DEFAULT '', 
	"email" VARCHAR(128) NOT NULL DEFAULT '', 
	"status" VARCHAR(32) NOT NULL DEFAULT '在职', 
	"last_login_at" DATETIME, 
	"last_login_ip" VARCHAR(64) NOT NULL DEFAULT '', 
	"remark" TEXT NOT NULL DEFAULT '', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_officer" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_officer_username" UNIQUE ("username"), 
	CONSTRAINT "fk_officer_role_id_role" FOREIGN KEY("role_id") REFERENCES "role" ("id"), 
	CONSTRAINT "fk_officer_city_god_id_city_god" FOREIGN KEY("city_god_id") REFERENCES "city_god" ("id")
);

-- ----------------------------
-- Table: role_permission
-- ----------------------------
CREATE TABLE "role_permission" (
	"id" INTEGER NOT NULL, 
	"role_id" INTEGER NOT NULL, 
	"permission_id" INTEGER NOT NULL, 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_role_permission" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_role_permission_pair" UNIQUE ("role_id", "permission_id"), 
	CONSTRAINT "fk_role_permission_role_id_role" FOREIGN KEY("role_id") REFERENCES "role" ("id") ON DELETE CASCADE, 
	CONSTRAINT "fk_role_permission_permission_id_permission" FOREIGN KEY("permission_id") REFERENCES "permission" ("id") ON DELETE CASCADE
);

-- ----------------------------
-- Table: soul
-- ----------------------------
CREATE TABLE "soul" (
	"id" INTEGER NOT NULL, 
	"soul_no" VARCHAR(32) NOT NULL, 
	"name" VARCHAR(64) NOT NULL, 
	"gender" VARCHAR(8) NOT NULL DEFAULT '男', 
	"age" INTEGER NOT NULL DEFAULT 0, 
	"birth_date" DATETIME, 
	"death_date" DATETIME, 
	"native_place" VARCHAR(128) NOT NULL DEFAULT '', 
	"region" VARCHAR(32) NOT NULL DEFAULT '中央', 
	"status" VARCHAR(32) NOT NULL DEFAULT '在册', 
	"prev_status" VARCHAR(32) NOT NULL DEFAULT '', 
	"karma_score" INTEGER NOT NULL DEFAULT 0, 
	"sin_level" VARCHAR(32) NOT NULL DEFAULT '无', 
	"death_type" VARCHAR(32) NOT NULL DEFAULT '寿终正寝', 
	"life_book_no" VARCHAR(32) NOT NULL DEFAULT '', 
	"city_god_id" INTEGER, 
	"summon_order_id" INTEGER, 
	"current_location" VARCHAR(64) NOT NULL DEFAULT '阴司在册', 
	"is_deleted" BOOLEAN NOT NULL DEFAULT 0, 
	"remark" TEXT NOT NULL DEFAULT '', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_soul" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_soul_soul_no" UNIQUE ("soul_no"), 
	CONSTRAINT "fk_soul_city_god_id_city_god" FOREIGN KEY("city_god_id") REFERENCES "city_god" ("id")
);

-- ----------------------------
-- Table: approval_request
-- ----------------------------
CREATE TABLE "approval_request" (
	"id" INTEGER NOT NULL, 
	"biz_type" VARCHAR(32) NOT NULL, 
	"biz_id" INTEGER NOT NULL DEFAULT 0, 
	"title" VARCHAR(128) NOT NULL, 
	"summary" TEXT NOT NULL DEFAULT '', 
	"payload_json" TEXT NOT NULL DEFAULT '', 
	"applicant_id" INTEGER, 
	"status" VARCHAR(32) NOT NULL DEFAULT '审批中', 
	"deadline_at" DATETIME, 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_approval_request" PRIMARY KEY ("id"), 
	CONSTRAINT "fk_approval_request_applicant_id_officer" FOREIGN KEY("applicant_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: audit_log
-- ----------------------------
CREATE TABLE "audit_log" (
	"id" INTEGER NOT NULL, 
	"officer_id" INTEGER, 
	"officer_name" VARCHAR(64) NOT NULL DEFAULT '', 
	"role_name" VARCHAR(64) NOT NULL DEFAULT '', 
	"action" VARCHAR(64) NOT NULL, 
	"module" VARCHAR(64) NOT NULL DEFAULT '', 
	"resource" VARCHAR(64) NOT NULL DEFAULT '', 
	"resource_id" VARCHAR(64) NOT NULL DEFAULT '', 
	"detail" TEXT NOT NULL DEFAULT '', 
	"level" VARCHAR(32) NOT NULL DEFAULT '正常', 
	"ip" VARCHAR(64) NOT NULL DEFAULT '', 
	"user_agent" VARCHAR(255) NOT NULL DEFAULT '', 
	"created_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_audit_log" PRIMARY KEY ("id"), 
	CONSTRAINT "fk_audit_log_officer_id_officer" FOREIGN KEY("officer_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: karma_record
-- ----------------------------
CREATE TABLE "karma_record" (
	"id" INTEGER NOT NULL, 
	"karma_no" VARCHAR(32) NOT NULL, 
	"soul_id" INTEGER, 
	"soul_name" VARCHAR(64) NOT NULL, 
	"region" VARCHAR(32) NOT NULL DEFAULT '中央', 
	"karma_type" VARCHAR(32) NOT NULL DEFAULT '恶', 
	"category" VARCHAR(32) NOT NULL DEFAULT '', 
	"score" INTEGER NOT NULL DEFAULT 0, 
	"source" VARCHAR(32) NOT NULL DEFAULT '孽镜台', 
	"occurred_at" DATETIME, 
	"recorder_id" INTEGER, 
	"recorder_name" VARCHAR(64) NOT NULL DEFAULT '', 
	"description" TEXT NOT NULL DEFAULT '', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_karma_record" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_karma_record_karma_no" UNIQUE ("karma_no"), 
	CONSTRAINT "fk_karma_record_soul_id_soul" FOREIGN KEY("soul_id") REFERENCES "soul" ("id"), 
	CONSTRAINT "fk_karma_record_recorder_id_officer" FOREIGN KEY("recorder_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: life_book
-- ----------------------------
CREATE TABLE "life_book" (
	"id" INTEGER NOT NULL, 
	"book_no" VARCHAR(32) NOT NULL, 
	"soul_id" INTEGER, 
	"soul_name" VARCHAR(64) NOT NULL, 
	"action" VARCHAR(32) NOT NULL, 
	"lifespan_years" INTEGER NOT NULL DEFAULT 0, 
	"before_content" TEXT NOT NULL DEFAULT '', 
	"after_content" TEXT NOT NULL DEFAULT '', 
	"diff_desc" VARCHAR(255) NOT NULL DEFAULT '', 
	"review_status" VARCHAR(32) NOT NULL DEFAULT '待复核', 
	"operator_id" INTEGER, 
	"operator_name" VARCHAR(64) NOT NULL DEFAULT '', 
	"reviewer_id" INTEGER, 
	"reviewer_name" VARCHAR(64) NOT NULL DEFAULT '', 
	"reviewed_at" DATETIME, 
	"review_comment" TEXT NOT NULL DEFAULT '', 
	"is_tampered" INTEGER NOT NULL DEFAULT 0, 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_life_book" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_life_book_book_no" UNIQUE ("book_no"), 
	CONSTRAINT "fk_life_book_soul_id_soul" FOREIGN KEY("soul_id") REFERENCES "soul" ("id"), 
	CONSTRAINT "fk_life_book_operator_id_officer" FOREIGN KEY("operator_id") REFERENCES "officer" ("id"), 
	CONSTRAINT "fk_life_book_reviewer_id_officer" FOREIGN KEY("reviewer_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: mobile_device
-- ----------------------------
CREATE TABLE "mobile_device" (
	"id" INTEGER NOT NULL, 
	"user_id" INTEGER, 
	"device_id" VARCHAR(128) NOT NULL, 
	"push_token" VARCHAR(255) NOT NULL DEFAULT '', 
	"platform" VARCHAR(16) NOT NULL DEFAULT 'h5', 
	"last_active_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_mobile_device" PRIMARY KEY ("id"), 
	CONSTRAINT "fk_mobile_device_user_id_officer" FOREIGN KEY("user_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: mobile_message
-- ----------------------------
CREATE TABLE "mobile_message" (
	"id" INTEGER NOT NULL, 
	"receiver_id" INTEGER, 
	"type" VARCHAR(32) NOT NULL DEFAULT '系统通知', 
	"title" VARCHAR(128) NOT NULL, 
	"content" TEXT NOT NULL DEFAULT '', 
	"biz_ref" VARCHAR(64) NOT NULL DEFAULT '', 
	"is_read" BOOLEAN NOT NULL DEFAULT 0, 
	"priority" VARCHAR(16) NOT NULL DEFAULT '普通', 
	"created_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_mobile_message" PRIMARY KEY ("id"), 
	CONSTRAINT "fk_mobile_message_receiver_id_officer" FOREIGN KEY("receiver_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: reincarnation
-- ----------------------------
CREATE TABLE "reincarnation" (
	"id" INTEGER NOT NULL, 
	"reinc_no" VARCHAR(32) NOT NULL, 
	"soul_id" INTEGER, 
	"soul_name" VARCHAR(64) NOT NULL, 
	"region" VARCHAR(32) NOT NULL DEFAULT '中央', 
	"path" VARCHAR(32) NOT NULL DEFAULT '人道', 
	"target_world" VARCHAR(128) NOT NULL DEFAULT '', 
	"karma_score" INTEGER NOT NULL DEFAULT 0, 
	"soup_confirmed" BOOLEAN NOT NULL DEFAULT 0, 
	"soup_at" DATETIME, 
	"soup_operator" VARCHAR(64) NOT NULL DEFAULT '', 
	"status" VARCHAR(32) NOT NULL DEFAULT '待办理', 
	"scheduled_at" DATETIME, 
	"reincarnated_at" DATETIME, 
	"operator_id" INTEGER, 
	"remark" TEXT NOT NULL DEFAULT '', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_reincarnation" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_reincarnation_reinc_no" UNIQUE ("reinc_no"), 
	CONSTRAINT "fk_reincarnation_soul_id_soul" FOREIGN KEY("soul_id") REFERENCES "soul" ("id"), 
	CONSTRAINT "fk_reincarnation_operator_id_officer" FOREIGN KEY("operator_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: summon_order
-- ----------------------------
CREATE TABLE "summon_order" (
	"id" INTEGER NOT NULL, 
	"order_no" VARCHAR(32) NOT NULL, 
	"soul_id" INTEGER, 
	"soul_name" VARCHAR(64) NOT NULL, 
	"region" VARCHAR(32) NOT NULL DEFAULT '中央', 
	"city_god_id" INTEGER, 
	"assignee_id" INTEGER, 
	"assignee_name" VARCHAR(64) NOT NULL DEFAULT '', 
	"priority" VARCHAR(32) NOT NULL DEFAULT '普通', 
	"status" VARCHAR(32) NOT NULL DEFAULT '待派发', 
	"death_type" VARCHAR(32) NOT NULL DEFAULT '寿终正寝', 
	"location" VARCHAR(255) NOT NULL DEFAULT '', 
	"deadline_at" DATETIME, 
	"started_at" DATETIME, 
	"finished_at" DATETIME, 
	"result" TEXT NOT NULL DEFAULT '', 
	"abnormal_reason" TEXT NOT NULL DEFAULT '', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_summon_order" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_summon_order_order_no" UNIQUE ("order_no"), 
	CONSTRAINT "fk_summon_order_soul_id_soul" FOREIGN KEY("soul_id") REFERENCES "soul" ("id"), 
	CONSTRAINT "fk_summon_order_city_god_id_city_god" FOREIGN KEY("city_god_id") REFERENCES "city_god" ("id"), 
	CONSTRAINT "fk_summon_order_assignee_id_officer" FOREIGN KEY("assignee_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: trial_record
-- ----------------------------
CREATE TABLE "trial_record" (
	"id" INTEGER NOT NULL, 
	"trial_no" VARCHAR(32) NOT NULL, 
	"soul_id" INTEGER, 
	"soul_name" VARCHAR(64) NOT NULL, 
	"court_level" INTEGER NOT NULL DEFAULT 1, 
	"region" VARCHAR(32) NOT NULL DEFAULT '中央', 
	"judge_id" INTEGER, 
	"judge_name" VARCHAR(64) NOT NULL DEFAULT '', 
	"karma_snapshot" INTEGER NOT NULL DEFAULT 0, 
	"guilt_desc" TEXT NOT NULL DEFAULT '', 
	"status" VARCHAR(32) NOT NULL DEFAULT '待审', 
	"verdict" VARCHAR(32) NOT NULL DEFAULT '', 
	"verdict_detail" TEXT NOT NULL DEFAULT '', 
	"sentence_years" INTEGER NOT NULL DEFAULT 0, 
	"hell_level" INTEGER NOT NULL DEFAULT 0, 
	"next_court_level" INTEGER NOT NULL DEFAULT 0, 
	"started_at" DATETIME, 
	"closed_at" DATETIME, 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_trial_record" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_trial_record_trial_no" UNIQUE ("trial_no"), 
	CONSTRAINT "fk_trial_record_soul_id_soul" FOREIGN KEY("soul_id") REFERENCES "soul" ("id"), 
	CONSTRAINT "fk_trial_record_judge_id_officer" FOREIGN KEY("judge_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: approval_step
-- ----------------------------
CREATE TABLE "approval_step" (
	"id" INTEGER NOT NULL, 
	"request_id" INTEGER NOT NULL, 
	"step_no" INTEGER NOT NULL DEFAULT 1, 
	"approver_id" INTEGER, 
	"action" VARCHAR(16) NOT NULL DEFAULT 'pending', 
	"comment" TEXT NOT NULL DEFAULT '', 
	"acted_at" DATETIME, 
	CONSTRAINT "pk_approval_step" PRIMARY KEY ("id"), 
	CONSTRAINT "fk_approval_step_request_id_approval_request" FOREIGN KEY("request_id") REFERENCES "approval_request" ("id"), 
	CONSTRAINT "fk_approval_step_approver_id_officer" FOREIGN KEY("approver_id") REFERENCES "officer" ("id")
);

-- ----------------------------
-- Table: document
-- ----------------------------
CREATE TABLE "document" (
	"id" INTEGER NOT NULL, 
	"doc_no" VARCHAR(32) NOT NULL, 
	"doc_type" VARCHAR(32) NOT NULL DEFAULT '路引', 
	"title" VARCHAR(128) NOT NULL DEFAULT '', 
	"soul_id" INTEGER, 
	"soul_name" VARCHAR(64) NOT NULL DEFAULT '', 
	"summon_order_id" INTEGER, 
	"city_god_id" INTEGER, 
	"content" TEXT NOT NULL DEFAULT '', 
	"status" VARCHAR(32) NOT NULL DEFAULT '草稿', 
	"issued_by" VARCHAR(64) NOT NULL DEFAULT '', 
	"issued_at" DATETIME, 
	"verified_by" VARCHAR(64) NOT NULL DEFAULT '', 
	"verified_at" DATETIME, 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_document" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_document_doc_no" UNIQUE ("doc_no"), 
	CONSTRAINT "fk_document_soul_id_soul" FOREIGN KEY("soul_id") REFERENCES "soul" ("id"), 
	CONSTRAINT "fk_document_summon_order_id_summon_order" FOREIGN KEY("summon_order_id") REFERENCES "summon_order" ("id"), 
	CONSTRAINT "fk_document_city_god_id_city_god" FOREIGN KEY("city_god_id") REFERENCES "city_god" ("id")
);

-- ----------------------------
-- Table: punishment
-- ----------------------------
CREATE TABLE "punishment" (
	"id" INTEGER NOT NULL, 
	"punish_no" VARCHAR(32) NOT NULL, 
	"soul_id" INTEGER, 
	"soul_name" VARCHAR(64) NOT NULL, 
	"trial_record_id" INTEGER, 
	"region" VARCHAR(32) NOT NULL DEFAULT '中央', 
	"hell_level" INTEGER NOT NULL DEFAULT 1, 
	"hell_name" VARCHAR(32) NOT NULL DEFAULT '', 
	"sentence_years" INTEGER NOT NULL DEFAULT 0, 
	"reduced_years" INTEGER NOT NULL DEFAULT 0, 
	"start_at" DATETIME, 
	"end_at" DATETIME, 
	"status" VARCHAR(32) NOT NULL DEFAULT '待执行', 
	"progress" INTEGER NOT NULL DEFAULT 0, 
	"executor_name" VARCHAR(64) NOT NULL DEFAULT '', 
	"remark" TEXT NOT NULL DEFAULT '', 
	"created_at" DATETIME NOT NULL, 
	"updated_at" DATETIME NOT NULL, 
	CONSTRAINT "pk_punishment" PRIMARY KEY ("id"), 
	CONSTRAINT "uq_punishment_punish_no" UNIQUE ("punish_no"), 
	CONSTRAINT "fk_punishment_soul_id_soul" FOREIGN KEY("soul_id") REFERENCES "soul" ("id"), 
	CONSTRAINT "fk_punishment_trial_record_id_trial_record" FOREIGN KEY("trial_record_id") REFERENCES "trial_record" ("id")
);

-- ----------------------------
-- Indexes
-- ----------------------------
CREATE INDEX "ix_city_god_region" ON "city_god" ("region");
CREATE INDEX "ix_menu_parent_id" ON "menu" ("parent_id");
CREATE INDEX "ix_permission_module" ON "permission" ("module");
CREATE INDEX "ix_officer_region" ON "officer" ("region");
CREATE INDEX "ix_officer_role_id" ON "officer" ("role_id");
CREATE INDEX "ix_role_permission_permission_id" ON "role_permission" ("permission_id");
CREATE INDEX "ix_role_permission_role_id" ON "role_permission" ("role_id");
CREATE INDEX "ix_soul_city_god_id" ON "soul" ("city_god_id");
CREATE INDEX "ix_soul_death_date" ON "soul" ("death_date");
CREATE INDEX "ix_soul_name" ON "soul" ("name");
CREATE INDEX "ix_soul_region" ON "soul" ("region");
CREATE INDEX "ix_soul_status" ON "soul" ("status");
CREATE INDEX "ix_approval_request_applicant_id" ON "approval_request" ("applicant_id");
CREATE INDEX "ix_approval_request_biz_id" ON "approval_request" ("biz_id");
CREATE INDEX "ix_approval_request_biz_type" ON "approval_request" ("biz_type");
CREATE INDEX "ix_approval_request_status" ON "approval_request" ("status");
CREATE INDEX "ix_audit_log_created_at" ON "audit_log" ("created_at");
CREATE INDEX "ix_audit_log_level" ON "audit_log" ("level");
CREATE INDEX "ix_audit_log_module" ON "audit_log" ("module");
CREATE INDEX "ix_audit_log_officer_id" ON "audit_log" ("officer_id");
CREATE INDEX "ix_karma_record_category" ON "karma_record" ("category");
CREATE INDEX "ix_karma_record_region" ON "karma_record" ("region");
CREATE INDEX "ix_karma_record_soul_id" ON "karma_record" ("soul_id");
CREATE INDEX "ix_karma_record_soul_name" ON "karma_record" ("soul_name");
CREATE INDEX "ix_life_book_review_status" ON "life_book" ("review_status");
CREATE INDEX "ix_life_book_soul_id" ON "life_book" ("soul_id");
CREATE INDEX "ix_life_book_soul_name" ON "life_book" ("soul_name");
CREATE UNIQUE INDEX "ix_mobile_device_device_id" ON "mobile_device" ("device_id");
CREATE INDEX "ix_mobile_device_user_id" ON "mobile_device" ("user_id");
CREATE INDEX "ix_mobile_message_biz_ref" ON "mobile_message" ("biz_ref");
CREATE INDEX "ix_mobile_message_is_read" ON "mobile_message" ("is_read");
CREATE INDEX "ix_mobile_message_receiver_id" ON "mobile_message" ("receiver_id");
CREATE INDEX "ix_mobile_message_type" ON "mobile_message" ("type");
CREATE INDEX "ix_reincarnation_path" ON "reincarnation" ("path");
CREATE INDEX "ix_reincarnation_region" ON "reincarnation" ("region");
CREATE INDEX "ix_reincarnation_soul_id" ON "reincarnation" ("soul_id");
CREATE INDEX "ix_reincarnation_soul_name" ON "reincarnation" ("soul_name");
CREATE INDEX "ix_reincarnation_status" ON "reincarnation" ("status");
CREATE INDEX "ix_summon_order_assignee_id" ON "summon_order" ("assignee_id");
CREATE INDEX "ix_summon_order_region" ON "summon_order" ("region");
CREATE INDEX "ix_summon_order_soul_id" ON "summon_order" ("soul_id");
CREATE INDEX "ix_summon_order_soul_name" ON "summon_order" ("soul_name");
CREATE INDEX "ix_summon_order_status" ON "summon_order" ("status");
CREATE INDEX "ix_trial_record_court_level" ON "trial_record" ("court_level");
CREATE INDEX "ix_trial_record_region" ON "trial_record" ("region");
CREATE INDEX "ix_trial_record_soul_id" ON "trial_record" ("soul_id");
CREATE INDEX "ix_trial_record_soul_name" ON "trial_record" ("soul_name");
CREATE INDEX "ix_trial_record_status" ON "trial_record" ("status");
CREATE INDEX "ix_approval_step_action" ON "approval_step" ("action");
CREATE INDEX "ix_approval_step_approver_id" ON "approval_step" ("approver_id");
CREATE INDEX "ix_approval_step_request_id" ON "approval_step" ("request_id");
CREATE INDEX "ix_approval_step_step_no" ON "approval_step" ("step_no");
CREATE INDEX "ix_document_doc_type" ON "document" ("doc_type");
CREATE INDEX "ix_document_soul_id" ON "document" ("soul_id");
CREATE INDEX "ix_document_status" ON "document" ("status");
CREATE INDEX "ix_punishment_hell_level" ON "punishment" ("hell_level");
CREATE INDEX "ix_punishment_region" ON "punishment" ("region");
CREATE INDEX "ix_punishment_soul_id" ON "punishment" ("soul_id");
CREATE INDEX "ix_punishment_soul_name" ON "punishment" ("soul_name");
CREATE INDEX "ix_punishment_status" ON "punishment" ("status");

COMMIT;

