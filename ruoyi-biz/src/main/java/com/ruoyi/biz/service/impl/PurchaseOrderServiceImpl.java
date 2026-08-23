package com.ruoyi.biz.service.impl;

import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.ruoyi.biz.domain.PurchaseOrder;
import com.ruoyi.biz.domain.dto.PurchaseOrderItemDTO;
import com.ruoyi.biz.domain.dto.PurchaseOrderRequest;
import com.ruoyi.biz.mapper.PurchaseOrderMapper;
import com.ruoyi.biz.service.IPurchaseOrderService;
import com.ruoyi.common.exception.ServiceException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * 采购订单服务实现：真实落库 + 下游级幂等
 *
 * <p>幂等实现（三层防线）：
 * 1. 先按 idempotency_key 查询，命中直接返回已有订单；
 * 2. 并发穿透时依赖唯一索引 uk_purchase_order_idem 兜底（DuplicateKeyException 重查）；
 * 3. 网关层（Agent 平台）另有审计表幂等缓存，双层防重。</p>
 *
 * @author nautilus-agent
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class PurchaseOrderServiceImpl implements IPurchaseOrderService {

    private static final DateTimeFormatter NO_FMT = DateTimeFormatter.ofPattern("yyyyMMdd");

    private final PurchaseOrderMapper purchaseOrderMapper;

    @Override
    @Transactional
    public Map<String, Object> createOrder(PurchaseOrderRequest request) {
        // ---------- 入参业务校验（业务规则全部下沉业务底座，网关/Agent 不做业务判断） ----------
        if (request.getItems() == null || request.getItems().isEmpty()) {
            throw new ServiceException("采购明细不能为空");
        }
        if (request.getSupplier() == null || request.getSupplier().isBlank()) {
            throw new ServiceException("供应商不能为空");
        }

        // ---------- 幂等第一层：按键预查 ----------
        String idemKey = request.getIdempotencyKey();
        if (idemKey != null && !idemKey.isBlank()) {
            PurchaseOrder existing = selectByIdempotencyKey(idemKey);
            if (existing != null) {
                log.info("[采购下单] 幂等命中，返回已有订单: orderNo={} idemKey={}", existing.getOrderNo(), idemKey);
                return result(existing.getOrderNo(), "DUPLICATE");
            }
        }

        // ---------- 真实落库 ----------
        BigDecimal total = BigDecimal.ZERO;
        for (PurchaseOrderItemDTO item : request.getItems()) {
            if (item.getQuantity() == null || item.getQuantity().compareTo(BigDecimal.ZERO) <= 0) {
                throw new ServiceException("采购数量必须大于0: " + item.getMedicineName());
            }
            BigDecimal price = item.getUnitPrice() == null ? BigDecimal.ZERO : item.getUnitPrice();
            total = total.add(price.multiply(item.getQuantity()));
        }

        PurchaseOrder order = new PurchaseOrder();
        // 预取序列生成真实单号：单段式插入（order_no 非空约束下避免先空后补的两段式）
        Long orderId = purchaseOrderMapper.nextOrderId();
        String orderNo = "PO-" + LocalDateTime.now().format(NO_FMT) + "-" + String.format("%04d", orderId);
        order.setOrderId(orderId);
        order.setOrderNo(orderNo);
        order.setSupplier(request.getSupplier());
        order.setItems(JSONUtil.toJsonStr(request.getItems()));
        order.setTotalAmount(total);
        order.setStatus("CREATED");
        order.setIdempotencyKey(idemKey);
        order.setRemark(request.getRemark() == null ? "" : request.getRemark());
        order.setCreateBy("agent-platform");
        order.setCreateTime(LocalDateTime.now());

        try {
            purchaseOrderMapper.insert(order);
        } catch (DuplicateKeyException e) {
            // ---------- 幂等第二层：并发穿透由唯一索引兜底 ----------
            PurchaseOrder winner = selectByIdempotencyKey(idemKey);
            if (winner != null) {
                log.info("[采购下单] 并发幂等兜底命中: orderNo={} idemKey={}", winner.getOrderNo(), idemKey);
                return result(winner.getOrderNo(), "DUPLICATE");
            }
            throw e;
        }

        log.info("[采购下单] 订单创建成功: orderNo={} supplier={} total={} idemKey={}",
                orderNo, request.getSupplier(), total, idemKey);
        return result(orderNo, "CREATED");
    }

    private PurchaseOrder selectByIdempotencyKey(String idemKey) {
        if (idemKey == null || idemKey.isBlank()) {
            return null;
        }
        return purchaseOrderMapper.selectOne(
                new QueryWrapper<PurchaseOrder>().eq("idempotency_key", idemKey).last("LIMIT 1"));
    }

    private Map<String, Object> result(String orderNo, String status) {
        Map<String, Object> map = new HashMap<>();
        map.put("code", 200);
        map.put("orderId", orderNo);
        map.put("status", status);
        return map;
    }
}
