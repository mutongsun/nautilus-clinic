package com.ruoyi.clinic.controller;

import com.ruoyi.clinic.service.ClinicQueueService;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.enums.BusinessType;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 叫号排队 前端控制器
 */
@Tag(name = "叫号排队管理", description = "诊所排队叫号接口")
@RestController
@RequestMapping("/clinic/queue")
@RequiredArgsConstructor
public class ClinicQueueController {

    private final ClinicQueueService clinicQueueService;

    /**
     * Add a patient to the waiting queue
     *
     * @param patientName The name of the patient (e.g., 'Elma' or 'Amy')
     * @return Success result
     */
    @Operation(summary = "患者入队")
    @PreAuthorize("@ss.hasPermi('clinic:queue:enqueue')")
    @Log(title = "叫号排队", businessType = BusinessType.INSERT)
    @PostMapping("/enqueue")
    public AjaxResult enqueue(@RequestParam String patientName) {
        clinicQueueService.enqueue(patientName);
        return AjaxResult.success("Patient " + patientName + " added to queue.");
    }

    /**
     * Call the next patient in the queue
     *
     * @param roomNumber The room number (e.g., '诊室1')
     * @return Success result with the called patient name, or a message if empty
     */
    @Operation(summary = "呼叫下一位患者")
    @PreAuthorize("@ss.hasPermi('clinic:queue:call')")
    @Log(title = "叫号排队", businessType = BusinessType.UPDATE)
    @PostMapping("/call")
    public AjaxResult callNext(@RequestParam String roomNumber) {
        String patientName = clinicQueueService.callNext(roomNumber);
        if (patientName != null) {
            return AjaxResult.success("Called patient " + patientName + " to room " + roomNumber);
        } else {
            return AjaxResult.success("Queue is empty. No patient to call.");
        }
    }
}
