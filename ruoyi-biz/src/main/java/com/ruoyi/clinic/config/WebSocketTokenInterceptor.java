package com.ruoyi.clinic.config;

import com.ruoyi.framework.web.service.TokenService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

import java.util.Map;

/**
 * WebSocket 握手 Token 校验拦截器
 * <p>
 * 由于浏览器 WebSocket API 无法设置自定义 HTTP Header，
 * 客户端需通过 URL query 参数传递 Token：ws://host/ws/queue?token=xxx
 * </p>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class WebSocketTokenInterceptor implements HandshakeInterceptor {

    private final TokenService tokenService;

    @Override
    public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response,
            WebSocketHandler wsHandler, Map<String, Object> attributes) {
        if (request instanceof ServletServerHttpRequest servletRequest) {
            HttpServletRequest httpRequest = servletRequest.getServletRequest();

            // 优先从 query 参数获取 token
            String token = httpRequest.getParameter("token");
            if (token != null && !token.isEmpty()) {
                try {
                    var loginUser = tokenService.getLoginUser("Bearer " + token);
                    if (loginUser != null) {
                        log.info("[WebSocket] Token 验证通过，用户: {}", loginUser.getUsername());
                        return true;
                    }
                } catch (Exception e) {
                    log.warn("[WebSocket] Token 验证失败: {}", e.getMessage());
                }
            }

            // 兜底：从 Authorization Header 获取（非浏览器客户端可能使用）
            var loginUser = tokenService.getLoginUser(httpRequest);
            if (loginUser != null) {
                log.info("[WebSocket] Header 验证通过，用户: {}", loginUser.getUsername());
                return true;
            }
        }
        log.warn("[WebSocket] 握手被拒绝：无有效 Token");
        return false;
    }

    @Override
    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
            WebSocketHandler wsHandler, Exception exception) {
        // No-op
    }
}
