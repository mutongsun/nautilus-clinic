package com.ruoyi.clinic.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

/**
 * Nautilus Clinic 核心配置类
 * 开启异步任务和定时调度能力
 */
@Configuration
@EnableAsync
@EnableScheduling
public class NautilusConfig {

    /** 通知专用线程池 — 替换默认 SimpleAsyncTaskExecutor，防止线程暴增 */
    @Bean(name = "clinicNotificationExecutor")
    public Executor clinicNotificationExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(5);
        executor.setQueueCapacity(50);
        executor.setThreadNamePrefix("clinic-notify-");
        executor.setRejectedExecutionHandler(
                new java.util.concurrent.ThreadPoolExecutor.CallerRunsPolicy());
        executor.initialize();
        return executor;
    }
}
