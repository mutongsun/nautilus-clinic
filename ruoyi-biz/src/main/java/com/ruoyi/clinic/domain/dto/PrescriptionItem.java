package com.ruoyi.clinic.domain.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * 处方药品条目 DTO — 强类型化替代 Map&lt;String, Object&gt;
 * <p>
 * 用于处方 Payload 的解析和展示，消除运行时 ClassCastException 风险。
 * </p>
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PrescriptionItem implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 药品编码 */
    private String itemCode;

    /** 药品名称 */
    private String itemName;

    /** 数量 */
    private Integer quantity;

    /** 用法嘱咐 */
    private String dosage;

    /** 附加说明 */
    private String instructions;

    /**
     * 从 Map 安全转换为 PrescriptionItem
     */
    public static PrescriptionItem fromMap(java.util.Map<String, Object> map) {
        if (map == null)
            return null;
        PrescriptionItem item = new PrescriptionItem();
        item.setItemCode(getStr(map, "itemCode"));
        item.setItemName(getStr(map, "itemName"));
        item.setDosage(getStr(map, "dosage"));
        item.setInstructions(getStr(map, "instructions"));

        Object qtyObj = map.get("quantity");
        if (qtyObj instanceof Number) {
            item.setQuantity(((Number) qtyObj).intValue());
        } else if (qtyObj != null) {
            try {
                item.setQuantity(Integer.parseInt(qtyObj.toString()));
            } catch (NumberFormatException e) {
                item.setQuantity(0);
            }
        }
        return item;
    }

    private static String getStr(java.util.Map<String, Object> map, String key) {
        Object val = map.get(key);
        return val != null ? val.toString() : null;
    }
}
