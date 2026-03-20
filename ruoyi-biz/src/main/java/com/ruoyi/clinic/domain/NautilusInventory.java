package com.ruoyi.clinic.domain;

import java.math.BigDecimal;
import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import com.ruoyi.common.core.domain.BaseEntity;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * 物资库存实体对象 nautilus_inventory
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
@TableName(value = "ruoyi.nautilus_inventory", autoResultMap = true)
public class NautilusInventory extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(value = "item_id", type = IdType.ASSIGN_ID)
    @JsonSerialize(using = ToStringSerializer.class)
    private Long itemId;

    /**
     * 物资编码
     */
    @NotBlank(message = "物资编码不能为空")
    private String itemCode;

    /**
     * 物资名称
     */
    @NotBlank(message = "物资名称不能为空")
    private String itemName;

    /**
     * 当前库存
     */
    @NotNull(message = "库存数量不能为空")
    @Min(value = 0, message = "库存数量不能为负数")
    private Integer currentStock;

    /**
     * 警戒库存阈值
     */
    private Integer alertThreshold;

    /**
     * 物资类别字典值
     */
    private String categoryDict = "0";

    /**
     * 药品单价
     */
    private BigDecimal price;

    /**
     * 批次号
     */
    private String batchNo;

    /**
     * 有效期至
     */
    @JsonFormat(pattern = "yyyy-MM-dd", timezone = "GMT+8")
    private Date expiryDate;

    /**
     * 物资扩展属性 (JSONB 映射)
     */
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> extAttributes;
}
