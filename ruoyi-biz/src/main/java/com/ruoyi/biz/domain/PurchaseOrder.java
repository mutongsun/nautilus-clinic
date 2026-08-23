package com.ruoyi.biz.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 药品采购订单对象 nautilus_purchase_order
 *
 * <p>高风险写操作：仅允许 Agent 平台经 MCP 网关 + BPM 审批通过后创建。</p>
 *
 * @author nautilus-agent
 */
@Data
@TableName("ruoyi.nautilus_purchase_order")
public class PurchaseOrder {

    /** 订单主键 */
    @TableId(value = "order_id", type = IdType.AUTO)
    private Long orderId;

    /** 订单号（业务单据号，落库后回填） */
    @TableField("order_no")
    private String orderNo;

    /** 供应商 */
    @TableField("supplier")
    private String supplier;

    /** 采购明细（JSONB 数组字符串：[{medicineName,quantity,unitPrice}...]） */
    @TableField("items")
    private String items;

    /** 订单总额 */
    @TableField("total_amount")
    private BigDecimal totalAmount;

    /** 状态：CREATED */
    @TableField("status")
    private String status;

    /** 幂等键（网关透传，唯一索引防重复下单） */
    @TableField("idempotency_key")
    private String idempotencyKey;

    /** 备注（默认承载用户原始指令摘要） */
    @TableField("remark")
    private String remark;

    /** 创建者 */
    @TableField("create_by")
    private String createBy;

    /** 创建时间 */
    @TableField("create_time")
    private LocalDateTime createTime;
}
