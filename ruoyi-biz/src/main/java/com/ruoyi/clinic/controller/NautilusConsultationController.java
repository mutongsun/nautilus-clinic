package com.ruoyi.clinic.controller;

import com.ruoyi.clinic.annotation.CheckAllergy;
import com.ruoyi.clinic.domain.NautilusConsultation;
import com.ruoyi.clinic.domain.dto.QuickConsultationDTO;
import com.ruoyi.clinic.service.INautilusConsultationService;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 就诊处方Controller
 */
@Tag(name = "就诊处方管理", description = "门诊就诊及处方流转单记录")
@RestController
@RequestMapping("/clinic/consultation")
@RequiredArgsConstructor
public class NautilusConsultationController extends BaseController {

    private final INautilusConsultationService consultationService;

    @Operation(summary = "查询就诊处方列表")
    @PreAuthorize("@ss.hasPermi('clinic:consultation:list')")
    @GetMapping("/list")
    public TableDataInfo list(NautilusConsultation consultation) {
        startPage();
        List<NautilusConsultation> list = consultationService.lambdaQuery()
                .eq(consultation.getPatientId() != null, NautilusConsultation::getPatientId,
                        consultation.getPatientId())
                .like(consultation.getChiefComplaint() != null, NautilusConsultation::getChiefComplaint,
                        consultation.getChiefComplaint())
                .list();
        return getDataTable(list);
    }

    @Operation(summary = "获取就诊处方详细信息")
    @PreAuthorize("@ss.hasPermi('clinic:consultation:query')")
    @GetMapping("/{consultationId}")
    public AjaxResult getInfo(@PathVariable("consultationId") Long consultationId) {
        return AjaxResult.success(consultationService.getById(consultationId));
    }

    @Operation(summary = "新增就诊处方")
    @PreAuthorize("@ss.hasPermi('clinic:consultation:add')")
    @Log(title = "就诊处方", businessType = BusinessType.INSERT)
    @CheckAllergy
    @PostMapping
    public AjaxResult add(@Validated @RequestBody NautilusConsultation consultation) {
        if (consultation.getStatus() == null) {
            consultation.setStatus("1"); // 默认状态为已开具(待发药)
        }
        return toAjax(consultationService.save(consultation));
    }

    @Operation(summary = "修改就诊处方")
    @PreAuthorize("@ss.hasPermi('clinic:consultation:edit')")
    @Log(title = "就诊处方", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@Validated @RequestBody NautilusConsultation consultation) {
        return toAjax(consultationService.updateById(consultation));
    }

    @Operation(summary = "删除就诊处方")
    @PreAuthorize("@ss.hasPermi('clinic:consultation:remove')")
    @Log(title = "就诊处方", businessType = BusinessType.DELETE)
    @DeleteMapping("/{consultationIds}")
    public AjaxResult remove(@PathVariable Long[] consultationIds) {
        return toAjax(consultationService.removeByIds(Arrays.asList(consultationIds)));
    }

    @Operation(summary = "Mock获取Yorushika风格处方")
    @PreAuthorize("@ss.hasPermi('clinic:consultation:query')")
    @GetMapping("/mock-example")
    public AjaxResult getMockExample() {
        NautilusConsultation mockData = new NautilusConsultation();
        mockData.setPatientId(1010101010L);
        mockData.setChiefComplaint("写不出歌词综合征");

        List<Map<String, Object>> payload = new ArrayList<>();
        Map<String, Object> prescription = new HashMap<>();
        prescription.put("itemCode", "THOUGHT_CRIMINAL_01");
        prescription.put("itemName", "思想犯药剂");
        prescription.put("quantity", 2);
        prescription.put("instructions", "睡前一滴");
        payload.add(prescription);

        mockData.setPrescriptionPayload(payload);
        return AjaxResult.success(mockData);
    }

    @Operation(summary = "患者就诊历史时间线", description = "按创建时间倒序返回指定患者的全部就诊记录")
    @PreAuthorize("@ss.hasPermi('clinic:consultation:list')")
    @GetMapping("/timeline/{patientId}")
    public AjaxResult timeline(@PathVariable("patientId") Long patientId) {
        List<NautilusConsultation> list = consultationService.lambdaQuery()
                .eq(NautilusConsultation::getPatientId, patientId)
                .orderByDesc(NautilusConsultation::getCreateTime)
                .list();
        return AjaxResult.success(list);
    }

    @Operation(summary = "一键快速接诊 (医生工作站接口)", description = "同一接口支持老患者或新入库患者，并开具处方")
    @PreAuthorize("@ss.hasPermi('clinic:consultation:add')")
    @Log(title = "医生接诊工作站", businessType = BusinessType.INSERT)
    @CheckAllergy
    @PostMapping("/workstation/quick-consultation")
    public AjaxResult quickConsultation(@Validated @RequestBody QuickConsultationDTO dto) {
        consultationService.quickConsultation(dto);
        return AjaxResult.success("接诊成功！开方数据已保存！");
    }

    @PreAuthorize("@ss.hasPermi('clinic:consultation:dispense')")
    @Log(title = "就诊处方", businessType = BusinessType.UPDATE)
    @PostMapping("/{consultationId}/dispense")
    public AjaxResult dispense(@PathVariable("consultationId") Long consultationId) {
        consultationService.dispenseMedication(consultationId);
        return AjaxResult.success("发药成功");
    }
}
