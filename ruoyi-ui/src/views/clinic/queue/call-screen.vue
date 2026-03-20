<template>
  <div class="call-screen-container">
    <!-- Header Bar -->
    <div class="cs-header">
      <div class="cs-header-left">
        <i class="el-icon-first-aid-kit"></i>
        <span>Nautilus 社区诊所 · 候诊大屏</span>
      </div>
      <div class="cs-header-right">
        <span class="cs-clock">{{ clock }}</span>
        <span :class="['cs-status', wsConnected ? 'online' : 'offline']">
          {{ wsConnected ? '● 已连接' : '○ 断开' }}
        </span>
      </div>
    </div>

    <!-- Main Display -->
    <div class="cs-main">
      <transition name="cs-fade" mode="out-in">
        <div v-if="currentPatient" key="calling" class="cs-calling">
          <div class="cs-label">请</div>
          <div class="cs-patient-name">{{ currentPatient }}</div>
          <div class="cs-label">到 <span class="cs-room">{{ currentRoom }}</span> 就诊</div>
        </div>
        <div v-else key="waiting" class="cs-waiting">
          <i class="el-icon-time" style="font-size: 80px; opacity: 0.3;"></i>
          <div style="margin-top: 24px; font-size: 2rem; opacity: 0.5;">等待呼叫中…</div>
        </div>
      </transition>
    </div>

    <!-- Recent Calls Bar -->
    <div class="cs-footer" v-if="recentCalls.length > 0">
      <div class="cs-footer-label">最近叫号</div>
      <div class="cs-recent-list">
        <span v-for="(call, idx) in recentCalls" :key="idx" class="cs-recent-item">
          {{ call.patient }} → {{ call.room }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import { getToken } from '@/utils/auth'

export default {
  name: 'CallScreen',
  data() {
    return {
      ws: null,
      wsConnected: false,
      currentPatient: '',
      currentRoom: '',
      recentCalls: [],
      clock: '',
      clockTimer: null
    }
  },
  mounted() {
    this.startClock()
    this.initWebSocket()
  },
  beforeDestroy() {
    if (this.ws) this.ws.close()
    if (this.clockTimer) clearInterval(this.clockTimer)
  },
  methods: {
    startClock() {
      const update = () => {
        const now = new Date()
        this.clock = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      }
      update()
      this.clockTimer = setInterval(update, 1000)
    },

    initWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://'
      const host = window.location.host
      const basePath = (process.env.VUE_APP_BASE_API || '/dev-api').replace(/\/$/, '')
      const token = getToken()
      const wsUrl = `${protocol}${host}${basePath}/ws/queue?token=${token}`

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.wsConnected = true
        console.log('[CallScreen] WebSocket 已连接')
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.action === 'CALL') {
            this.currentPatient = data.patient
            this.currentRoom = data.room
            // 添加到最近列表（最多保留 5 条）
            this.recentCalls.unshift({ patient: data.patient, room: data.room })
            if (this.recentCalls.length > 5) this.recentCalls.pop()
            // TTS
            this.playTTS(data.patient, data.room)
          }
        } catch (e) {
          console.error('[CallScreen] 解析 WebSocket 数据失败:', e)
        }
      }

      this.ws.onerror = () => {
        this.wsConnected = false
      }

      this.ws.onclose = () => {
        this.wsConnected = false
        console.log('[CallScreen] WebSocket 已断开，5秒后重连…')
        setTimeout(() => this.initWebSocket(), 5000)
      }
    },

    playTTS(patientName, roomNumber) {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel()
        const msg = new SpeechSynthesisUtterance(`请 ${patientName} 到 ${roomNumber} 就诊`)
        msg.rate = 0.9
        msg.pitch = 1.0
        msg.volume = 1.0
        window.speechSynthesis.speak(msg)
      }
    }
  }
}
</script>

<style scoped>
.call-screen-container {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 9999;
  background: linear-gradient(135deg, #0c1426 0%, #1a2940 50%, #0c1426 100%);
  color: #ffffff;
  display: flex;
  flex-direction: column;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  overflow: hidden;
}

.cs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  background: rgba(255,255,255,0.05);
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.cs-header-left {
  font-size: 1.2rem;
  font-weight: bold;
  letter-spacing: 2px;
}
.cs-header-left i { margin-right: 10px; color: #4bb884; }
.cs-header-right { display: flex; align-items: center; gap: 20px; }
.cs-clock { font-size: 1.3rem; letter-spacing: 1px; opacity: 0.8; }
.cs-status { font-size: 0.9rem; }
.cs-status.online { color: #67c23a; }
.cs-status.offline { color: #f56c6c; }

.cs-main {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.cs-calling {
  animation: cs-pulse 2s ease-in-out infinite;
}
.cs-label {
  font-size: 2.5rem;
  letter-spacing: 4px;
  opacity: 0.7;
}
.cs-patient-name {
  font-size: 6rem;
  font-weight: bold;
  color: #e6a23c;
  margin: 16px 0;
  text-shadow: 0 0 40px rgba(230,162,60,0.4);
  letter-spacing: 6px;
}
.cs-room {
  color: #4bb884;
  font-weight: bold;
}

.cs-waiting {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: rgba(255,255,255,0.4);
}

.cs-footer {
  display: flex;
  align-items: center;
  padding: 14px 32px;
  background: rgba(255,255,255,0.05);
  border-top: 1px solid rgba(255,255,255,0.1);
  gap: 16px;
}
.cs-footer-label {
  font-size: 0.85rem;
  opacity: 0.5;
  white-space: nowrap;
}
.cs-recent-list {
  display: flex;
  gap: 12px;
  overflow: hidden;
}
.cs-recent-item {
  background: rgba(255,255,255,0.08);
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 0.85rem;
  opacity: 0.6;
  white-space: nowrap;
}

@keyframes cs-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}

.cs-fade-enter-active, .cs-fade-leave-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.cs-fade-enter { opacity: 0; transform: translateY(20px); }
.cs-fade-leave-to { opacity: 0; transform: translateY(-20px); }
</style>
