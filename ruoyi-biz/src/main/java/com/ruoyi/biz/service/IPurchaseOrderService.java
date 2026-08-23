package com.ruoyi.biz.service;

import com.ruoyi.biz.domain.dto.PurchaseOrderRequest;

import java.util.Map;

/**
 * 采购订单服务接口（Agent 平台专用）
 *
 * @author nautilus-agent
 */
public interface IPurchaseOrderService {

    /**
     * 创建采购订单（下游级幂等）
     *
     * <p>同一 idempotency_key 重复请求不再生成新订单，直接返回已有单据（status=DUPLICATE），
     * 与 Agent 平台网关层幂等形成端到端双层防重。</p>
     *
     * @param request 下单请求（供应商/明细/幂等键/备注）
     * @return {orderId: 订单号, status: CREATED | DUPLICATE}
     */
    Map<String, Object> createOrder(PurchaseOrderRequest request);
}
