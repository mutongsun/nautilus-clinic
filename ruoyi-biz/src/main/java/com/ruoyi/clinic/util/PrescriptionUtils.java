package com.ruoyi.clinic.util;

import java.math.BigDecimal;

/**
 * 处方解析工具类 — 消除重复的 quantity 类型转换逻辑
 */
public final class PrescriptionUtils {

    private PrescriptionUtils() {
    }

    /**
     * 安全解析处方药品数量（兼容 Integer / BigDecimal / String）
     *
     * @param qtyObj 原始数量对象（来自 JSONB Map）
     * @return 解析后的整型数量，null 时返回 0
     */
    public static int parseQuantity(Object qtyObj) {
        if (qtyObj == null) {
            return 0;
        }
        if (qtyObj instanceof Integer) {
            return (Integer) qtyObj;
        }
        if (qtyObj instanceof BigDecimal) {
            return ((BigDecimal) qtyObj).intValue();
        }
        return Integer.parseInt(qtyObj.toString());
    }
}
