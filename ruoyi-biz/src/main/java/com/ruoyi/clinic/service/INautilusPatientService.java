package com.ruoyi.clinic.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.ruoyi.clinic.domain.NautilusPatient;

import java.util.List;

/**
 * 患者信息服务接口
 */
public interface INautilusPatientService extends IService<NautilusPatient> {

    /**
     * 根据 JSONB 特性进行高级动态域查询
     * 
     * @param tag     患者标签
     * @param allergy 过敏源
     * @return 患者列表
     */
    List<NautilusPatient> advancedSearch(String tag, String allergy);
}
