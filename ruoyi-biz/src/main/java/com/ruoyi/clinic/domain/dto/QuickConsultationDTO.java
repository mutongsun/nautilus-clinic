package com.ruoyi.clinic.domain.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/**
 * 快速接诊(医生工作站)数据传输对象
 */
@Data
public class QuickConsultationDTO {

    // 1. 患者信息部分
    // 如果 patientId 不为空，则为复诊老患者；否则为新患者
    private Long patientId;

    @NotBlank(message = "患者姓名不能为空")
    private String patientName;

    private String gender;
    private Integer age;
    private LocalDate birthDate;
    private String phoneNumber;
    private String department;

    // 过敏史和血型等可存放在患者的 dynamicProfile JSONB 中
    private String allergyHistory;
    private String bloodType;

    // 患者联系地址
    private List<String> region;
    private String address;

    // 2. 就诊/处方部分
    // 临床诊断
    private String diagnosis;
    // 主诉 (可选)
    private String chiefComplaint;

    // 3. 处方明细表 (JSONB 映射)
    private List<Map<String, Object>> prescriptionItems;
}
