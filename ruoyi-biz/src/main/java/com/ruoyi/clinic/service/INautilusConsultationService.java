package com.ruoyi.clinic.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.ruoyi.clinic.domain.NautilusConsultation;

/**
 * 就诊处方服务接口
 */
public interface INautilusConsultationService extends IService<NautilusConsultation> {

    /**
     * 执行发药逻辑并扣减对应库存
     * 
     * @param consultationId 就诊单ID
     */
    void dispenseMedication(Long consultationId);

    /**
     * 执行一键快速接诊逻辑（新建/更新患者，开具处方等）
     * 
     * @param dto 快速接诊数据传输对象
     */
    void quickConsultation(com.ruoyi.clinic.domain.dto.QuickConsultationDTO dto);
}
