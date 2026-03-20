package com.ruoyi.clinic.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.ruoyi.clinic.domain.NautilusConsultation;
import com.ruoyi.clinic.domain.NautilusPatient;
import com.ruoyi.clinic.mapper.NautilusConsultationMapper;
import com.ruoyi.clinic.mapper.NautilusPatientMapper;
import com.ruoyi.clinic.service.IClinicBillingService;
import com.ruoyi.clinic.service.INautilusInventoryService;
import com.ruoyi.clinic.util.PrescriptionUtils;
import com.ruoyi.common.exception.ServiceException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * 💰 分布式账单与结算中心核心引擎 (v3 — 安全锁 + patientId 驱动)
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ClinicBillingServiceImpl implements IClinicBillingService {

    private final StringRedisTemplate redisTemplate;
    private final INautilusInventoryService inventoryService;
    private final NautilusPatientMapper patientMapper;
    private final NautilusConsultationMapper consultationMapper;

    /**
     * Lua 脚本：安全释放分布式锁（仅当 value 匹配 owner 时才删除）
     */
    private static final DefaultRedisScript<Long> UNLOCK_SCRIPT = new DefaultRedisScript<>(
            "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
            Long.class);

    // =========================================================
    // 🔍 查询层
    // =========================================================

    /**
     * 列出所有有待缴费处方（status=1）的患者 ID 和姓名
     */
    @Override
    public List<Map<String, Object>> listPendingPatients() {
        // 取所有 status=1 的就诊单
        List<NautilusConsultation> pending = consultationMapper.selectList(
                new LambdaQueryWrapper<NautilusConsultation>()
                        .eq(NautilusConsultation::getStatus, "1"));
        // 批量取 patientId -> patientName
        List<Long> patientIds = pending.stream()
                .map(NautilusConsultation::getPatientId)
                .distinct().collect(Collectors.toList());
        if (patientIds.isEmpty())
            return List.of();

        List<NautilusPatient> patients = patientMapper.selectList(
                new LambdaQueryWrapper<NautilusPatient>()
                        .in(NautilusPatient::getPatientId, patientIds));

        return patients.stream().map(p -> {
            Map<String, Object> map = new HashMap<>();
            map.put("patientId", p.getPatientId().toString());
            map.put("patientName", p.getPatientName());
            return map;
        }).collect(Collectors.toList());
    }

    /**
     * 按患者ID查询该患者最新一条 status=1 的处方 Payload
     */
    @Override
    public List<Map<String, Object>> queryPrescriptionByPatientId(Long patientId) {
        NautilusConsultation consultation = consultationMapper.selectOne(
                new LambdaQueryWrapper<NautilusConsultation>()
                        .eq(NautilusConsultation::getPatientId, patientId)
                        .eq(NautilusConsultation::getStatus, "1")
                        .orderByDesc(NautilusConsultation::getCreateTime)
                        .last("LIMIT 1"));
        if (consultation == null || consultation.getPrescriptionPayload() == null) {
            throw new ServiceException("该患者暂无待缴费处方");
        }
        return consultation.getPrescriptionPayload();
    }

    // =========================================================
    // 🚀 金融级流水发号器
    // =========================================================
    @Override
    public String generateBillNo() {
        String dateStr = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        String redisKey = "nautilus:seq:bill:" + dateStr;
        Long sequence = redisTemplate.opsForValue().increment(redisKey);
        if (sequence != null && sequence == 1L) {
            redisTemplate.expire(redisKey, 24, TimeUnit.HOURS);
        }
        return String.format("BILL-%s-%06d", dateStr, sequence);
    }

    // =========================================================
    // 🛡️ 支付结算网关 (安全分布式锁 + @Transactional)
    // =========================================================
    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean processPayment(String billNo, Long patientId) {
        // 1. 分布式锁防重放（带 owner 标识）
        String lockKey = "nautilus:lock:pay:" + billNo;
        String owner = UUID.randomUUID().toString();
        Boolean acquired = redisTemplate.opsForValue().setIfAbsent(lockKey, owner, 30, TimeUnit.SECONDS);
        if (Boolean.FALSE.equals(acquired)) {
            log.warn("🚨 防重放拦截：账单 [{}] 正在处理中！", billNo);
            throw new ServiceException("支付正在处理中，请勿频繁点击！");
        }

        try {
            log.info(">>> 🔒 获取支付锁，开始处理账单: {}", billNo);

            // 2. 从 DB 查询该患者最新待付款处方
            List<Map<String, Object>> payload = queryPrescriptionByPatientId(patientId);
            log.info(">>> 📋 共读取到 {} 条处方药品，准备扣减库存...", payload.size());

            // 3. 动态扣减真实处方库存
            for (Map<String, Object> item : payload) {
                String itemCode = (String) item.get("itemCode");
                String itemName = (String) item.get("itemName");
                Object qtyObj = item.get("quantity");
                if (itemCode == null || qtyObj == null)
                    continue;

                int quantity = PrescriptionUtils.parseQuantity(qtyObj);

                log.info(">>> 💊 扣减药品: [{}] {} x{}", itemCode, itemName, quantity);
                boolean ok = inventoryService.decreaseStock(itemCode, quantity);
                if (!ok) {
                    throw new ServiceException("库存联动失败：未找到商品或库存不足 [" + itemCode + "]");
                }
            }

            // 4. 将该就诊单状态扭转为 2 (已缴费/已发药)
            NautilusConsultation toUpdate = consultationMapper.selectOne(
                    new LambdaQueryWrapper<NautilusConsultation>()
                            .eq(NautilusConsultation::getPatientId, patientId)
                            .eq(NautilusConsultation::getStatus, "1")
                            .orderByDesc(NautilusConsultation::getCreateTime)
                            .last("LIMIT 1"));
            if (toUpdate != null) {
                toUpdate.setStatus("2");
                consultationMapper.updateById(toUpdate);
                log.info(">>> 📌 就诊单 [{}] 状态已更新为 2（已缴费）", toUpdate.getConsultationId());
            }

            log.info(">>> 🎉 患者 [{}] 账单 [{}] 结算完毕！", patientId, billNo);
            return true;

        } finally {
            // 安全释放：Lua 脚本保证只释放自己持有的锁
            Long result = redisTemplate.execute(UNLOCK_SCRIPT, List.of(lockKey), owner);
            log.info(">>> 🔓 支付锁释放: {} (result={})", lockKey, result);
        }
    }
}