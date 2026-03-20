package com.ruoyi.clinic.controller;

import com.ruoyi.clinic.domain.NautilusPatient;
import com.ruoyi.clinic.service.INautilusPatientService;
import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.page.TableDataInfo;
import com.ruoyi.common.enums.BusinessType;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.List;

/**
 * 患者信息 前端控制器
 */
@Tag(name = "患者信息管理", description = "诊所患者档案及动态随访管理接口")
@RestController
@RequestMapping("/clinic/patient")
@RequiredArgsConstructor
public class NautilusPatientController extends BaseController {

    private final INautilusPatientService patientService;

    /**
     * 查询患者列表
     */
    @Operation(summary = "查询患者列表", description = "根据条件查询患者，例如名称检索 Amy")
    @PreAuthorize("@ss.hasPermi('clinic:patient:list')")
    @GetMapping("/list")
    public TableDataInfo list(NautilusPatient patient) {
        startPage();
        List<NautilusPatient> list = patientService.lambdaQuery()
                .like(patient.getPatientName() != null, NautilusPatient::getPatientName, patient.getPatientName())
                .list();
        return getDataTable(list);
    }

    /**
     * 获取患者详细信息
     */
    @Operation(summary = "获取患者详情", description = "获取单个患者详情，返回体中包含 JSONB 的 dynamicProfile 属性")
    @PreAuthorize("@ss.hasPermi('clinic:patient:query')")
    @GetMapping("/{id}")
    public AjaxResult getInfo(@PathVariable("id") Long id) {
        return AjaxResult.success(patientService.getById(id));
    }

    /**
     * 新增患者
     */
    @Operation(summary = "新增患者")
    @PreAuthorize("@ss.hasPermi('clinic:patient:add')")
    @Log(title = "患者信息", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@Validated @RequestBody NautilusPatient patient) {
        return toAjax(patientService.save(patient));
    }

    /**
     * 修改患者
     */
    @Operation(summary = "修改患者")
    @PreAuthorize("@ss.hasPermi('clinic:patient:edit')")
    @Log(title = "患者信息", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@Validated @RequestBody NautilusPatient patient) {
        return toAjax(patientService.updateById(patient));
    }

    /**
     * 删除患者
     */
    @Operation(summary = "删除患者信息")
    @PreAuthorize("@ss.hasPermi('clinic:patient:remove')")
    @Log(title = "患者信息", businessType = BusinessType.DELETE)
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable Long[] ids) {
        return toAjax(patientService.removeByIds(Arrays.asList(ids)));
    }

    @Operation(summary = "基于 JSONB 的高阶域查询")
    @PreAuthorize("@ss.hasPermi('clinic:patient:list')")
    @GetMapping("/advanced-search")
    public TableDataInfo advancedSearch(
            @Parameter(description = "患者自定义标签", example = "Yorushika铁粉") @RequestParam(required = false) String tag,
            @Parameter(description = "过敏源记录", example = "春泥") @RequestParam(required = false) String allergy) {
        startPage();
        List<NautilusPatient> list = patientService.advancedSearch(tag, allergy);
        return getDataTable(list);
    }
}
