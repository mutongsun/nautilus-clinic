package com.ruoyi.clinic.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ruoyi.common.core.domain.model.LoginUser;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 排队叫号 WebSocket 处理器
 * <p>
 * 广播仅发送叫号动作（患者姓名 + 诊室号），不发送完整病历。
 * 未来可按角色拆分广播粒度（如医生端收到完整信息，候诊屏仅显示序号）。
 * </p>
 */
@Slf4j
@Component
public class QueueWebSocketHandler extends TextWebSocketHandler {

    private final CopyOnWriteArrayList<WebSocketSession> sessions = new CopyOnWriteArrayList<>();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private int maxSessions = 50;

    public void setMaxSessions(int maxSessions) {
        this.maxSessions = maxSessions;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        if (sessions.size() >= maxSessions) {
            log.warn("[WebSocket] 连接数已达上限 {}，拒绝新连接: {}", maxSessions, session.getId());
            session.close(CloseStatus.SERVICE_OVERLOAD);
            return;
        }
        sessions.add(session);
        LoginUser user = (LoginUser) session.getAttributes().get(WebSocketTokenInterceptor.LOGIN_USER_ATTR);
        log.info("[WebSocket] 新连接: {} (用户: {}, 总连接数: {})",
                session.getId(), user != null ? user.getUsername() : "unknown", sessions.size());
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        sessions.remove(session);
        log.info("[WebSocket] 连接关闭: {} (总连接数: {})", session.getId(), sessions.size());
    }

    /**
     * 广播叫号消息 — 仅发送患者姓名与诊室号，不做脱敏（叫号屏需要显示）。
     */
    public void broadcastCall(String patientName, String roomNumber) {
        if (sessions.isEmpty()) {
            log.debug("[WebSocket] 无活跃连接，跳过广播: patient={}", patientName);
            return;
        }

        try {
            Map<String, String> payload = new HashMap<>();
            payload.put("action", "CALL");
            payload.put("patient", patientName);
            payload.put("room", roomNumber);
            String jsonMessage = objectMapper.writeValueAsString(payload);
            TextMessage textMessage = new TextMessage(jsonMessage);

            for (WebSocketSession session : sessions) {
                if (session.isOpen()) {
                    try {
                        session.sendMessage(textMessage);
                    } catch (IOException e) {
                        log.error("[WebSocket] 发送失败: session={}", session.getId(), e);
                    }
                } else {
                    sessions.remove(session);
                }
            }
        } catch (Exception e) {
            log.error("[WebSocket] 广播消息 JSON 序列化失败", e);
        }
    }
}
