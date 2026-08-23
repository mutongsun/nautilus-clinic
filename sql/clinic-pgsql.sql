-- ============================================================
-- Nautilus Clinic 业务底座：Agent 对接补充表（真实采购链路）
-- 库存表结构与既有实体 NautilusInventory 严格对齐；
-- 采购订单表为新增（下游级幂等：idempotency_key 唯一约束）
-- ============================================================

-- ----------------------------
-- 药品库存表（对齐 com.ruoyi.clinic.domain.NautilusInventory）
-- ----------------------------
DROP TABLE IF EXISTS "ruoyi"."nautilus_inventory";
CREATE TABLE "ruoyi"."nautilus_inventory" (
    "item_id"         BIGINT PRIMARY KEY,
    "item_code"       VARCHAR(64) DEFAULT '',
    "item_name"       VARCHAR(128) NOT NULL,
    "current_stock"   INTEGER DEFAULT 0,
    "alert_threshold" INTEGER DEFAULT 10,
    "category_dict"   VARCHAR(32) DEFAULT '0',
    "price"           NUMERIC(12,2) DEFAULT 0,
    "batch_no"        VARCHAR(64) DEFAULT '',
    "expiry_date"     DATE,
    "ext_attributes"  JSONB DEFAULT '{}',
    "remark"          VARCHAR(500) DEFAULT '',
    "create_by"       VARCHAR(64) DEFAULT '',
    "create_time"     TIMESTAMP DEFAULT NOW(),
    "update_by"       VARCHAR(64) DEFAULT '',
    "update_time"     TIMESTAMP DEFAULT NOW()
);
COMMENT ON TABLE "ruoyi"."nautilus_inventory" IS '物资库存（既有实体表，含Agent查询数据）';
CREATE INDEX "idx_nautilus_inventory_item_name" ON "ruoyi"."nautilus_inventory" ("item_name");

-- 演示种子数据（阿莫西林低于警戒水位 10 → 触发采购链路）
INSERT INTO "ruoyi"."nautilus_inventory"
("item_id","item_code","item_name","current_stock","alert_threshold","category_dict","price","batch_no","ext_attributes") VALUES
(1, 'AMX-050', '阿莫西林胶囊',   2, 10, '1', 8.50, 'B20260801', '{"storage":"常温"}'),
(2, 'IBU-030', '布洛芬缓释胶囊', 56, 10, '1', 12.00, 'B20260715', '{"storage":"常温"}');

-- ----------------------------
-- 采购订单表（高风险写操作落库）
-- 下游级幂等：同一 idempotency_key 仅允许一张订单（重复请求返回已有单据）
-- ----------------------------
DROP TABLE IF EXISTS "ruoyi"."nautilus_purchase_order";
CREATE TABLE "ruoyi"."nautilus_purchase_order" (
    "order_id"         BIGSERIAL PRIMARY KEY,
    "order_no"         VARCHAR(64) NOT NULL,
    "supplier"         VARCHAR(128) NOT NULL,
    "items"            JSONB NOT NULL DEFAULT '[]',
    "total_amount"     NUMERIC(14,2) DEFAULT 0,
    "status"           VARCHAR(16) DEFAULT 'CREATED',
    "idempotency_key"  VARCHAR(160),
    "remark"           VARCHAR(500) DEFAULT '',
    "create_by"        VARCHAR(64) DEFAULT 'agent',
    "create_time"      TIMESTAMP DEFAULT NOW()
);
COMMENT ON TABLE "ruoyi"."nautilus_purchase_order" IS '药品采购订单（Agent经BPM审批后创建）';
COMMENT ON COLUMN "ruoyi"."nautilus_purchase_order"."idempotency_key" IS '幂等键：网关透传，重复下单防重';
CREATE UNIQUE INDEX "uk_purchase_order_idem" ON "ruoyi"."nautilus_purchase_order" ("idempotency_key");
CREATE INDEX "idx_purchase_order_no" ON "ruoyi"."nautilus_purchase_order" ("order_no");
