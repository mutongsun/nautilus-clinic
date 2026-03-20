<template>
  <div class="app-container">
    <el-row :gutter="24">

      <!-- 左栏：处方明细 (60%) -->
      <el-col :span="14">
        <el-card shadow="hover">
          <div slot="header" style="font-weight: bold; font-size: 16px;">
            <i class="el-icon-s-order" style="margin-right: 6px;"></i>处方明细
            <span v-if="selectedPatientName" style="font-size: 13px; color: #909399; margin-left: 10px;">
              — {{ selectedPatientName }}
            </span>
          </div>

          <div v-if="!prescriptionItems.length" style="text-align:center; color:#c0c4cc; padding: 40px 0;">
            <i class="el-icon-document" style="font-size: 40px;"></i>
            <p>请先在右侧选择患者</p>
          </div>

          <el-table v-else :data="prescriptionItems" border stripe>
            <el-table-column label="药品编码" prop="itemCode" width="200" />
            <el-table-column label="药品名称" prop="itemName" />
            <el-table-column label="数量" prop="quantity" width="80" align="center" />
          </el-table>

          <div v-if="prescriptionItems.length" style="margin-top: 24px; text-align: right; padding-right: 8px;">
            <span style="font-size: 14px; color: #909399;">共 {{ prescriptionItems.length }} 种药品</span>
          </div>
        </el-card>
      </el-col>

      <!-- 右栏：结算控制台 (40%) -->
      <el-col :span="10">
        <el-card shadow="hover">
          <div slot="header" style="font-weight: bold; font-size: 16px;">
            <i class="el-icon-bank-card" style="margin-right: 6px;"></i>医保结算控制台
          </div>

          <el-form :model="form" label-width="100px" style="margin-top: 10px;">
            <el-form-item label="选择患者">
              <el-select
                v-model="form.patientId"
                placeholder="请选择待缴费患者"
                style="width: 100%;"
                :loading="loadingPatients"
                @change="handlePatientChange"
              >
                <el-option
                  v-for="p in pendingPatients"
                  :key="p.patientId"
                  :label="p.patientName"
                  :value="p.patientId"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="账单流水号">
              <el-input
                v-model="form.billNo"
                readonly
                placeholder="点击下方按钮生成"
              />
            </el-form-item>
          </el-form>

          <div style="display: flex; flex-direction: column; gap: 12px; padding: 0 20px 10px;">
            <el-button
              type="primary"
              icon="el-icon-refresh"
              style="width: 100%;"
              :disabled="!form.patientId"
              @click="handleGenerateBill"
            >
              1. 获取账单流水号
            </el-button>

            <el-button
              type="success"
              icon="el-icon-check"
              style="width: 100%;"
              :loading="paying"
              :disabled="!form.billNo"
              @click="handlePay"
            >
              2. 确认医保支付
            </el-button>
          </div>

          <el-alert
            v-if="payResult"
            :title="payResult.message"
            :type="payResult.type"
            show-icon
            style="margin: 12px 20px 0;"
          />
        </el-card>
      </el-col>

    </el-row>
  </div>
</template>

<script>
import { getPendingPatients, getPrescription, generateBill, payBill } from '@/api/clinic/billing'

export default {
  name: 'ClinicBilling',
  data() {
    return {
      loadingPatients: false,
      paying: false,
      payResult: null,
      pendingPatients: [],      // [{patientId, patientName}, ...]
      prescriptionItems: [],
      selectedPatientName: '',
      form: {
        patientId: '',
        billNo: ''
      }
    }
  },
  created() {
    this.loadPendingPatients()
  },
  activated() {
    // 从其他页面切回时自动刷新待缴费列表
    this.loadPendingPatients()
    this.prescriptionItems = []
    this.selectedPatientName = ''
    this.form.patientId = ''
    this.form.billNo = ''
    this.payResult = null
  },
  methods: {
    loadPendingPatients() {
      this.loadingPatients = true
      getPendingPatients().then(res => {
        this.pendingPatients = res.data || []
      }).catch(err => {
        this.$modal.msgError(err.msg || '获取患者列表失败')
      }).finally(() => {
        this.loadingPatients = false
      })
    },

    handlePatientChange(patientId) {
      this.prescriptionItems = []
      this.form.billNo = ''
      this.payResult = null
      // 找到选中患者的姓名用于显示
      const found = this.pendingPatients.find(p => p.patientId === patientId)
      this.selectedPatientName = found ? found.patientName : ''
      if (!patientId) return
      getPrescription(patientId).then(res => {
        this.prescriptionItems = res.data || []
      }).catch(err => {
        this.$modal.msgError(err.msg || '加载处方失败')
      })
    },

    handleGenerateBill() {
      this.payResult = null
      this.form.billNo = ''
      generateBill().then(res => {
        this.form.billNo = res.data
        this.$modal.msgSuccess('账单流水号已生成：' + res.data)
      }).catch(err => {
        this.$modal.msgError(err.msg || '流水号生成失败')
      })
    },

    handlePay() {
      if (!this.form.billNo) {
        this.$modal.msgWarning('请先获取账单流水号')
        return
      }
      this.paying = true
      this.payResult = null
      payBill(this.form.billNo, this.form.patientId).then(() => {
        this.payResult = { type: 'success', message: `✅ 患者 ${this.selectedPatientName} 结算成功，库存已同步扣减！` }
        this.$modal.msgSuccess('支付成功！')
        // 结算成功：重置页面，刷新待缴费患者列表
        this.form.billNo = ''
        this.form.patientId = ''
        this.selectedPatientName = ''
        this.prescriptionItems = []
        this.loadPendingPatients()
      }).catch(err => {
        const msg = err.msg || err.message || '支付失败'
        this.payResult = { type: 'error', message: `❌ ${msg}` }
        this.$modal.msgError(msg)
      }).finally(() => {
        this.paying = false
      })
    }
  }
}
</script>
