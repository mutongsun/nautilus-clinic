package com.ruoyi.clinic.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.ruoyi.clinic.domain.NautilusPatient;
import com.ruoyi.clinic.mapper.NautilusPatientMapper;
import com.ruoyi.clinic.service.INautilusPatientService;
import com.ruoyi.common.utils.StringUtils;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 患者信息服务实现类
 */
@Service
public class NautilusPatientServiceImpl extends ServiceImpl<NautilusPatientMapper, NautilusPatient>
                implements INautilusPatientService {

        @Override
        public List<NautilusPatient> advancedSearch(String tag, String allergy) {
                LambdaQueryWrapper<NautilusPatient> wrapper = new LambdaQueryWrapper<>();

                if (StringUtils.isNotEmpty(tag)) {
                        // 使用 PostgreSQL 原生 jsonb_exists 函数，避免 JDBC 占位符 '?' 冲突
                        wrapper.apply("jsonb_exists(dynamic_profile->'tags', {0})", tag);
                }

                if (StringUtils.isNotEmpty(allergy)) {
                        // 使用 PostgreSQL 原生 jsonb_exists 函数，避免 JDBC 占位符 '?' 冲突
                        wrapper.apply("jsonb_exists(dynamic_profile->'allergies', {0})", allergy);
                }

                return this.list(wrapper);
        }
}
