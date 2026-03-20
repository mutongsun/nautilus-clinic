<template>
  <div class="app-container">
    <el-card shadow="never" style="margin-bottom: 20px;">
      <el-form :model="queryParams" ref="queryForm" size="small" :inline="true" v-show="showSearch" label-width="80px">
        <el-form-item label="主诉" prop="chiefComplaint">
          <el-input
            v-model="queryParams.chiefComplaint"
            placeholder="请输入主诉"
            clearable
            @keyup.enter.native="handleQuery"
          />
        </el-form-item>
        <el-form-item label="单据状态" prop="status">
          <el-select v-model="queryParams.status" placeholder="请选择状态" clearable>
            <el-option label="待发药" value="1" />
            <el-option label="已发药" value="2" />
            <el-option label="已归档" value="3" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="el-icon-search" size="mini" @click="handleQuery">搜索</el-button>
          <el-button icon="el-icon-refresh" size="mini" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button
          type="primary"
          plain
          icon="el-icon-plus"
          size="mini"
          @click="handleAdd"
        >新增就诊单</el-button>
      </el-col>
      <right-toolbar :showSearch.sync="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <!-- 列表数据 -->
    <el-table v-loading="loading" :data="consultationList">
      <el-table-column label="序号" type="index" width="80" align="center" />
      <el-table-column label="就诊编号" align="center" prop="consultationId" width="80" v-if="false" />
      <el-table-column label="患者ID" align="center" prop="patientId" width="80" v-if="false" />
      <el-table-column label="患者姓名" align="center" width="120">
        <template slot-scope="scope">
          <span style="font-weight: bold">{{ getPatientName(scope.row.patientId) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="主诉症状" align="left" prop="chiefComplaint" min-width="150" show-overflow-tooltip />
      <el-table-column label="诊断结果" align="left" prop="diagnosis" min-width="150" show-overflow-tooltip />
      
      <!-- 状态机渲染 -->
      <el-table-column label="状态" align="center" prop="status" width="100">
        <template slot-scope="scope">
          <el-tag v-if="scope.row.status === '1'" type="warning">待发药</el-tag>
          <el-tag v-else-if="scope.row.status === '2'" type="success">已发药</el-tag>
          <el-tag v-else-if="scope.row.status === '3'" type="info">已归档</el-tag>
          <el-tag v-else type="danger">异常</el-tag>
        </template>
      </el-table-column>

      <!-- 优雅渲染 JSONB 处方数组 -->
      <el-table-column label="处方明细 (Payload)" align="left" min-width="250">
        <template slot-scope="scope">
          <div v-if="scope.row.prescriptionPayload && scope.row.prescriptionPayload.length > 0">
            <div v-for="(item, index) in scope.row.prescriptionPayload" :key="index" style="margin-bottom: 3px;">
              <el-tag size="mini" effect="plain" style="margin-right: 5px;">
                💊 {{ item.itemName || item.itemCode }} x {{ item.quantity }}
              </el-tag>
              <span v-if="item.dosage" style="font-size: 12px; color: #666;">({{ item.dosage }})</span>
            </div>
          </div>
          <span v-else style="color: #999;">暂无处方</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="200">
        <template slot-scope="scope">
          <!-- 一键发药 (仅在状态为待发药 1 时展示) -->
          <el-button
            v-if="scope.row.status === '1'"
            size="mini"
            type="success"
            round
            icon="el-icon-lightning"
            style="font-weight: bold; margin-right: 5px;"
            @click="handleDispense(scope.row, scope.$index)"
          >一键发药</el-button>
          
          <el-button
            size="mini"
            type="text"
            icon="el-icon-printer"
            @click="handlePrint(scope.row)"
          >打印</el-button>
          <el-button
            size="mini"
            type="text"
            icon="el-icon-edit"
            @click="handleUpdate(scope.row)"
          >修改</el-button>
          <el-button
            size="mini"
            type="text"
            icon="el-icon-delete"
            @click="handleDelete(scope.row, scope.$index)"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <pagination
      v-show="total>0"
      :total="total"
      :page.sync="queryParams.pageNum"
      :limit.sync="queryParams.pageSize"
      @pagination="getList"
    />
    </el-card>

    <!-- 添加或修改就诊单对话框 -->
    <el-dialog :title="title" :visible.sync="open" width="1050px" append-to-body :close-on-click-modal="false">
      <el-row :gutter="20">
        <!-- 左侧处方开单区 -->
        <el-col :span="16" style="border-right: 1px solid #EBEEF5;">
          <el-form ref="form" :model="form" :rules="rules" label-width="80px">
            <el-form-item label="患者ID" prop="patientId">
              <el-select v-model="form.patientId" filterable placeholder="请搜索并选择患者" style="width: 100%;" @change="handlePatientChange">
                <el-option
                  v-for="patient in patientOptions"
                  :key="patient.patientId"
                  :label="patient.patientName"
                  :value="patient.patientId"
                ></el-option>
              </el-select>
            </el-form-item>
            <!-- (用户要求移除主诉录入框)
            <el-form-item label="主诉" prop="chiefComplaint">
              <el-input v-model="form.chiefComplaint" type="textarea" placeholder="请输入症状描述" />
            </el-form-item>
            -->
            <el-form-item label="诊断" prop="diagnosis">
              <el-input v-model="form.diagnosis" type="textarea" placeholder="请输入诊断结果" />
            </el-form-item>
            <el-form-item label="处方明细">
              <!-- 规范化手动添加区域 -->
              <div v-for="(item, index) in dynamicPrescription" :key="index" style="margin-bottom: 10px;">
                <el-row :gutter="10" type="flex" align="middle">
                  <el-col :span="9">
                    <el-select
                      v-model="item.itemCode"
                      filterable
                      placeholder="请选择药品"
                      @change="(val) => handleMedicineChange(val, index)"
                      style="width: 100%;"
                    >
                      <el-option
                        v-for="med in inventoryOptions"
                        :key="med.itemCode"
                        :label="med.itemName + ' (剩余: ' + med.currentStock + ')'"
                        :value="med.itemCode"
                        :disabled="med.currentStock <= 0"
                      >
                        <span style="float: left">{{ med.itemName }}</span>
                        <span style="float: right; color: #8492a6; font-size: 13px">存货: {{ med.currentStock }}</span>
                      </el-option>
                    </el-select>
                  </el-col>
                  <el-col :span="5">
                    <el-input-number v-model="item.quantity" :min="1" placeholder="数量" style="width: 100%;" controls-position="right" />
                  </el-col>
                  <el-col :span="8">
                    <el-input v-model="item.dosage" placeholder="用法用法 (如:每日三次)" />
                  </el-col>
                  <el-col :span="2" style="text-align: center;">
                    <el-button type="danger" icon="el-icon-delete" circle size="mini" @click="removePrescriptionItem(index)"></el-button>
                  </el-col>
                </el-row>
              </div>
              <el-button plain icon="el-icon-plus" size="small" @click="addPrescriptionItem" style="width: 100%; border-style: dashed; margin-bottom: 15px;">传统列表加药</el-button>
              
              <!-- 自然语言解析开方区域 -->
              <div style="background-color: #f8f9fc; padding: 12px; border-radius: 6px; border: 1px dashed #dcdfe6;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                  <span style="font-size: 13px; color: #909399;">
                    <i class="el-icon-magic-stick"></i> 智能快捷开方（输入如："春泥两盒" 按回车）
                  </span>
                  <el-button type="text" size="mini" icon="el-icon-search" @click="inventoryDrawer = true" style="padding: 0;">速看库存</el-button>
                </div>
                <el-autocomplete
                  v-model="nlpInput"
                  :fetch-suggestions="querySearchInventory"
                  placeholder="请输入需开具的药品自然语言指令..."
                  style="width: 100%"
                  @keyup.enter.native="parseNaturalLanguagePrescription"
                  clearable
                >
                  <template slot="append">
                    <el-button icon="el-icon-s-promotion" type="primary" @click="parseNaturalLanguagePrescription" style="background-color: #1890ff; color: white;">AI 提取</el-button>
                  </template>
                  <!-- 联想列表模板 -->
                  <template slot-scope="{ item }">
                    <div style="display: flex; justify-content: space-between;">
                      <span style="font-weight: bold; color: #303133;">{{ item.itemName }}</span>
                      <span style="font-size: 12px; color: #909399;">剩余: {{ item.currentStock }}</span>
                    </div>
                  </template>
                </el-autocomplete>
              </div>
            </el-form-item>
          </el-form>
        </el-col>
        
        <!-- 右侧患者画像区 -->
        <el-col :span="8">
          <div style="padding: 10px;">
            <h4 style="margin-top: 5px; margin-bottom: 15px; color: #303133; border-bottom: 2px solid #e4e7ed; padding-bottom: 10px;">
              <i class="el-icon-user"></i> 患者临床画像
            </h4>
            <div v-if="!activePatientId" style="color: #909399; font-size: 13px; text-align: center; margin-top: 40px;">
              <i class="el-icon-box" style="font-size: 30px; display: block; margin-bottom: 10px;"></i>
              请先在左侧选择患者
            </div>
            <div v-else>
              <div style="font-size: 16px; font-weight: bold; margin-bottom: 12px; color: #409EFF;">
                {{ activePatientInfo.patientName }} 
                <el-tag size="mini" :type="activePatientInfo.gender === '1' ? '' : 'danger'" style="margin-left: 5px;">
                  {{ activePatientInfo.gender === '1' ? '男' : (activePatientInfo.gender === '2' ? '女' : '未知') }}
                </el-tag>
              </div>
              <div style="font-size: 14px; line-height: 1.8; color: #606266; background: #fdfdfd; padding: 15px; border-radius: 8px; border: 1px solid #ebeef5; text-align: justify;" v-html="activePatientDiagnosisHtml">
              </div>
              <div style="margin-top: 15px; font-size: 13px; color: #909399;">
                <div><i class="el-icon-phone-outline"></i> 联系电话：{{ activePatientInfo.phoneNumber || '未提供' }}</div>
                <div style="margin-top: 8px;"><i class="el-icon-location-information"></i> 年龄：{{ activePatientInfo.age ? activePatientInfo.age + '岁' : '未提供' }}</div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
      <div slot="footer" class="dialog-footer">
        <el-button type="primary" @click="submitForm">确 定</el-button>
        <el-button @click="cancel">取 消</el-button>
      </div>
    </el-dialog>

    <!-- 库存速查抽屉 (不关闭处方台) -->
    <el-drawer
      title="药房库存速查手册"
      :visible.sync="inventoryDrawer"
      direction="rtl"
      size="300px"
      append-to-body
    >
      <div style="padding: 15px; height: 100%; overflow-y: auto;">
        <el-input
          v-model="inventorySearchKeyword"
          placeholder="搜索药品名称..."
          prefix-icon="el-icon-search"
          size="small"
          clearable
          style="margin-bottom: 15px;"
        ></el-input>
        <div v-if="filteredInventoryList.length === 0" style="text-align: center; color: #999; margin-top: 30px;">
          暂无该药品或库存不足
        </div>
        <div v-else>
          <div v-for="(med, idx) in filteredInventoryList" :key="idx" 
               style="padding: 10px; border-bottom: 1px solid #ebeef5; display: flex; justify-content: space-between; align-items: center; transition: all 0.3s;"
               onmouseover="this.style.backgroundColor='#f5f7fa'"
               onmouseout="this.style.backgroundColor='transparent'"
          >
            <div>
              <div style="font-size: 14px; color: #303133; font-weight: bold; margin-bottom: 4px;">{{ med.itemName }}</div>
            </div>
            <div>
              <el-tag size="mini" :type="med.currentStock > 10 ? 'success' : 'danger'">余: {{ med.currentStock }}</el-tag>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 处方打印预览弹窗 -->
    <el-dialog title="处方打印预览" :visible.sync="printOpen" width="600px" append-to-body>
      <div id="printArea" class="print-area">
        <div style="text-align: center; border-bottom: 2px solid #333; padding-bottom: 12px; margin-bottom: 16px;">
          <h2 style="margin: 0;">Nautilus 社区诊所</h2>
          <p style="margin: 4px 0 0; color: #666; font-size: 13px;">门诊处方笺</p>
        </div>
        <table class="print-info" style="width: 100%; margin-bottom: 16px; font-size: 14px;">
          <tr>
            <td><strong>患者：</strong>{{ printData.patientName }}</td>
            <td style="text-align: right;"><strong>日期：</strong>{{ printData.date }}</td>
          </tr>
        </table>
        <div style="margin-bottom: 12px;">
          <strong>主诉：</strong>{{ printData.chiefComplaint || '-' }}
        </div>
        <div style="margin-bottom: 16px;">
          <strong>诊断：</strong>{{ printData.diagnosis || '-' }}
        </div>
        <table v-if="printData.prescriptions.length > 0" style="width: 100%; border-collapse: collapse; font-size: 14px;">
          <thead>
            <tr style="background: #f5f5f5;">
              <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">药品名称</th>
              <th style="border: 1px solid #ddd; padding: 8px; text-align: center; width: 80px;">数量</th>
              <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">用法</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(p, idx) in printData.prescriptions" :key="idx">
              <td style="border: 1px solid #ddd; padding: 8px;">{{ p.itemName || p.itemCode }}</td>
              <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{{ p.quantity }}</td>
              <td style="border: 1px solid #ddd; padding: 8px;">{{ p.dosage || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else style="color: #999; text-align: center; padding: 20px;">暂无处方明细</div>
        <div style="margin-top: 40px; display: flex; justify-content: space-between; font-size: 13px; color: #666;">
          <span>医师签名：_______________</span>
          <span>药房签名：_______________</span>
        </div>
      </div>
      <div slot="footer">
        <el-button icon="el-icon-printer" type="primary" @click="doPrint">打印处方</el-button>
        <el-button @click="printOpen = false">关闭</el-button>
      </div>
    </el-dialog>
  </div>
  <!-- Trigger HMR -->
</template>

<script>
import { listConsultation, getConsultation, delConsultation, addConsultation, updateConsultation, dispenseMedication } from "@/api/clinic/consultation";
import { listInventory } from "@/api/clinic/inventory";
import { listPatient } from "@/api/clinic/patient";

export default {
  name: "Consultation",
  data() {
    return {
      loading: true,
      showSearch: true,
      total: 0,
      consultationList: [],
      title: "",
      open: false,
      // 打印弹窗
      printOpen: false,
      printData: {
        patientName: '',
        date: '',
        chiefComplaint: '',
        diagnosis: '',
        prescriptions: []
      },
      queryParams: {
        pageNum: 1,
        pageSize: 10,
        chiefComplaint: null,
        status: null
      },
      dynamicPrescription: [],
      // NLP 智能开方文本框
      nlpInput: '',
      // 库存速看
      inventoryDrawer: false,
      inventorySearchKeyword: '',
      // 当前弹窗右侧联动的患者独立数据
      activePatientId: null,
      activePatientInfo: {},
      activePatientDiagnosisHtml: '',
      
      patientOptions: [],
      inventoryOptions: [],
      form: {},
      rules: {
        patientId: [
          { required: true, message: "患者ID不能为空", trigger: "blur" }
        ],
      }
    };
  },
  computed: {
    // 实时过滤库存抽屉
    filteredInventoryList() {
      if (!this.inventorySearchKeyword) {
        return this.inventoryOptions;
      }
      return this.inventoryOptions.filter(item => 
        item.itemName.toLowerCase().includes(this.inventorySearchKeyword.toLowerCase())
      );
    }
  },
  created() {
    this.getList();
    this.getPatientList();
    this.getInventoryList();
  },
  activated() {
    this.getList();
  },
  methods: {
    getInventoryList() {
      listInventory({ pageNum: 1, pageSize: 1000 }).then(response => {
        this.inventoryOptions = response.rows;
      });
    },
    getPatientList() {
      listPatient({ pageNum: 1, pageSize: 1000 }).then(response => {
        this.patientOptions = response.rows;
      });
    },
    getList() {
      this.loading = true;
      listConsultation(this.queryParams).then(response => {
        this.consultationList = response.rows;
        this.total = response.total;
        this.loading = false;
      });
    },
    cancel() {
      this.open = false;
      this.reset();
    },
    reset() {
      this.form = {
        consultationId: null,
        patientId: null,
        status: "1",
        chiefComplaint: null,
        diagnosis: null,
        prescriptionPayload: null
      };
      this.dynamicPrescription = [];
      this.nlpInput = '';
      this.activePatientId = null;
      this.activePatientInfo = {};
      this.activePatientDiagnosisHtml = '';
      this.resetForm("form");
    },
    handleQuery() {
      this.queryParams.pageNum = 1;
      this.getList();
    },
    resetQuery() {
      this.resetForm("queryForm");
      this.handleQuery();
    },
    handleAdd() {
      this.reset();
      this.open = true;
      this.title = "添加就诊处方";
    },
    handleUpdate(row) {
      this.reset();
      const consultationId = row.consultationId;
      getConsultation(consultationId).then(response => {
        this.form = response.data;
        if (this.form.prescriptionPayload) {
          try {
            // 将后端返回的 JSON 数组深拷贝给前端表单
            this.dynamicPrescription = JSON.parse(JSON.stringify(this.form.prescriptionPayload));
          } catch (e) {
            this.dynamicPrescription = [];
          }
        } else {
          this.dynamicPrescription = [];
        }
        
        // 修改时回显右侧面板
        if (this.form.patientId) {
          this.handlePatientChange(this.form.patientId);
        }

        this.open = true;
        this.title = "修改就诊单";
      });
    },
    submitForm() {
      this.$refs["form"].validate(valid => {
        if (valid) {
          // 在提交前将动态数组赋值回 payload
          this.form.prescriptionPayload = this.dynamicPrescription.length > 0 ? this.dynamicPrescription : null;

          if (this.form.consultationId != null) {
            updateConsultation(this.form).then(response => {
              this.$modal.msgSuccess("修改成功");
              this.open = false;
              this.getList();
            });
          } else {
            addConsultation(this.form).then(response => {
              this.$modal.msgSuccess("新增成功");
              this.open = false;
              this.getList();
            });
          }
        }
      });
    },
    handleDelete(row, index) {
      const consultationId = row.consultationId;
      const displayIndex = index !== undefined ? ((this.queryParams.pageNum - 1) * this.queryParams.pageSize + index + 1) : consultationId;
      this.$modal.confirm('是否确认删除序号为"' + displayIndex + '"的就诊单？').then(function() {
        return delConsultation(consultationId);
      }).then(() => {
        this.getList();
        this.$modal.msgSuccess("删除成功");
      }).catch(() => {});
    },
    /** 处方明细动态表单操作 */
    addPrescriptionItem() {
      this.dynamicPrescription.push({
        itemCode: "",
        itemName: "",
        quantity: 1,
        dosage: ""
      });
    },
    removePrescriptionItem(index) {
      this.dynamicPrescription.splice(index, 1);
    },
    /** 药品下拉选中时，将 itemName 同步回填到当前行 */
    handleMedicineChange(itemCode, index) {
      const selectedMed = this.inventoryOptions.find(med => med.itemCode === itemCode);
      if (selectedMed) {
        // 更新当前行的 itemName，保证 payload 数据完整
        this.$set(this.dynamicPrescription[index], 'itemName', selectedMed.itemName);
      }
    },
    getPatientName(patientId) {
      if (!this.patientOptions || this.patientOptions.length === 0) return patientId;
      const p = this.patientOptions.find(p => p.patientId === patientId);
      return p ? p.patientName : "未知患者";
    },
    /** 一键发药核心逻辑 */
    handleDispense(row, index) {
      const consultationId = row.consultationId;
      const seqNumber = index !== undefined ? ((this.queryParams.pageNum - 1) * this.queryParams.pageSize + index + 1) : "-";
      const patientName = this.getPatientName(row.patientId);
      this.$modal.confirm(`确认要对序号为【${seqNumber}】名字是${patientName}的就诊单进行发药扣除库存操作吗？这将不可逆！`, '发药确认').then(() => {
        return dispenseMedication(consultationId);
      }).then(() => {
        this.$modal.msgSuccess("发药成功，库存已安全扣除！");
        this.getList();
      }).catch(() => {});
    },
    /** 处方打印 */
    handlePrint(row) {
      this.printData = {
        patientName: this.getPatientName(row.patientId),
        date: this.parseTime(row.createTime, '{y}-{m}-{d} {h}:{i}'),
        chiefComplaint: row.chiefComplaint,
        diagnosis: row.diagnosis,
        prescriptions: row.prescriptionPayload || []
      };
      this.printOpen = true;
    },
    doPrint() {
      const printContent = document.getElementById('printArea').innerHTML;
      const printWindow = window.open('', '_blank');
      printWindow.document.write(`
        <html><head><title>处方打印</title>
        <style>
          body { font-family: 'Microsoft YaHei', sans-serif; padding: 20px; }
          table { width: 100%; border-collapse: collapse; }
          th, td { border: 1px solid #ddd; padding: 8px; }
          th { background: #f5f5f5; }
        </style></head>
        <body>${printContent}</body></html>
      `);
      printWindow.document.close();
      printWindow.focus();
      printWindow.print();
      printWindow.close();
    },
    // ---- 联动与自然语言解析专属方法 ----
    handlePatientChange(patientId) {
      if (!patientId) {
        this.activePatientId = null;
        this.activePatientInfo = {};
        this.activePatientDiagnosisHtml = '';
        return;
      }
      this.activePatientId = patientId;
      const patient = this.patientOptions.find(p => p.patientId === patientId);
      if (patient) {
        this.activePatientInfo = patient;
        this.activePatientDiagnosisHtml = this.formatPatientDiagnosisHTML(patient.dynamicProfile);
      }
    },
    formatPatientDiagnosisHTML(profile) {
      if (!profile) return '<div style="color: #999; text-align: center;">该患者暂无填写的临床画像记录</div>';
      let html = '';
      if (profile.symptoms) html += `<div style="margin-bottom: 8px;"><strong>症状：</strong>${profile.symptoms}</div>`;
      if (profile.allergies && profile.allergies.length > 0) {
        let allergyStr = Array.isArray(profile.allergies) ? profile.allergies.join('、') : profile.allergies;
        html += `<div style="margin-bottom: 8px; color: #F56C6C;"><strong><i class="el-icon-warning-outline"></i> 过敏史：</strong>${allergyStr}</div>`;
      }
      if (profile.bloodType) html += `<div style="margin-bottom: 8px;"><strong>血型：</strong>${profile.bloodType}</div>`;
      if (profile.tags && profile.tags.length > 0) {
        let tagsStr = Array.isArray(profile.tags) ? profile.tags.join('、') : profile.tags;
        html += `<div><strong>标签：</strong>${tagsStr}</div>`;
      }
      return html || '<div style="color: #999; text-align: center;">该患者暂无临床诊断详情</div>';
    },
    // autocomplete 获取联想列表
    querySearchInventory(queryString, cb) {
      const allInventory = this.inventoryOptions;
      // 当输入至少一个字后进行筛选
      if (queryString) {
        const results = allInventory.filter(item => 
          item.itemName.toLowerCase().indexOf(queryString.toLowerCase()) > -1 && 
          item.currentStock > 0
        );
        // Autocomplete 组件需要 value 属性用于展示在输入框
        results.forEach(item => item.value = item.itemName);
        cb(results);
      } else {
        cb([]);
      }
    },
    // 解析自然语言核心函数 (支持一句话多个药，带严格隔离)
    parseNaturalLanguagePrescription() {
      const text = this.nlpInput.trim();
      if (!text) return;

      const cnNumberMap = {
        '〇': 0, '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
      };

      // 0. 【第一层净化】提取所有的用法嘱咐，并在替代文本中将其彻底抹去！
      let foundDosages = [];
      // 增强版正则：支持“一日三次”、“每次两粒”、“一次两粒”、“睡前服”、“饭后”... 且全局匹配
      const dosagePattern = /(?:每[日天]|一[日天])[一二两三四五六七八九十\d]+次|(?:每|一)次[一二两三四五六七八九十\d]+[粒包片支颗瓶剂滴毫升mlg克]+|睡前服?|饭[前后]服?|空腹服?/g;
      let textWithoutDosage = text;
      let dMatch;
      while ((dMatch = dosagePattern.exec(text)) !== null) {
        foundDosages.push({ index: dMatch.index, text: dMatch[0] });
        // 使用一个占位字符替代，以免后续找数量的时候因为索引错位而混乱，且防止其中的任何字被意外匹配
        textWithoutDosage = textWithoutDosage.substring(0, dMatch.index) + "■".repeat(dMatch[0].length) + textWithoutDosage.substring(dMatch.index + dMatch[0].length);
      }

      // 1. **药名词汇挖掘**：扫描整句话，把所有出现的药名找出来
      let foundMeds = [];
      const sortedInventory = [...this.inventoryOptions].sort((a, b) => b.itemName.length - a.itemName.length);
      
      for (const inv of sortedInventory) {
        let searchIdx = 0;
        let idx;
        while ((idx = text.indexOf(inv.itemName, searchIdx)) !== -1) {
          let isCovered = foundMeds.some(m => idx >= m.index && idx < (m.index + m.item.itemName.length));
          if (!isCovered) {
            foundMeds.push({
              index: idx,
              item: inv,
              quantity: null,
              dosage: []
            });
            // 顺手连药名也从分析本里抹去，让后文提纯到极致
            textWithoutDosage = textWithoutDosage.substring(0, idx) + "■".repeat(inv.itemName.length) + textWithoutDosage.substring(idx + inv.itemName.length);
          }
          searchIdx = idx + inv.itemName.length;
        }
      }
      
      foundMeds.sort((a, b) => a.index - b.index);

      if (foundMeds.length === 0) {
        this.$message.warning("提取失败：你没有填写库存中存在的“药品名字”");
        return;
      }

      // 2.【划价数量提取】 - 基于【被极致打码的 textWithoutDosage】
      // 此时所有 "两次" "两粒" "感冒胶囊" 都变成了 "■■■■"！
      let foundQuantities = [];
      const qPattern = /([0-9]+|[一二两三四五六七八九十])\s*(盒|克|粒|支|包|瓶|副|片|颗|袋|剂)/g;
      let m;
      while ((m = qPattern.exec(textWithoutDosage)) !== null) {
        let val = /^[0-9]+$/.test(m[1]) ? parseInt(m[1], 10) : cnNumberMap[m[1]];
        foundQuantities.push({ index: m.index, value: val, matched: false });
      }
      
      // 补充兜底逻辑：只写了“拿2”或者“二” 没有带量词单位，找“拿/开/数量为/加”等前缀
      // (注意：这里在被抠干净的文本里找“2”，绝不可能再找到之前那句“两次”里被抠掉的“两”了！)
      const loosePattern = /(?:数量为|拿|开|给|加)\s*([0-9]+|[一二两三四五六七八九十])(?!\s*(?:盒|克|粒|支|包|瓶|副|片|颗|袋|剂))/g;
      while ((m = loosePattern.exec(textWithoutDosage)) !== null) {
        let val = /^[0-9]+$/.test(m[1]) ? parseInt(m[1], 10) : cnNumberMap[m[1]];
        foundQuantities.push({ index: m.index, value: val, matched: false });
      }

      // 3. **为每个药品跨距离配对组合要素**
      for (let med of foundMeds) {
        // --- 配对该药品最近的划价数量 ---
        let nearestQ = null;
        let minDistanceQ = Infinity;
        for (let q of foundQuantities) {
          if (!q.matched) {
            let dist = Math.abs(q.index - med.index);
            if (dist < minDistanceQ) {
              minDistanceQ = dist;
              nearestQ = q;
            }
          }
        }
        // 反推绑定
        if (nearestQ && minDistanceQ < 50) {
          nearestQ.matched = true;
          med.quantity = nearestQ.value;
        }
      }

      // --- 将用法嘱咐分发给在其上方最近诞生的那款药品 ---
      for (let d of foundDosages) {
         let assignedMed = null;
         let minDistance = Infinity;
         for (let med of foundMeds) {
           let dist = d.index - med.index;
           // 确保用法在药名后面出现，并且是距离最近的那个药
           if (dist > 0 && dist < minDistance) {
             minDistance = dist;
             assignedMed = med;
           }
         }
         // 兜底：如果用户倒装句把用法写在了所有药最前面，就全算给第一个药
         if (!assignedMed) {
            assignedMed = foundMeds[0];
         }
         if (assignedMed) {
            assignedMed.dosage.push(d.text);
         }
      }

      // 4. **统一推入处方组装并提示错误**
      let successCount = 0;
      let errorMsgs = [];
      
      for (let med of foundMeds) {
        if (!med.quantity || med.quantity <= 0) {
          errorMsgs.push(`未写明【${med.item.itemName}】的提货数量！(如补一句“拿两盒”)`);
        } else if (med.quantity > med.item.currentStock) {
          errorMsgs.push(`库存不足：【${med.item.itemName}】仅剩 ${med.item.currentStock} 件，数量过高被拦截！`);
        } else {
          // 成功加药
          this.dynamicPrescription.push({
            itemCode: med.item.itemCode,
            itemName: med.item.itemName,
            quantity: med.quantity,
            dosage: med.dosage.length > 0 ? med.dosage.join("，") : ""
          });
          successCount++;
        }
      }

      if (successCount > 0) {
        this.$message.success(`智能识别成功！共为您提取了 ${successCount} 种药品。`);
        this.nlpInput = ''; // 解析成功后清空面板，准备下一次开
      }
      if (errorMsgs.length > 0) {
        this.$message.warning(errorMsgs.join(" | "));
      }
    }
  }
};
</script>
