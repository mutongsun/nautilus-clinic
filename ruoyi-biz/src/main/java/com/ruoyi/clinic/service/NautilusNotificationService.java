package com.ruoyi.clinic.service;

import com.ruoyi.clinic.domain.NautilusPatient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

/**
 * 异步通知服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class NautilusNotificationService {

    private final INautilusPatientService patientService;

    /**
     * 异步发送发药短信通知
     *
     * @param patientId 患者ID
     * @param itemName  药品名称
     */
    @Async
    public void sendDispenseSms(Long patientId, String itemName) {
        NautilusPatient patient = patientService.getById(patientId);
        String patientName = (patient != null && patient.getPatientName() != null) ? patient.getPatientName() : "未知患者";

        // 模拟调用第三方短信网关，打印带有 Yorushika 元素的日志
        log.info("[SMS Gateway] 异步短信发送成功 -> {}, 您的【{}】已发放。祝您早日摆脱写不出歌词综合征，夜行性万岁！", patientName, itemName);
    }
}
