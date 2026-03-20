package com.ruoyi.clinic.service;

import java.util.List;
import java.util.Map;

/**
 * 诊所结算服务接口
 */
public interface IClinicBillingService {

    /**
     * 列出所有有待缴费处方的患者（返回 patientId + patientName）
     */
    List<Map<String, Object>> listPendingPatients();

    /**
     * 按患者ID查询最新一条待缴费处方明细
     *
     * @param patientId 患者ID
     * @return 处方 payload 列表
     */
    List<Map<String, Object>> queryPrescriptionByPatientId(Long patientId);

    /**
     * 生成账单流水号
     */
    String generateBillNo();

    /**
     * 支付结算
     *
     * @param billNo    账单流水号
     * @param patientId 患者ID
     * @return 是否成功
     */
    boolean processPayment(String billNo, Long patientId);
}
