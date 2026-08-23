package com.ruoyi.biz.domain.dto;

import lombok.Data;

import java.math.BigDecimal;

/**
 * 采购单行项目。
 *
 * @author nautilus-agent
 */
@Data
public class PurchaseOrderItemDTO {

    /** 药品名称 */
    private String medicineName;

    /** 采购数量 */
    private BigDecimal quantity;

    /** 单价 */
    private BigDecimal unitPrice;
}
