<template>
  <div class="app-container">
    <!-- Top Section (Big Screen Display) -->
    <el-card class="box-card big-screen" style="background-color: #2b2b2b; color: #fff;">
      <div slot="header" class="clearfix" style="border-bottom: 1px solid #4bb884; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 1.5rem; font-weight: bold;">实时叫号大屏</span>
        <el-button type="warning" size="small" icon="el-icon-full-screen" @click="openFullScreen">独立全屏大屏</el-button>
      </div>
      <div class="display-content" style="display: flex; justify-content: center; align-items: center; min-height: 250px;">
        <h1 v-if="currentPatient && currentRoom" class="call-text" style="font-size: 3rem; letter-spacing: 2px;">
          请 <span style="color: #e6a23c; padding: 0 10px;">{{ currentPatient }}</span> 到 <span style="color: #e6a23c; padding: 0 10px;">{{ currentRoom }}</span> 就诊
        </h1>
        <h1 v-else class="empty-text" style="font-size: 2.5rem; color: #888;">
          暂无呼叫
        </h1>
      </div>
    </el-card>

    <!-- Bottom Section (Control Panel) -->
    <el-card class="box-card control-panel" style="margin-top: 20px;">
      <div slot="header" class="clearfix">
        <span style="font-weight: bold;">控制面板</span>
      </div>
      
      <el-row :gutter="20">
        <!-- Enqueue Section -->
        <el-col :span="12">
          <div style="padding: 20px; background-color: #f8f9fa; border-radius: 4px; border: 1px solid #e2e2e2; height: 100%;">
            <h3 style="margin-top: 0;">排队叫号机</h3>
            <div style="display: flex; align-items: center; margin-top: 15px;">
              <el-input 
                v-model="enqueueForm.patientName" 
                placeholder="请输入患者姓名 (如：Elma)" 
                style="width: 250px; margin-right: 15px;"
                @keyup.enter.native="handleEnqueue"
              ></el-input>
              <el-button type="primary" icon="el-icon-plus" @click="handleEnqueue">模拟挂号入队</el-button>
            </div>
          </div>
        </el-col>
        
        <!-- Call Section -->
        <el-col :span="12">
          <div style="padding: 20px; background-color: #f8f9fa; border-radius: 4px; border: 1px solid #e2e2e2; height: 100%;">
            <h3 style="margin-top: 0;">医生工作台呼叫端</h3>
            <div style="display: flex; align-items: center; margin-top: 15px;">
              <el-input 
                v-model="callForm.roomNumber" 
                placeholder="请输入诊室号 (如：诊室1)" 
                style="width: 250px; margin-right: 15px;"
                @keyup.enter.native="handleCallNext"
              ></el-input>
              <el-button type="success" icon="el-icon-bell" @click="handleCallNext">呼叫下一位</el-button>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script>
import request from '@/utils/request'

export default {
  name: "ClinicQueue",
  data() {
    return {
      ws: null,
      currentPatient: '',
      currentRoom: '',
      enqueueForm: {
        patientName: ''
      },
      callForm: {
        roomNumber: '诊室1'
      }
    };
  },
  mounted() {
    this.initWebSocket();
  },
  beforeDestroy() {
    if (this.ws) {
      this.ws.close();
    }
  },
  methods: {
    initWebSocket() {
      // 动态获取 websocket 代理地址
      const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
      const host = window.location.host;
      const basePath = process.env.VUE_APP_BASE_API || '/dev-api';
      const cleanBasePath = basePath.endsWith('/') ? basePath.slice(0, -1) : basePath;
      const wsUrl = `${protocol}${host}${cleanBasePath}/ws/queue`;
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log("WebSocket 大屏连接已建立。");
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.action === "CALL") {
            this.currentPatient = data.patient;
            this.currentRoom = data.room;
            this.playTTS(this.currentPatient, this.currentRoom);
          }
        } catch (e) {
          console.error("解析 WebSocket 推送数据失败:", e);
        }
      };
      
      this.ws.onerror = (error) => {
        console.error("WebSocket 发生错误:", error);
      };
      
      this.ws.onclose = () => {
        console.log("WebSocket 大屏连接已关闭。");
      };
    },

    openFullScreen() {
      window.open('/call-screen', '_blank');
    },
    
    playTTS(patientName, roomNumber) {
      // 使用 HTML5 Web Speech API
      if ('speechSynthesis' in window) {
        // 取消前一个正在播放的语音（如果频繁叫号重叠）
        window.speechSynthesis.cancel();
        
        const text = "请 " + patientName + " 到 " + roomNumber + " 就诊";
        const msg = new SpeechSynthesisUtterance(text);
        
        msg.rate = 1.0;
        msg.pitch = 1.0;
        msg.volume = 1.0;
        // 若需指定特定的中文语音可以在这里设置，一般默认系统语言
        // msg.lang = 'zh-CN'; 
        
        window.speechSynthesis.speak(msg);
      } else {
        console.warn("当前浏览器不支持 HTML5 文字转语音播报!");
        this.$message.warning("您的浏览器不支持语音播报(Web Speech API)");
      }
    },
    
    handleEnqueue() {
      if (!this.enqueueForm.patientName) {
        this.$message.warning("请输入患者姓名");
        return;
      }
      
      // 调用加入队列 API
      request({
        url: '/clinic/queue/enqueue',
        method: 'post',
        params: {
          patientName: this.enqueueForm.patientName
        }
      }).then(response => {
        // 后端可能返回 200 或 AjaxResult
        this.$message.success(`患者 ${this.enqueueForm.patientName} 已加入排队系统`);
        this.enqueueForm.patientName = '';
      }).catch(error => {
        console.error("挂号入队调用失败:", error);
      });
    },
    
    handleCallNext() {
      if (!this.callForm.roomNumber) {
        this.$message.warning("请输入诊室号");
        return;
      }
      
      // 调用呼叫 API
      request({
        url: '/clinic/queue/call',
        method: 'post',
        params: {
          roomNumber: this.callForm.roomNumber
        }
      }).then(response => {
        if (response.msg && response.msg.includes("Queue is empty")) {
            this.$message.info("当前等待队列为空，暂无患者可呼叫。");
        } else {
            this.$message.success(`呼叫指令已成功发送至大屏`);
        }
      }).catch(error => {
        console.error("呼叫患者调用失败:", error);
      });
    }
  }
};
</script>
