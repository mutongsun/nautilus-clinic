package com.ruoyi.clinic.controller;

import com.ruoyi.clinic.service.IClinicBillingService;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.enums.BusinessType;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

/**
 * 诊所结算 前端控制器
 */
@Tag(name = "诊所结算管理", description = "门诊结算与医保支付接口")
@RestController
@RequestMapping("/clinic/billing")
@RequiredArgsConstructor
public class ClinicBillingController {

    private final IClinicBillingService clinicBillingService;

    /** 获取所有有待付款处方的患者列表 */
    @Operation(summary = "查询待缴费患者列表")
    @PreAuthorize("@ss.hasPermi('clinic:billing:list')")
    @GetMapping("/pending-patients")
    public AjaxResult pendingPatients() {
        return AjaxResult.success(clinicBillingService.listPendingPatients());
    }

    /** 按患者ID查询最新一条状态=1的处方明细 */
    @Operation(summary = "查询待缴费处方明细")
    @PreAuthorize("@ss.hasPermi('clinic:billing:list')")
    @GetMapping("/prescription")
    public AjaxResult getPrescription(@RequestParam Long patientId) {
        return AjaxResult.success(clinicBillingService.queryPrescriptionByPatientId(patientId));
    }

    /** 生成账单流水号 */
    @Operation(summary = "生成账单流水号")
    @PreAuthorize("@ss.hasPermi('clinic:billing:pay')")
    @GetMapping("/generate")
    public AjaxResult generateBill() {
        return AjaxResult.success("Success", clinicBillingService.generateBillNo());
    }

    /** 确认支付并动态扣减库存 */
    @Operation(summary = "确认医保支付")
    @PreAuthorize("@ss.hasPermi('clinic:billing:pay')")
    @Log(title = "诊所结算", businessType = BusinessType.UPDATE)
    @PostMapping("/pay")
    public AjaxResult payBill(@RequestParam String billNo, @RequestParam Long patientId) {
        clinicBillingService.processPayment(billNo, patientId);
        return AjaxResult.success("结算成功");
    }
}
