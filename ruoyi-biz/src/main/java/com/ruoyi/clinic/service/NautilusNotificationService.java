package com.ruoyi.clinic.service;

import com.ruoyi.clinic.domain.NautilusPatient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

/**
 * 异步通知服务 — 使用专用线程池 clinicNotificationExecutor
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class NautilusNotificationService {

    private final INautilusPatientService patientService;

    /**
     * 异步发送发药短信通知（使用专用线程池，防止线程耗尽）
     *
     * @param patientId 患者ID
     * @param itemName  药品名称
     */
    @Async("clinicNotificationExecutor")
    public void sendDispenseSms(Long patientId, String itemName) {
        try {
            NautilusPatient patient = patientService.getById(patientId);
            String patientName = (patient != null && patient.getPatientName() != null)
                    ? patient.getPatientName()
                    : "未知患者";

            if (patient == null) {
                log.warn("[SMS] 患者不存在，跳过短信: patientId={}", patientId);
                return;
            }

            // 模拟调用第三方短信网关
            log.info("[SMS Gateway] 异步短信发送成功 -> {}, 您的【{}】已发放。", patientName, itemName);
        } catch (Exception e) {
            log.error("[SMS] 发送失败: patientId={}, itemName={}", patientId, itemName, e);
            // 不向外抛出，避免影响主流程
        }
    }
}
