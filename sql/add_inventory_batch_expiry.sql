-- 药品有效期 & 批次管理：为 nautilus_inventory 表添加 batch_no 和 expiry_date 列
ALTER TABLE ruoyi.nautilus_inventory ADD COLUMN IF NOT EXISTS batch_no VARCHAR(64) DEFAULT NULL;
ALTER TABLE ruoyi.nautilus_inventory ADD COLUMN IF NOT EXISTS expiry_date DATE DEFAULT NULL;

COMMENT ON COLUMN ruoyi.nautilus_inventory.batch_no IS '生产批次号';
COMMENT ON COLUMN ruoyi.nautilus_inventory.expiry_date IS '有效期至';
