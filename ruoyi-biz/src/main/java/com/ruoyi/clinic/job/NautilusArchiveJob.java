package com.ruoyi.clinic.job;

import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.ruoyi.clinic.domain.NautilusConsultation;
import com.ruoyi.clinic.service.INautilusConsultationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * 定时归档器
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class NautilusArchiveJob {

    private final INautilusConsultationService consultationService;

    /**
     * 自动归档就诊单
     * 每天凌晨2点执行。
     * 将状态为 '2' 且更新时间在指定时间晚于7天的单据状态更新为 '3'。
     */
    @Scheduled(cron = "0 0 2 * * ?")
    // @Scheduled(fixedRate = 60000) // 生产环境注释掉测试用的触发器
    public void autoArchiveConsultations() {
        log.info("--- 开始执行就诊单自动归档任务 ---");

        // 生产环境：归档 7 天之前更新的已发药单据
        LocalDateTime thresholdTime = LocalDateTime.now().minusDays(7);

        LambdaUpdateWrapper<NautilusConsultation> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(NautilusConsultation::getStatus, "2")
                .lt(NautilusConsultation::getUpdateTime, thresholdTime)
                .set(NautilusConsultation::getStatus, "3");

        boolean success = consultationService.update(updateWrapper);
        if (success) {
            long count = consultationService.lambdaQuery()
                    .eq(NautilusConsultation::getStatus, "3")
                    .ge(NautilusConsultation::getUpdateTime, thresholdTime) // 粗略统计本次修改（或者利用更精确的方法）
                    .count();
            // 上面的 count 只是给个大致反馈，更严谨的话需要先 select 查出 ID，再 update，然后拿到精准的 count
            log.info("就诊单归档任务执行完毕，共影响了 {} 条单据。", count);
        } else {
            log.info("就诊单归档任务执行完毕，没有符合归档条件的单据。");
        }
    }
}
