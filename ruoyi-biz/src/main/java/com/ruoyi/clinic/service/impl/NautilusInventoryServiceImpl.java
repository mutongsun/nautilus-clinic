package com.ruoyi.clinic.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.baomidou.mybatisplus.core.toolkit.IdWorker;
import com.ruoyi.common.exception.ServiceException;
import com.ruoyi.common.utils.DateUtils;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.clinic.domain.NautilusInventory;
import com.ruoyi.clinic.mapper.NautilusInventoryMapper;
import com.ruoyi.clinic.service.INautilusInventoryService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * 物资库存 Service 业务层处理
 */
@Service
public class NautilusInventoryServiceImpl extends ServiceImpl<NautilusInventoryMapper, NautilusInventory>
                implements INautilusInventoryService {

        private static final Logger log = LoggerFactory.getLogger(NautilusInventoryServiceImpl.class);

        // =======================================================
        // 🛡️ 架构师的绝对封锁线：拦截所有"偷渡"请求！
        // =======================================================

        /**
         * 拦截 1: 封杀 MyBatis-Plus 原生 Controller 的偷渡调用
         */
        @Override
        public boolean save(NautilusInventory entity) {
                log.warn("⚠️ [INTERCEPT-1] save() was called directly! itemCode=[{}] — routing to upsertInventory.",
                                entity == null ? "NULL_ENTITY" : entity.getItemCode());
                return this.upsertInventory(entity);
        }

        /**
         * 拦截 2: 封杀框架默认风格 Controller 的偷渡调用
         */
        @Override
        public int insertNautilusInventory(NautilusInventory nautilusInventory) {
                log.warn("⚠️ [INTERCEPT-2] insertNautilusInventory() was called! itemCode=[{}] — routing to upsertInventory.",
                                nautilusInventory == null ? "NULL_ENTITY" : nautilusInventory.getItemCode());
                return this.upsertInventory(nautilusInventory) ? 1 : 0;
        }

        // =======================================================
        // 🚀 核心容错进货引擎 (Upsert Engine) - PostgreSQL 原生 UPSERT 版
        // =======================================================
        @Override
        public boolean upsertInventory(NautilusInventory entity) {
                log.info("🔍 [UPSERT-ENGINE] Received entity. Raw itemCode=[{}], itemName=[{}], currentStock=[{}]",
                                entity == null ? "NULL_ENTITY" : entity.getItemCode(),
                                entity == null ? "NULL_ENTITY" : entity.getItemName(),
                                entity == null ? "NULL_ENTITY" : entity.getCurrentStock());

                if (entity == null) {
                        log.error("❌ [UPSERT-ENGINE] Entity is NULL! Aborting.");
                        return false;
                }

                if (entity.getItemCode() == null || entity.getItemCode().trim().isEmpty()) {
                        log.error("❌ [UPSERT-ENGINE] itemCode is null or blank! Raw value=[{}]. Aborting.",
                                        entity.getItemCode());
                        return false;
                }

                // ---- 激进清洗 ----
                String sanitizedCode = entity.getItemCode().trim();
                entity.setItemCode(sanitizedCode);
                log.info("🧹 [UPSERT-ENGINE] Sanitized itemCode=[{}] (length={})", sanitizedCode,
                                sanitizedCode.length());

                // 若无主键则由 Snowflake 分配（INSERT ... ON CONFLICT 需要 item_id）
                if (entity.getItemId() == null) {
                        entity.setItemId(IdWorker.getId());
                }

                // 设置审计字段
                if (entity.getCreateTime() == null) {
                        entity.setCreateTime(DateUtils.getNowDate());
                }
                try {
                        if (entity.getCreateBy() == null) {
                                entity.setCreateBy(SecurityUtils.getUsername());
                        }
                } catch (Exception e) {
                        log.warn("⚠️ [UPSERT-ENGINE] Could not get current username: {}", e.getMessage());
                }

                // 🚀 发射：单条 PostgreSQL 原生 INSERT ... ON CONFLICT DO UPDATE
                int result = this.baseMapper.nativeUpsert(entity);
                log.info("📊 [UPSERT-ENGINE] nativeUpsert result={} for itemCode=[{}]", result, sanitizedCode);
                return result > 0;
        }

        // =======================================================
        // 💊 结算联动：扣减库存 (Stock Deduction Engine)
        // 修复 TOCTOU：直接原子 UPDATE，不再先 SELECT 后 UPDATE
        // =======================================================
        @Override
        public boolean decreaseStock(String itemCode, int quantity) {
                log.info("💊 [DEDUCTION] Attempting to deduct {} unit(s) of itemCode=[{}]", quantity, itemCode);

                // 原子扣减：UPDATE ... SET current_stock = current_stock - quantity
                // WHERE item_code = ? AND current_stock >= quantity
                // quantity is int primitive, safe from SQL injection
                // If this ever accepts external string input, switch to apply("{0}", value)
                boolean success = this.lambdaUpdate()
                                .eq(NautilusInventory::getItemCode, itemCode)
                                .ge(NautilusInventory::getCurrentStock, quantity)
                                .setSql("current_stock = current_stock - " + quantity)
                                .update();

                if (success) {
                        log.info("✅ [DEDUCTION] Successfully deducted {} unit(s) of itemCode=[{}]",
                                        quantity, itemCode);
                } else {
                        log.error("❌ [DEDUCTION] Atomic deduction failed for itemCode=[{}] — stock insufficient or item not found",
                                        itemCode);
                        throw new ServiceException("库存不足或物资不存在: " + itemCode);
                }
                return true;
        }
}
