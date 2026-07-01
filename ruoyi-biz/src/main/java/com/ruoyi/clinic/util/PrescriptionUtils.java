package com.ruoyi.clinic.util;

import com.ruoyi.common.exception.ServiceException;

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
     * @return 解析后的整型数量
     * @throws ServiceException 当数量无法解析为合法整数时
     */
    public static int parseQuantity(Object qtyObj) {
        if (qtyObj == null) {
            throw new ServiceException("处方药品数量不能为空");
        }
        if (qtyObj instanceof Integer) {
            return (Integer) qtyObj;
        }
        if (qtyObj instanceof BigDecimal) {
            return ((BigDecimal) qtyObj).intValue();
        }
        try {
            return Integer.parseInt(qtyObj.toString());
        } catch (NumberFormatException e) {
            throw new ServiceException("处方药品数量格式非法: " + qtyObj);
        }
    }
}
