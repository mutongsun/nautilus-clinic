package com.ruoyi.clinic.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.ruoyi.clinic.domain.NautilusInventory;

/**
 * 物资库存 Service 接口
 */
public interface INautilusInventoryService extends IService<NautilusInventory> {

    /**
     * 🛡️ 桥接方法：新增物资库存（与基架代码生成契约兼容）
     *
     * @param nautilusInventory 物资库存
     * @return 结果
     */
    int insertNautilusInventory(NautilusInventory nautilusInventory);

    /**
     * 🚀 核心逻辑：容错进货引擎 (Upsert)
     *
     * @param entity 物资实体
     * @return 结果
     */
    boolean upsertInventory(NautilusInventory entity);

    /**
     * 💊 结算联动：扣减库存
     *
     * @param itemCode 药品编码 (e.g., "YORU-001")
     * @param quantity 扣减数量
     * @return true 扣减成功；false 库存不足或记录不存在
     */
    boolean decreaseStock(String itemCode, int quantity);

}