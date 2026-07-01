package com.ruoyi.clinic.config;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * WebSocket 配置 — 排队叫号推送
 * <p>
 * 安全约束：仅允许配置的域名连接（默认内网地址），拒绝通配符 *。
 * 生产部署时通过 ${clinic.ws.allowed-origins} 指定白名单。
 * </p>
 */
@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketConfigurer {

    private final QueueWebSocketHandler queueWebSocketHandler;
    private final WebSocketTokenInterceptor webSocketTokenInterceptor;

    @Value("${clinic.ws.allowed-origins:http://localhost:5173,http://127.0.0.1:5173}")
    private String allowedOrigins;

    /** 最大连接数，防止连接耗尽 */
    @Value("${clinic.ws.max-sessions:50}")
    private int maxSessions;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        // 限制最大连接数
        queueWebSocketHandler.setMaxSessions(maxSessions);
        registry.addHandler(queueWebSocketHandler, "/ws/queue")
                .setAllowedOriginPatterns(allowedOrigins.split(","))
                .addInterceptors(webSocketTokenInterceptor);
    }
}
