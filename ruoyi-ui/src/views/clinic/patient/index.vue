<template>
  <div class="app-container">
    <el-card shadow="never" style="margin-bottom: 20px;">
      <el-form :model="queryParams" ref="queryForm" size="small" :inline="true" v-show="showSearch" label-width="68px">
        <!-- 基础搜索 -->
        <el-form-item label="患者姓名" prop="patientName">
          <el-input
            v-model="queryParams.patientName"
            placeholder="请输入患者姓名"
            clearable
            @keyup.enter.native="handleQuery"
          />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="queryParams.phone"
            placeholder="请输入手机号"
            clearable
            @keyup.enter.native="handleQuery"
          />
        </el-form-item>

        <!-- JSONB 高级检索栏 -->
        <el-form-item label="患者标签" prop="tag">
          <el-input
            v-model="advancedQueryParams.tag"
            placeholder="请输入动态标签 (如 Yorushika铁粉)"
            clearable
            @keyup.enter.native="handleAdvancedQuery"
          />
        </el-form-item>
        <el-form-item label="过敏原" prop="allergy">
          <el-input
            v-model="advancedQueryParams.allergy"
            placeholder="请输入过敏原 (如 春泥)"
            clearable
            @keyup.enter.native="handleAdvancedQuery"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" icon="el-icon-search" size="mini" @click="handleQuery">基础搜索</el-button>
          <el-button type="danger" icon="el-icon-camera" size="mini" @click="handleAdvancedQuery">JSONB 高级检索</el-button>
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
        >新增患者</el-button>
      </el-col>
      <right-toolbar :showSearch.sync="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <!-- 列表数据 -->
    <el-table v-loading="loading" :data="patientList" @selection-change="handleSelectionChange">
      <el-table-column label="序号" type="index" width="80" align="center" />
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="患者编号" align="center" prop="patientId" v-if="false" />
      <el-table-column label="患者姓名" align="center" prop="patientName" />
      <el-table-column label="性别" align="center" prop="gender">
        <template slot-scope="scope">
          <span v-if="scope.row.gender === '0'">男</span>
          <span v-else-if="scope.row.gender === '1'">女</span>
          <span v-else>未知</span>
        </template>
      </el-table-column>
      <el-table-column label="年龄" align="center" prop="age" width="80" />
      <el-table-column label="科别" align="center" prop="department" />
      <el-table-column label="手机号" align="center" prop="phoneNumber" />
      
      <!-- 核心：解析展示 JSONB 动态画像 -->
      <el-table-column label="临床诊断" align="left" min-width="250">
        <template slot-scope="scope">
          <div v-if="scope.row.dynamicProfile" @click="showDiagnosisDetail(scope.row)" style="cursor: pointer; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; color: #606266; font-size: 13px; line-height: 1.5; padding: 4px; border-radius: 4px;" title="点击查看详情" class="diagnosis-cell" v-html="formatClinicalDiagnosis(scope.row.dynamicProfile)">
          </div>
          <span v-else style="color: #999;">暂无诊断</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="220">
        <template slot-scope="scope">
          <el-button
            size="mini"
            type="text"
            icon="el-icon-time"
            @click="handleTimeline(scope.row)"
          >就诊历史</el-button>
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
            @click="handleDelete(scope.row)"
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

    <!-- 添加或修改患者对话框 -->
    <el-dialog :title="title" :visible.sync="open" width="500px" append-to-body :close-on-click-modal="false">
      <el-form ref="form" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="患者姓名" prop="patientName">
          <el-input v-model="form.patientName" placeholder="请输入患者姓名" />
        </el-form-item>
        <el-row>
          <el-col :span="8">
            <el-form-item label="性别" prop="gender">
              <el-select v-model="form.gender" placeholder="请选择" style="width: 100%;">
                <el-option label="男" value="0"></el-option>
                <el-option label="女" value="1"></el-option>
                <el-option label="未知" value="2"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="年龄" prop="age">
              <el-input-number v-model="form.age" :min="0" :max="150" placeholder="年龄" style="width: 100%;"></el-input-number>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="科别" prop="department">
              <el-select v-model="form.department" placeholder="请选择" clearable style="width: 100%;">
                <el-option label="内科" value="内科"></el-option>
                <el-option label="外科" value="外科"></el-option>
                <el-option label="儿科" value="儿科"></el-option>
                <el-option label="妇科" value="妇科"></el-option>
                <el-option label="全科" value="全科"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="手机号" prop="phoneNumber">
          <el-input v-model="form.phoneNumber" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="联系地址" required>
          <div style="display: flex; gap: 10px;">
            <div style="flex: 2;">
              <el-cascader
                v-model="form.region"
                :options="regionOptions"
                placeholder="请选择省市区"
                style="width: 100%"
                clearable
              ></el-cascader>
            </div>
            <div style="flex: 3;">
              <el-form-item prop="address" style="margin-bottom: 0;">
                <el-input v-model="form.address" placeholder="请输入详细地址" />
              </el-form-item>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="临床诊断" prop="symptoms">
          <el-input v-model="dynamicForm.symptoms" type="textarea" rows="3" placeholder="请输入患者的临床诊断" />
        </el-form-item>
        <el-form-item label="过敏史" prop="allergies">
          <el-input v-model="dynamicForm.allergies" placeholder="请输入患者过敏史（如没有请留空）" />
        </el-form-item>
        <el-form-item label="血型" prop="bloodType">
          <el-select v-model="dynamicForm.bloodType" placeholder="请选择血型" clearable style="width: 100%;">
            <el-option label="A型" value="A"></el-option>
            <el-option label="B型" value="B"></el-option>
            <el-option label="AB型" value="AB"></el-option>
            <el-option label="O型" value="O"></el-option>
            <el-option label="其它" value="其它"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <div slot="footer" class="dialog-footer">
        <el-button type="primary" @click="submitForm">确 定</el-button>
        <el-button @click="cancel">取 消</el-button>
      </div>
    </el-dialog>

    <!-- 就诊历史时间线抽屉 -->
    <el-drawer
      :title="timelineTitle"
      :visible.sync="timelineOpen"
      direction="rtl"
      size="520px"
    >
      <div style="padding: 0 24px 24px;">
        <div v-if="timelineLoading" style="text-align: center; padding: 60px 0;">
          <i class="el-icon-loading" style="font-size: 28px; color: #409EFF;"></i>
          <p style="color: #909399; margin-top: 12px;">加载中</p>
        </div>
        <div v-else-if="timelineList.length === 0" style="text-align: center; padding: 60px 0;">
          <i class="el-icon-document" style="font-size: 40px; color: #c0c4cc;"></i>
          <p style="color: #909399; margin-top: 12px;">暂无就诊记录</p>
        </div>
        <el-timeline v-else>
          <el-timeline-item
            v-for="(item, index) in timelineList"
            :key="index"
            :timestamp="parseTime(item.createTime, '{y}-{m}-{d} {h}:{i}')"
            placement="top"
            :type="item.status === '1' ? 'warning' : item.status === '2' ? 'success' : 'info'"
            :icon="item.status === '1' ? 'el-icon-time' : item.status === '2' ? 'el-icon-check' : 'el-icon-document'"
          >
            <el-card shadow="hover" style="margin-bottom: 4px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-weight: bold; font-size: 15px;">{{ item.chiefComplaint || '未填写主诉' }}</span>
                <el-tag size="small" :type="item.status === '1' ? 'warning' : item.status === '2' ? 'success' : 'info'">
                  {{ item.status === '1' ? '待发药' : item.status === '2' ? '已发药' : '已归档' }}
                </el-tag>
              </div>
              <div v-if="item.diagnosis" style="margin-bottom: 8px; color: #606266; font-size: 13px;">
                <i class="el-icon-first-aid-kit" style="margin-right: 4px; color: #E6A23C;"></i>
                <strong>诊断：</strong>{{ item.diagnosis }}
              </div>
              <div v-if="item.prescriptionPayload && item.prescriptionPayload.length > 0">
                <div style="font-size: 12px; color: #909399; margin-bottom: 6px;">处方明细：</div>
                <el-tag
                  v-for="(drug, dIdx) in item.prescriptionPayload"
                  :key="dIdx"
                  size="small"
                  effect="plain"
                  style="margin-right: 6px; margin-bottom: 6px;"
                >
                   {{ drug.itemName || drug.itemCode }} x{{ drug.quantity }}
                </el-tag>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-drawer>
  </div>
</template>

<script>
import { listPatient, advancedSearchPatient, getPatient, delPatient, addPatient, updatePatient } from "@/api/clinic/patient";
import { getConsultationTimeline } from "@/api/clinic/consultation";

export default {
  name: "Patient",
  data() {
    return {
      // 遮罩层
      loading: true,
      // 选中数组
      ids: [],
      // 非单个禁用
      single: true,
      // 非多个禁用
      multiple: true,
      // 显示搜索条件
      showSearch: true,
      // 总条数
      total: 0,
      // 患者表格数据
      patientList: [],
      // 弹出层标题
      title: "",
      // 是否显示弹出层
      open: false,
      // 时间线抽屉
      timelineOpen: false,
      timelineLoading: false,
      timelineTitle: '',
      timelineList: [],
      // 基础查询参数
      queryParams: {
        pageNum: 1,
        pageSize: 10,
        patientName: null,
        phoneNumber: null
      },
      // 高级 JSONB 查询参数
      advancedQueryParams: {
        tag: null,
        allergy: null
      },
      // 动态 JSONB 映射表单
      dynamicForm: {
        symptoms: '',
        allergies: '',
        bloodType: ''
      },
      // 简易省市区选项 (Mock)
      regionOptions: [
          {
              "value": "四川省",
              "label": "四川省",
              "children": [
                  {
                      "value": "成都市",
                      "label": "成都市",
                      "children": [
                          {
                              "value": "锦江区",
                              "label": "锦江区"
                          },
                          {
                              "value": "青羊区",
                              "label": "青羊区"
                          },
                          {
                              "value": "金牛区",
                              "label": "金牛区"
                          },
                          {
                              "value": "武侯区",
                              "label": "武侯区"
                          },
                          {
                              "value": "成华区",
                              "label": "成华区"
                          },
                          {
                              "value": "龙泉驿区",
                              "label": "龙泉驿区"
                          },
                          {
                              "value": "青白江区",
                              "label": "青白江区"
                          },
                          {
                              "value": "新都区",
                              "label": "新都区"
                          },
                          {
                              "value": "温江区",
                              "label": "温江区"
                          },
                          {
                              "value": "双流区",
                              "label": "双流区"
                          },
                          {
                              "value": "郫都区",
                              "label": "郫都区"
                          },
                          {
                              "value": "新津区",
                              "label": "新津区"
                          },
                          {
                              "value": "金堂县",
                              "label": "金堂县"
                          },
                          {
                              "value": "大邑县",
                              "label": "大邑县"
                          },
                          {
                              "value": "蒲江县",
                              "label": "蒲江县"
                          },
                          {
                              "value": "都江堰市",
                              "label": "都江堰市"
                          },
                          {
                              "value": "彭州市",
                              "label": "彭州市"
                          },
                          {
                              "value": "邛崃市",
                              "label": "邛崃市"
                          },
                          {
                              "value": "崇州市",
                              "label": "崇州市"
                          },
                          {
                              "value": "简阳市",
                              "label": "简阳市"
                          }
                      ]
                  },
                  {
                      "value": "自贡市",
                      "label": "自贡市",
                      "children": [
                          {
                              "value": "自流井区",
                              "label": "自流井区"
                          },
                          {
                              "value": "贡井区",
                              "label": "贡井区"
                          },
                          {
                              "value": "大安区",
                              "label": "大安区"
                          },
                          {
                              "value": "沿滩区",
                              "label": "沿滩区"
                          },
                          {
                              "value": "荣县",
                              "label": "荣县"
                          },
                          {
                              "value": "富顺县",
                              "label": "富顺县"
                          }
                      ]
                  },
                  {
                      "value": "攀枝花市",
                      "label": "攀枝花市",
                      "children": [
                          {
                              "value": "东区",
                              "label": "东区"
                          },
                          {
                              "value": "西区",
                              "label": "西区"
                          },
                          {
                              "value": "仁和区",
                              "label": "仁和区"
                          },
                          {
                              "value": "米易县",
                              "label": "米易县"
                          },
                          {
                              "value": "盐边县",
                              "label": "盐边县"
                          }
                      ]
                  },
                  {
                      "value": "泸州市",
                      "label": "泸州市",
                      "children": [
                          {
                              "value": "江阳区",
                              "label": "江阳区"
                          },
                          {
                              "value": "纳溪区",
                              "label": "纳溪区"
                          },
                          {
                              "value": "龙马潭区",
                              "label": "龙马潭区"
                          },
                          {
                              "value": "泸县",
                              "label": "泸县"
                          },
                          {
                              "value": "合江县",
                              "label": "合江县"
                          },
                          {
                              "value": "叙永县",
                              "label": "叙永县"
                          },
                          {
                              "value": "古蔺县",
                              "label": "古蔺县"
                          }
                      ]
                  },
                  {
                      "value": "德阳市",
                      "label": "德阳市",
                      "children": [
                          {
                              "value": "旌阳区",
                              "label": "旌阳区"
                          },
                          {
                              "value": "罗江区",
                              "label": "罗江区"
                          },
                          {
                              "value": "中江县",
                              "label": "中江县"
                          },
                          {
                              "value": "广汉市",
                              "label": "广汉市"
                          },
                          {
                              "value": "什邡市",
                              "label": "什邡市"
                          },
                          {
                              "value": "绵竹市",
                              "label": "绵竹市"
                          }
                      ]
                  },
                  {
                      "value": "绵阳市",
                      "label": "绵阳市",
                      "children": [
                          {
                              "value": "涪城区",
                              "label": "涪城区"
                          },
                          {
                              "value": "游仙区",
                              "label": "游仙区"
                          },
                          {
                              "value": "安州区",
                              "label": "安州区"
                          },
                          {
                              "value": "三台县",
                              "label": "三台县"
                          },
                          {
                              "value": "盐亭县",
                              "label": "盐亭县"
                          },
                          {
                              "value": "梓潼县",
                              "label": "梓潼县"
                          },
                          {
                              "value": "北川羌族自治县",
                              "label": "北川羌族自治县"
                          },
                          {
                              "value": "平武县",
                              "label": "平武县"
                          },
                          {
                              "value": "江油市",
                              "label": "江油市"
                          }
                      ]
                  },
                  {
                      "value": "广元市",
                      "label": "广元市",
                      "children": [
                          {
                              "value": "利州区",
                              "label": "利州区"
                          },
                          {
                              "value": "昭化区",
                              "label": "昭化区"
                          },
                          {
                              "value": "朝天区",
                              "label": "朝天区"
                          },
                          {
                              "value": "旺苍县",
                              "label": "旺苍县"
                          },
                          {
                              "value": "青川县",
                              "label": "青川县"
                          },
                          {
                              "value": "剑阁县",
                              "label": "剑阁县"
                          },
                          {
                              "value": "苍溪县",
                              "label": "苍溪县"
                          }
                      ]
                  },
                  {
                      "value": "遂宁市",
                      "label": "遂宁市",
                      "children": [
                          {
                              "value": "船山区",
                              "label": "船山区"
                          },
                          {
                              "value": "安居区",
                              "label": "安居区"
                          },
                          {
                              "value": "蓬溪县",
                              "label": "蓬溪县"
                          },
                          {
                              "value": "大英县",
                              "label": "大英县"
                          },
                          {
                              "value": "射洪市",
                              "label": "射洪市"
                          }
                      ]
                  },
                  {
                      "value": "内江市",
                      "label": "内江市",
                      "children": [
                          {
                              "value": "市中区",
                              "label": "市中区"
                          },
                          {
                              "value": "东兴区",
                              "label": "东兴区"
                          },
                          {
                              "value": "威远县",
                              "label": "威远县"
                          },
                          {
                              "value": "资中县",
                              "label": "资中县"
                          },
                          {
                              "value": "隆昌市",
                              "label": "隆昌市"
                          }
                      ]
                  },
                  {
                      "value": "乐山市",
                      "label": "乐山市",
                      "children": [
                          {
                              "value": "市中区",
                              "label": "市中区"
                          },
                          {
                              "value": "沙湾区",
                              "label": "沙湾区"
                          },
                          {
                              "value": "五通桥区",
                              "label": "五通桥区"
                          },
                          {
                              "value": "金口河区",
                              "label": "金口河区"
                          },
                          {
                              "value": "犍为县",
                              "label": "犍为县"
                          },
                          {
                              "value": "井研县",
                              "label": "井研县"
                          },
                          {
                              "value": "夹江县",
                              "label": "夹江县"
                          },
                          {
                              "value": "沐川县",
                              "label": "沐川县"
                          },
                          {
                              "value": "峨边彝族自治县",
                              "label": "峨边彝族自治县"
                          },
                          {
                              "value": "马边彝族自治县",
                              "label": "马边彝族自治县"
                          },
                          {
                              "value": "峨眉山市",
                              "label": "峨眉山市"
                          }
                      ]
                  },
                  {
                      "value": "南充市",
                      "label": "南充市",
                      "children": [
                          {
                              "value": "顺庆区",
                              "label": "顺庆区"
                          },
                          {
                              "value": "高坪区",
                              "label": "高坪区"
                          },
                          {
                              "value": "嘉陵区",
                              "label": "嘉陵区"
                          },
                          {
                              "value": "南部县",
                              "label": "南部县"
                          },
                          {
                              "value": "营山县",
                              "label": "营山县"
                          },
                          {
                              "value": "蓬安县",
                              "label": "蓬安县"
                          },
                          {
                              "value": "仪陇县",
                              "label": "仪陇县"
                          },
                          {
                              "value": "西充县",
                              "label": "西充县"
                          },
                          {
                              "value": "阆中市",
                              "label": "阆中市"
                          }
                      ]
                  },
                  {
                      "value": "眉山市",
                      "label": "眉山市",
                      "children": [
                          {
                              "value": "东坡区",
                              "label": "东坡区"
                          },
                          {
                              "value": "彭山区",
                              "label": "彭山区"
                          },
                          {
                              "value": "仁寿县",
                              "label": "仁寿县"
                          },
                          {
                              "value": "洪雅县",
                              "label": "洪雅县"
                          },
                          {
                              "value": "丹棱县",
                              "label": "丹棱县"
                          },
                          {
                              "value": "青神县",
                              "label": "青神县"
                          }
                      ]
                  },
                  {
                      "value": "宜宾市",
                      "label": "宜宾市",
                      "children": [
                          {
                              "value": "翠屏区",
                              "label": "翠屏区"
                          },
                          {
                              "value": "南溪区",
                              "label": "南溪区"
                          },
                          {
                              "value": "叙州区",
                              "label": "叙州区"
                          },
                          {
                              "value": "江安县",
                              "label": "江安县"
                          },
                          {
                              "value": "长宁县",
                              "label": "长宁县"
                          },
                          {
                              "value": "高县",
                              "label": "高县"
                          },
                          {
                              "value": "珙县",
                              "label": "珙县"
                          },
                          {
                              "value": "筠连县",
                              "label": "筠连县"
                          },
                          {
                              "value": "兴文县",
                              "label": "兴文县"
                          },
                          {
                              "value": "屏山县",
                              "label": "屏山县"
                          }
                      ]
                  },
                  {
                      "value": "广安市",
                      "label": "广安市",
                      "children": [
                          {
                              "value": "广安区",
                              "label": "广安区"
                          },
                          {
                              "value": "前锋区",
                              "label": "前锋区"
                          },
                          {
                              "value": "岳池县",
                              "label": "岳池县"
                          },
                          {
                              "value": "武胜县",
                              "label": "武胜县"
                          },
                          {
                              "value": "邻水县",
                              "label": "邻水县"
                          },
                          {
                              "value": "华蓥市",
                              "label": "华蓥市"
                          }
                      ]
                  },
                  {
                      "value": "达州市",
                      "label": "达州市",
                      "children": [
                          {
                              "value": "通川区",
                              "label": "通川区"
                          },
                          {
                              "value": "达川区",
                              "label": "达川区"
                          },
                          {
                              "value": "宣汉县",
                              "label": "宣汉县"
                          },
                          {
                              "value": "开江县",
                              "label": "开江县"
                          },
                          {
                              "value": "大竹县",
                              "label": "大竹县"
                          },
                          {
                              "value": "渠县",
                              "label": "渠县"
                          },
                          {
                              "value": "万源市",
                              "label": "万源市"
                          }
                      ]
                  },
                  {
                      "value": "雅安市",
                      "label": "雅安市",
                      "children": [
                          {
                              "value": "雨城区",
                              "label": "雨城区"
                          },
                          {
                              "value": "名山区",
                              "label": "名山区"
                          },
                          {
                              "value": "荥经县",
                              "label": "荥经县"
                          },
                          {
                              "value": "汉源县",
                              "label": "汉源县"
                          },
                          {
                              "value": "石棉县",
                              "label": "石棉县"
                          },
                          {
                              "value": "天全县",
                              "label": "天全县"
                          },
                          {
                              "value": "芦山县",
                              "label": "芦山县"
                          },
                          {
                              "value": "宝兴县",
                              "label": "宝兴县"
                          }
                      ]
                  },
                  {
                      "value": "巴中市",
                      "label": "巴中市",
                      "children": [
                          {
                              "value": "巴州区",
                              "label": "巴州区"
                          },
                          {
                              "value": "恩阳区",
                              "label": "恩阳区"
                          },
                          {
                              "value": "通江县",
                              "label": "通江县"
                          },
                          {
                              "value": "南江县",
                              "label": "南江县"
                          },
                          {
                              "value": "平昌县",
                              "label": "平昌县"
                          }
                      ]
                  },
                  {
                      "value": "资阳市",
                      "label": "资阳市",
                      "children": [
                          {
                              "value": "雁江区",
                              "label": "雁江区"
                          },
                          {
                              "value": "安岳县",
                              "label": "安岳县"
                          },
                          {
                              "value": "乐至县",
                              "label": "乐至县"
                          }
                      ]
                  },
                  {
                      "value": "阿坝藏族羌族自治州",
                      "label": "阿坝藏族羌族自治州",
                      "children": [
                          {
                              "value": "马尔康市",
                              "label": "马尔康市"
                          },
                          {
                              "value": "汶川县",
                              "label": "汶川县"
                          },
                          {
                              "value": "理县",
                              "label": "理县"
                          },
                          {
                              "value": "茂县",
                              "label": "茂县"
                          },
                          {
                              "value": "松潘县",
                              "label": "松潘县"
                          },
                          {
                              "value": "九寨沟县",
                              "label": "九寨沟县"
                          },
                          {
                              "value": "金川县",
                              "label": "金川县"
                          },
                          {
                              "value": "小金县",
                              "label": "小金县"
                          },
                          {
                              "value": "黑水县",
                              "label": "黑水县"
                          },
                          {
                              "value": "壤塘县",
                              "label": "壤塘县"
                          },
                          {
                              "value": "阿坝县",
                              "label": "阿坝县"
                          },
                          {
                              "value": "若尔盖县",
                              "label": "若尔盖县"
                          },
                          {
                              "value": "红原县",
                              "label": "红原县"
                          }
                      ]
                  },
                  {
                      "value": "甘孜藏族自治州",
                      "label": "甘孜藏族自治州",
                      "children": [
                          {
                              "value": "康定市",
                              "label": "康定市"
                          },
                          {
                              "value": "泸定县",
                              "label": "泸定县"
                          },
                          {
                              "value": "丹巴县",
                              "label": "丹巴县"
                          },
                          {
                              "value": "九龙县",
                              "label": "九龙县"
                          },
                          {
                              "value": "雅江县",
                              "label": "雅江县"
                          },
                          {
                              "value": "道孚县",
                              "label": "道孚县"
                          },
                          {
                              "value": "炉霍县",
                              "label": "炉霍县"
                          },
                          {
                              "value": "甘孜县",
                              "label": "甘孜县"
                          },
                          {
                              "value": "新龙县",
                              "label": "新龙县"
                          },
                          {
                              "value": "德格县",
                              "label": "德格县"
                          },
                          {
                              "value": "白玉县",
                              "label": "白玉县"
                          },
                          {
                              "value": "石渠县",
                              "label": "石渠县"
                          },
                          {
                              "value": "色达县",
                              "label": "色达县"
                          },
                          {
                              "value": "理塘县",
                              "label": "理塘县"
                          },
                          {
                              "value": "巴塘县",
                              "label": "巴塘县"
                          },
                          {
                              "value": "乡城县",
                              "label": "乡城县"
                          },
                          {
                              "value": "稻城县",
                              "label": "稻城县"
                          },
                          {
                              "value": "得荣县",
                              "label": "得荣县"
                          }
                      ]
                  },
                  {
                      "value": "凉山彝族自治州",
                      "label": "凉山彝族自治州",
                      "children": [
                          {
                              "value": "西昌市",
                              "label": "西昌市"
                          },
                          {
                              "value": "会理市",
                              "label": "会理市"
                          },
                          {
                              "value": "木里藏族自治县",
                              "label": "木里藏族自治县"
                          },
                          {
                              "value": "盐源县",
                              "label": "盐源县"
                          },
                          {
                              "value": "德昌县",
                              "label": "德昌县"
                          },
                          {
                              "value": "会东县",
                              "label": "会东县"
                          },
                          {
                              "value": "宁南县",
                              "label": "宁南县"
                          },
                          {
                              "value": "普格县",
                              "label": "普格县"
                          },
                          {
                              "value": "布拖县",
                              "label": "布拖县"
                          },
                          {
                              "value": "金阳县",
                              "label": "金阳县"
                          },
                          {
                              "value": "昭觉县",
                              "label": "昭觉县"
                          },
                          {
                              "value": "喜德县",
                              "label": "喜德县"
                          },
                          {
                              "value": "冕宁县",
                              "label": "冕宁县"
                          },
                          {
                              "value": "越西县",
                              "label": "越西县"
                          },
                          {
                              "value": "甘洛县",
                              "label": "甘洛县"
                          },
                          {
                              "value": "美姑县",
                              "label": "美姑县"
                          },
                          {
                              "value": "雷波县",
                              "label": "雷波县"
                          }
                      ]
                  }
              ]
          }
      ],
      // 表单参数
      form: {},
      // 表单校验
      rules: {
        patientName: [
          { required: true, message: "患者姓名不能为空", trigger: "blur" }
        ],
        phoneNumber: [
          { pattern: /^1[3-9]\d{9}$/, message: "请输入正确的11位手机号码", trigger: "blur" }
        ],
        address: [
          { required: true, message: "联系详细地址不能为空", trigger: "blur" }
        ]
      }
    };
  },
  created() {
    this.getList();
  },
  activated() {
    this.getList();
  },
  methods: {
    formatClinicalDiagnosis(profile) {
      if (!profile) return '暂无';
      let text = profile.symptoms ? `<strong>临床诊断：</strong>${profile.symptoms}` : '';
      if (profile.allergies && profile.allergies.length > 0) {
        const allergyStr = Array.isArray(profile.allergies) ? profile.allergies.join('、') : profile.allergies;
        text += (text ? '。' : '') + `<strong>过敏史：</strong>${allergyStr}`;
      }
      if (profile.bloodType) {
        text += (text ? '。' : '') + `<strong>血型：</strong>${profile.bloodType}`;
      }
      if (profile.tags && profile.tags.length > 0) {
        text += (text ? '。' : '') + `<strong>标签：</strong>${Array.isArray(profile.tags) ? profile.tags.join('、') : profile.tags}`;
      }
      return text || '暂无临床诊断';
    },
    showDiagnosisDetail(row) {
      const htmlText = this.formatClinicalDiagnosis(row.dynamicProfile);
      this.$alert(`<div style="font-size: 14px; line-height: 1.6;">${htmlText}</div>`, '临床诊断详情', {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '确定'
      });
    },
    /** 查询患者列表 */
    getList() {
      this.loading = true;
      listPatient(this.queryParams).then(response => {
        this.patientList = response.rows;
        this.total = response.total;
        this.loading = false;
      });
    },
    // 取消按钮
    cancel() {
      this.open = false;
      this.reset();
    },
    // 表单重置
    reset() {
      this.form = {
        patientId: null,
        patientName: null,
        gender: "0",
        age: null,
        department: null,
        phoneNumber: null,
        region: [],
        address: null,
        dynamicProfile: null
      };
      this.dynamicForm = {
        symptoms: '',
        allergies: '',
        bloodType: ''
      };
      this.resetForm("form");
    },
    /** 基础搜索按钮操作 */
    handleQuery() {
      this.queryParams.pageNum = 1;
      this.getList();
    },
    /** JSONB 高级检索按钮操作 */
    handleAdvancedQuery() {
      this.loading = true;
      advancedSearchPatient({
        tag: this.advancedQueryParams.tag,
        allergy: this.advancedQueryParams.allergy,
        pageNum: this.queryParams.pageNum,
        pageSize: this.queryParams.pageSize
      }).then(response => {
        this.patientList = response.rows;
        this.total = response.total;
        this.loading = false;
      }).catch(() => {
        this.loading = false;
      });
    },
    /** 重置按钮操作 */
    resetQuery() {
      this.advancedQueryParams.tag = null;
      this.advancedQueryParams.allergy = null;
      this.resetForm("queryForm");
      this.handleQuery();
    },
    // 多选框选中数据
    handleSelectionChange(selection) {
      this.ids = selection.map(item => item.patientId)
      this.single = selection.length!==1
      this.multiple = !selection.length
    },
    /** 新增按钮操作 */
    handleAdd() {
      this.reset();
      this.open = true;
      this.title = "添加患者";
    },
    /** 修改按钮操作 */
    handleUpdate(row) {
      this.reset();
      const patientId = row.patientId || this.ids
      getPatient(patientId).then(response => {
        this.form = response.data;
        if (!this.form.region) {
          this.form.region = [];
        }
        // 拆解并回显 JSONB 对象供前端表单展示
        if (this.form.dynamicProfile) {
          const profile = this.form.dynamicProfile;
          this.dynamicForm.symptoms = profile.symptoms || '';
          this.dynamicForm.allergies = profile.allergies || '';
          this.dynamicForm.bloodType = profile.bloodType || '';
          if (profile.region) {
            this.form.region = profile.region;
          }
        } else {
          this.dynamicForm = { symptoms: '', allergies: '', bloodType: '' };
        }
        this.open = true;
        this.title = "修改患者";
      });
    },
    /** 提交按钮 */
    submitForm() {
      this.$refs["form"].validate(valid => {
        if (valid) {
          if (!this.form.region || this.form.region.length === 0) {
            this.$modal.msgError("请选择省/市/区");
            return;
          }

          // 组装 dynamicForm 到 dynamicProfile 中
          const { symptoms, allergies, bloodType } = this.dynamicForm;
          
          this.form.dynamicProfile = {
            symptoms: symptoms || '',
            allergies: allergies || [],
            bloodType: bloodType || '',
            region: this.form.region
          };

          if (this.form.patientId != null) {
            updatePatient(this.form).then(response => {
              this.$modal.msgSuccess("修改成功");
              this.open = false;
              this.getList();
            });
          } else {
            addPatient(this.form).then(response => {
              this.$modal.msgSuccess("新增成功");
              this.open = false;
              this.getList();
            });
          }
        }
      });
    },
    /** 删除按钮操作 */
    handleDelete(row) {
      const patientIds = row.patientId || this.ids;
      this.$modal.confirm('是否确认删除患者编号为"' + patientIds + '"的数据项？').then(function() {
        return delPatient(patientIds);
      }).then(() => {
        this.getList();
        this.$modal.msgSuccess("删除成功");
      }).catch(() => {});
    },
    /** 查看就诊历史时间线 */
    handleTimeline(row) {
      this.timelineTitle = (row.patientName || '患者') + '  就诊历史时间线';
      this.timelineList = [];
      this.timelineLoading = true;
      this.timelineOpen = true;
      getConsultationTimeline(row.patientId).then(response => {
        this.timelineList = response.data || [];
      }).catch(() => {
        this.$modal.msgError('加载就诊历史失败');
      }).finally(() => {
        this.timelineLoading = false;
      });
    }
  }
};
</script>



