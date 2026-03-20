package com.ruoyi.clinic.controller;

import com.ruoyi.clinic.domain.NautilusInventory;
import com.ruoyi.clinic.service.INautilusInventoryService;
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

import java.util.List;

/**
 * 物资库存 前端控制器
 */
@Tag(name = "物资库存管理", description = "诊所药品、物资生命周期管理及扩展属性接口")
@RestController
@RequestMapping("/clinic/inventory")
@RequiredArgsConstructor
public class NautilusInventoryController extends BaseController {

    private final INautilusInventoryService inventoryService;

    /**
     * 查询物资列表
     */
    @Operation(summary = "查询物资列表", description = "获取药品/物资列表支持模糊搜索")
    @PreAuthorize("@ss.hasPermi('clinic:inventory:list')")
    @GetMapping("/list")
    public TableDataInfo list(NautilusInventory inventory) {
        startPage();
        List<NautilusInventory> list = inventoryService.lambdaQuery()
                .like(inventory.getItemName() != null && !inventory.getItemName().isEmpty(),
                        NautilusInventory::getItemName, inventory.getItemName())
                .like(inventory.getItemCode() != null && !inventory.getItemCode().isEmpty(),
                        NautilusInventory::getItemCode, inventory.getItemCode())
                .list();
        return getDataTable(list);
    }

    /**
     * 获取物资详细信息
     */
    @Operation(summary = "获取物资详情")
    @PreAuthorize("@ss.hasPermi('clinic:inventory:query')")
    @GetMapping("/{id}")
    public AjaxResult getInfo(@PathVariable("id") Long id) {
        return AjaxResult.success(inventoryService.getById(id));
    }

    /**
     * 新增物资
     */
    @Operation(summary = "新增物资")
    @PreAuthorize("@ss.hasPermi('clinic:inventory:add')")
    @Log(title = "物资库存", businessType = BusinessType.INSERT)
    @PostMapping
    public AjaxResult add(@Validated @RequestBody NautilusInventory nautilusInventory) {
        return toAjax(inventoryService.upsertInventory(nautilusInventory));
    }

    /**
     * 修改物资
     */
    @Operation(summary = "修改物资")
    @PreAuthorize("@ss.hasPermi('clinic:inventory:edit')")
    @Log(title = "物资库存", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult edit(@Validated @RequestBody NautilusInventory inventory) {
        return toAjax(inventoryService.updateById(inventory));
    }

    /**
     * 删除物资
     */
    @Operation(summary = "删除物资")
    @PreAuthorize("@ss.hasPermi('clinic:inventory:remove')")
    @Log(title = "物资库存", businessType = BusinessType.DELETE)
    @DeleteMapping("/{ids}")
    public AjaxResult remove(@PathVariable List<Long> ids) {
        return toAjax(inventoryService.removeByIds(ids));
    }

    @Operation(summary = "库存预警面板", description = "返回低库存和近效期预警药品列表")
    @PreAuthorize("@ss.hasPermi('clinic:inventory:list')")
    @GetMapping("/alerts")
    public AjaxResult alerts() {
        // 低库存：current_stock <= alert_threshold
        List<NautilusInventory> lowStock = inventoryService.lambdaQuery()
                .apply("current_stock <= alert_threshold")
                .list();

        // 近效期/已过期：expiry_date 存在且 <= 当前日期 + 30天
        List<NautilusInventory> expiringSoon = inventoryService.lambdaQuery()
                .isNotNull(NautilusInventory::getExpiryDate)
                .apply("expiry_date <= CURRENT_DATE + INTERVAL '30 days'")
                .list();

        java.util.Map<String, Object> result = new java.util.HashMap<>();
        result.put("lowStock", lowStock);
        result.put("expiringSoon", expiringSoon);
        return AjaxResult.success(result);
    }
}
