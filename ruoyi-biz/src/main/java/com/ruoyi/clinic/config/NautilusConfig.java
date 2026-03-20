package com.ruoyi.clinic.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Nautilus Clinic 核心配置类
 * 开启异步任务和定时调度能力
 */
@Configuration
@EnableAsync
@EnableScheduling
public class NautilusConfig {
}
