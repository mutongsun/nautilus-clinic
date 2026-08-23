package com.ruoyi.biz.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.ruoyi.biz.domain.dto.PurchaseOrderRequest;
import com.ruoyi.biz.service.IPurchaseOrderService;
import com.ruoyi.clinic.domain.NautilusInventory;
import com.ruoyi.clinic.service.INautilusInventoryService;
import com.ruoyi.common.annotation.Anonymous;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.utils.StringUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Agent 平台对接 Controller（内网服务间调用）
 *
 * <p>与既有 NautilusInventoryController 的关系：复用同一 Service 与库存表，
 * 但提供面向 Agent 平台的匿名只读视图（字段契约对齐 src/services/clinic_client.py），
 * 避免与需登录鉴权的管理端接口耦合。</p>
 *
 * <p>安全说明：@Anonymous 放行仅面向 Docker 内网（nautilus-net）的 MCP 网关调用，
 * 生产环境应替换为服务账号鉴权（API Key / mTLS）并收敛网络访问控制。</p>
 *
 * @author nautilus-agent
 */
@Slf4j
@RestController
@RequestMapping("/clinic/agent")
@RequiredArgsConstructor
public class ClinicAgentController extends BaseController {

    private final INautilusInventoryService inventoryService;
    private final IPurchaseOrderService purchaseOrderService;

    /**
     * 药品库存查询（只读，供 Agent 查询/下单前自查；平台契约视图）
     *
     * <p>字段映射：itemName→medicineName、currentStock→quantity、price→salePrice。</p>
     *
     * @param medicineName 药品名称（模糊匹配，为空查全部）
     */
    @Anonymous
    @GetMapping("/inventory")
    public Map<String, Object> inventoryList(@RequestParam(value = "medicineName", required = false) String medicineName) {
        QueryWrapper<NautilusInventory> wrapper = new QueryWrapper<>();
        if (StringUtils.isNotEmpty(medicineName)) {
            wrapper.like("item_name", medicineName);
        }
        wrapper.orderByAsc("item_name");
        List<NautilusInventory> items = inventoryService.list(wrapper);

        List<Map<String, Object>> rows = new ArrayList<>();
        for (NautilusInventory item : items) {
            Map<String, Object> row = new HashMap<>();
            row.put("medicineName", item.getItemName());
            row.put("spec", item.getBatchNo());
            row.put("unit", "盒");
            row.put("quantity", item.getCurrentStock());
            row.put("salePrice", item.getPrice());
            rows.add(row);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("code", 200);
        result.put("rows", rows);
        result.put("total", rows.size());
        return result;
    }

    /**
     * 创建采购订单（高风险写操作）
     *
     * <p>前置约束（由 Agent 平台 MCP 网关保证）：BPM 审批通过 + 网关级幂等；
     * 本接口再做业务校验与下游级幂等（唯一索引），三层防线。</p>
     */
    @Anonymous
    @PostMapping("/purchase/order")
    public Map<String, Object> createPurchaseOrder(@RequestBody PurchaseOrderRequest request) {
        log.info("[Agent下单] supplier={} items={} idemKey={}",
                request.getSupplier(),
                request.getItems() == null ? 0 : request.getItems().size(),
                request.getIdempotencyKey());
        return purchaseOrderService.createOrder(request);
    }
}
