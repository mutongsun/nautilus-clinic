package com.ruoyi.clinic.service.impl;

import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.ruoyi.clinic.domain.NautilusConsultation;
import com.ruoyi.clinic.domain.NautilusInventory;
import com.ruoyi.clinic.mapper.NautilusConsultationMapper;
import com.ruoyi.clinic.mapper.NautilusInventoryMapper;
import com.ruoyi.clinic.service.INautilusConsultationService;
import com.ruoyi.clinic.service.NautilusNotificationService;
import com.ruoyi.clinic.util.PrescriptionUtils;
import com.ruoyi.common.exception.ServiceException;
import lombok.RequiredArgsConstructor;
import com.ruoyi.clinic.service.INautilusPatientService;
import com.ruoyi.clinic.domain.dto.QuickConsultationDTO;
import com.ruoyi.clinic.domain.NautilusPatient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

/**
 * 就诊处方服务实现类
 */
@Service
@RequiredArgsConstructor
public class NautilusConsultationServiceImpl extends ServiceImpl<NautilusConsultationMapper, NautilusConsultation>
                implements INautilusConsultationService {

        private final NautilusInventoryMapper inventoryMapper;
        private final NautilusNotificationService notificationService;
        private final INautilusPatientService patientService;

        @Override
        @Transactional(rollbackFor = Exception.class)
        public void dispenseMedication(Long consultationId) {
                NautilusConsultation consultation = this.getById(consultationId);
                if (consultation == null) {
                        throw new ServiceException("就诊单不存在");
                }

                if (!"1".equals(consultation.getStatus())) {
                        throw new ServiceException("处方状态不合法，必须为已开具(1)状态才能发药");
                }

                List<Map<String, Object>> payload = consultation.getPrescriptionPayload();
                if (payload == null || payload.isEmpty()) {
                        throw new ServiceException("处方内未包含任何药品信息");
                }

                for (Map<String, Object> item : payload) {
                        String itemCode = (String) item.get("itemCode");
                        Object qtyObj = item.get("quantity");
                        if (itemCode == null || qtyObj == null) {
                                continue;
                        }

                        int quantity = PrescriptionUtils.parseQuantity(qtyObj);
                        // quantity is int primitive, safe from SQL injection
                        // If this ever accepts external string input, switch to apply("{0}", value)
                        LambdaUpdateWrapper<NautilusInventory> updateWrapper = new LambdaUpdateWrapper<>();
                        updateWrapper.eq(NautilusInventory::getItemCode, itemCode)
                                        .ge(NautilusInventory::getCurrentStock, quantity)
                                        .setSql("current_stock = current_stock - " + quantity);

                        int rows = inventoryMapper.update(null, updateWrapper);
                        if (rows == 0) {
                                throw new ServiceException("库存不足或物资不存在，发药失败：[" + itemCode + "]");
                        }

                        // 发出异步通知
                        String itemName = (String) item.get("itemName");
                        if (itemName == null)
                                itemName = itemCode;
                        notificationService.sendDispenseSms(consultation.getPatientId(), itemName);
                }

                // 扭转状态机
                consultation.setStatus("2");
                this.updateById(consultation);
        }

        @Override
        @Transactional(rollbackFor = Exception.class)
        public void quickConsultation(QuickConsultationDTO dto) {
                Long patientId = dto.getPatientId();
                NautilusPatient patient;

                if (patientId == null) {
                        // 新增患者
                        patient = new NautilusPatient();
                        patient.setPatientName(dto.getPatientName());
                        patient.setGender(dto.getGender());
                        patient.setAge(dto.getAge());
                        patient.setBirthDate(dto.getBirthDate());
                        patient.setPhoneNumber(dto.getPhoneNumber());
                        patient.setDepartment(dto.getDepartment());

                        Map<String, Object> profile = new java.util.HashMap<>();
                        if (com.ruoyi.common.utils.StringUtils.isNotEmpty(dto.getAllergyHistory())) {
                                profile.put("allergies", dto.getAllergyHistory());
                        }
                        if (com.ruoyi.common.utils.StringUtils.isNotEmpty(dto.getBloodType())) {
                                profile.put("bloodType", dto.getBloodType());
                        }
                        if (com.ruoyi.common.utils.StringUtils.isNotEmpty(dto.getAddress())) {
                                profile.put("address", dto.getAddress());
                        }
                        if (dto.getRegion() != null && !dto.getRegion().isEmpty()) {
                                profile.put("region", dto.getRegion());
                        }
                        patient.setDynamicProfile(profile);

                        patientService.save(patient);
                        patientId = patient.getPatientId();
                } else {
                        // 更新已存在的患者部分信息
                        patient = patientService.getById(patientId);
                        if (patient != null) {
                                boolean needsUpdate = false;
                                if (dto.getAge() != null && !dto.getAge().equals(patient.getAge())) {
                                        patient.setAge(dto.getAge());
                                        needsUpdate = true;
                                }
                                if (com.ruoyi.common.utils.StringUtils.isNotEmpty(dto.getPhoneNumber())
                                                && !dto.getPhoneNumber().equals(patient.getPhoneNumber())) {
                                        patient.setPhoneNumber(dto.getPhoneNumber());
                                        needsUpdate = true;
                                }

                                Map<String, Object> profile = patient.getDynamicProfile();
                                if (profile == null) {
                                        profile = new java.util.HashMap<>();
                                        patient.setDynamicProfile(profile);
                                }

                                if (com.ruoyi.common.utils.StringUtils.isNotEmpty(dto.getAllergyHistory())) {
                                        profile.put("allergies", dto.getAllergyHistory());
                                        needsUpdate = true;
                                }
                                if (com.ruoyi.common.utils.StringUtils.isNotEmpty(dto.getBloodType())) {
                                        profile.put("bloodType", dto.getBloodType());
                                        needsUpdate = true;
                                }
                                if (com.ruoyi.common.utils.StringUtils.isNotEmpty(dto.getAddress())) {
                                        profile.put("address", dto.getAddress());
                                        needsUpdate = true;
                                }
                                if (dto.getRegion() != null && !dto.getRegion().isEmpty()) {
                                        profile.put("region", dto.getRegion());
                                        needsUpdate = true;
                                }

                                if (needsUpdate) {
                                        patientService.updateById(patient);
                                }
                        } else {
                                throw new ServiceException("指定的患者不存在");
                        }
                }

                // 创建就诊记录
                NautilusConsultation consultation = new NautilusConsultation();
                consultation.setPatientId(patientId);
                consultation.setDiagnosis(dto.getDiagnosis());
                consultation.setChiefComplaint(dto.getChiefComplaint());
                consultation.setPrescriptionPayload(dto.getPrescriptionItems());
                consultation.setStatus("1"); // 默认状态为已开具(待发药)

                this.save(consultation);
        }
}
