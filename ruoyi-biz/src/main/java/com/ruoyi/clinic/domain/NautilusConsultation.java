package com.ruoyi.clinic.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import com.ruoyi.common.core.domain.BaseEntity;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * 就诊处方实体对象 nautilus_consultation
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(callSuper = true)
@TableName(value = "ruoyi.nautilus_consultation", autoResultMap = true)
public class NautilusConsultation extends BaseEntity {

    private static final long serialVersionUID = 1L;

    /**
     * 就诊记录ID
     */
    @TableId(value = "consultation_id", type = IdType.ASSIGN_ID)
    @JsonSerialize(using = ToStringSerializer.class)
    private Long consultationId;

    /**
     * 关联的患者ID
     */
    @NotNull(message = "患者ID不能为空")
    @JsonSerialize(using = ToStringSerializer.class)
    private Long patientId;

    /**
     * 主诉
     */
    private String chiefComplaint;

    /**
     * 诊断结果
     */
    private String diagnosis;

    /**
     * 就诊单状态 (1=已开具, 2=已发药)
     */
    private String status;

    /**
     * 处方详情 (JSONB 映射)
     */
    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<Map<String, Object>> prescriptionPayload;
}
