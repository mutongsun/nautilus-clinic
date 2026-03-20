package com.ruoyi.clinic.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import com.ruoyi.common.core.domain.BaseEntity;
import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * 患者实体对象 nautilus_patient
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
@TableName(value = "ruoyi.nautilus_patient", autoResultMap = true)
public class NautilusPatient extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(value = "patient_id", type = IdType.ASSIGN_ID)
    @JsonSerialize(using = ToStringSerializer.class)
    private Long patientId;

    /**
     * 患者姓名
     */
    @NotBlank(message = "患者姓名不能为空")
    private String patientName;

    /**
     * 性别
     */
    private String gender;

    /**
     * 出生日期
     */
    private java.time.LocalDate birthDate;

    /**
     * 电话号码
     */
    private String phoneNumber;

    /**
     * 年龄
     */
    private Integer age;

    /**
     * 科别
     */
    private String department;

    /**
     * 患者动态随访/体征数据 (JSONB 映射)
     */
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> dynamicProfile;
}
