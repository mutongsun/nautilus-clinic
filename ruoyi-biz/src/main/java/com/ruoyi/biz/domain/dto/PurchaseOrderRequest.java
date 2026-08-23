package com.ruoyi.biz.domain.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

/**
 * Agent 平台采购下单入参（与 MCP 网关 ClinicClient 契约一致）。
 *
 * @author nautilus-agent
 */
@Data
public class PurchaseOrderRequest {

    /** 供应商 */
    private String supplier;

    /** 采购明细 */
    private List<PurchaseOrderItemDTO> items;

    /** 幂等键：同一键重复下单返回已有订单（下游级幂等兜底） */
    private String idempotencyKey;

    /** 备注 */
    private String remark;
}
