package com.ruoyi.clinic.aspect;

import com.ruoyi.clinic.domain.NautilusConsultation;
import com.ruoyi.clinic.domain.NautilusPatient;
import com.ruoyi.clinic.domain.dto.PrescriptionItem;
import com.ruoyi.clinic.mapper.NautilusPatientMapper;
import com.ruoyi.common.exception.ServiceException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * 处方过敏拦截切面
 */
@Aspect
@Component
@RequiredArgsConstructor
@Slf4j
public class AllergyCheckAspect {

    private final NautilusPatientMapper patientMapper;

    @Before("@annotation(com.ruoyi.clinic.annotation.CheckAllergy)")
    public void doBefore(JoinPoint joinPoint) {
        log.info("--- 进入处方过敏拦截 AOP (AllergyCheckAspect) ---");
        Object[] args = joinPoint.getArgs();
        for (Object arg : args) {
            if (arg instanceof NautilusConsultation) {
                NautilusConsultation consultation = (NautilusConsultation) arg;
                checkAllergy(consultation);
                return;
            }
        }
    }

    private void checkAllergy(NautilusConsultation consultation) {
        if (consultation == null || consultation.getPatientId() == null) {
            return;
        }

        NautilusPatient patient = patientMapper.selectById(consultation.getPatientId());
        if (patient == null || patient.getDynamicProfile() == null) {
            return;
        }

        Map<String, Object> dynamicProfile = patient.getDynamicProfile();
        Object allergiesObj = dynamicProfile.get("allergies");
        if (allergiesObj == null) {
            log.info("患者未设置过敏史 (allergies 字段不存在)");
            return;
        }

        List<String> allergies = new java.util.ArrayList<>();
        if (allergiesObj instanceof List) {
            for (Object obj : (List<?>) allergiesObj) {
                if (obj != null) {
                    allergies.add(obj.toString());
                }
            }
        } else {
            String allergyStr = allergiesObj.toString().replaceAll("[\"\\[\\]]", "");
            for (String s : allergyStr.split(",")) {
                if (s != null && !s.trim().isEmpty()) {
                    allergies.add(s.trim());
                }
            }
        }

        if (allergies.isEmpty()) {
            return;
        }

        log.info("解析到患者({}): 过敏史 => {}", patient.getPatientId(), allergies);

        List<Map<String, Object>> payload = consultation.getPrescriptionPayload();
        if (payload == null || payload.isEmpty()) {
            return;
        }

        // 使用 PrescriptionItem DTO 进行强类型化遍历
        for (Map<String, Object> rawItem : payload) {
            PrescriptionItem item = PrescriptionItem.fromMap(rawItem);
            if (item == null || item.getItemName() == null) {
                continue;
            }
            String drugName = item.getItemName();
            for (String allergy : allergies) {
                if (allergy == null || allergy.trim().isEmpty()) {
                    continue;
                }
                // 单字过敏原过滤：只有出现在药品名开头才报警（避免"林"误匹配"林可霉素"）
                if (allergy.trim().length() == 1) {
                    if (drugName.startsWith(allergy.trim())) {
                        log.warn("高危拦截（单字匹配）：患者对【{}】过敏，药品名以【{}】开头！",
                                allergy, drugName);
                        throw new ServiceException("高危拦截：患者对【" + allergy + "】过敏，药品【"
                                + drugName + "】可能含有过敏成分，严禁开具！");
                    }
                    continue;
                }
                // 多字过敏原：精确子串匹配（中文药品名中"青霉素"匹配"青霉素V钾片"是合理的）
                if (drugName.contains(allergy)) {
                    log.warn("高危拦截：患者对【{}】过敏，药品【{}】包含过敏原！", allergy, drugName);
                    throw new ServiceException("高危拦截：患者对【" + allergy + "】过敏，严禁开具【"
                            + drugName + "】！");
                }
            }
        }
    }
}
