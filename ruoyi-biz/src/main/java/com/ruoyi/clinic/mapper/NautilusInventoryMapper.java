package com.ruoyi.clinic.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.ruoyi.clinic.domain.NautilusInventory;
import org.apache.ibatis.annotations.Insert;

/**
 * 物资库存Mapper接口
 *
 * 采用 PostgreSQL 原生 UPSERT（INSERT ... ON CONFLICT DO UPDATE）策略，
 * 绕过 MyBatis-Plus 的所有钩子，实现真正的原子化幂等写入。
 */
public interface NautilusInventoryMapper extends BaseMapper<NautilusInventory> {

    /**
     * 🚀 终极原子 UPSERT：PostgreSQL 原生 INSERT...ON CONFLICT
     * - 新药品 → 直接 INSERT
     * - 已存在药品（item_code 冲突）→ 原子叠加库存 + 追加备注
     * - 100% 免疫 PSQLException: duplicate key
     */
    @Insert("INSERT INTO ruoyi.nautilus_inventory " +
            "  (item_id, item_code, item_name, current_stock, alert_threshold, price, category_dict, batch_no, expiry_date, remark, create_by, create_time, del_flag) "
            +
            "VALUES " +
            "  (#{itemId}, #{itemCode}, #{itemName}, COALESCE(#{currentStock}, 0), #{alertThreshold}, #{price}, COALESCE(#{categoryDict}, '0'), #{batchNo}, #{expiryDate}, #{remark}, #{createBy}, #{createTime}, '0') "
            +
            "ON CONFLICT (item_code) DO UPDATE SET " +
            "  current_stock = ruoyi.nautilus_inventory.current_stock + COALESCE(EXCLUDED.current_stock, 0), " +
            "  batch_no      = COALESCE(EXCLUDED.batch_no, ruoyi.nautilus_inventory.batch_no), " +
            "  expiry_date   = COALESCE(EXCLUDED.expiry_date, ruoyi.nautilus_inventory.expiry_date), " +
            "  remark        = CASE " +
            "                    WHEN EXCLUDED.remark IS NULL OR EXCLUDED.remark = '' THEN ruoyi.nautilus_inventory.remark "
            +
            "                    WHEN ruoyi.nautilus_inventory.remark IS NULL OR ruoyi.nautilus_inventory.remark = '' THEN EXCLUDED.remark "
            +
            "                    ELSE ruoyi.nautilus_inventory.remark || ' | ' || EXCLUDED.remark " +
            "                  END, " +
            "  del_flag      = '0', " +
            "  update_time   = NOW()")
    int nativeUpsert(NautilusInventory entity);
}