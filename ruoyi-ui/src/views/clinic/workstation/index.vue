<template>
  <div class="app-container">
    <el-row :gutter="20">
      <!-- 左部分：患者信息区 -->
      <el-col :span="12">
        <el-card shadow="never" style="height: 100%;">
          <div slot="header" class="clearfix">
            <span><i class="el-icon-user"></i> 患者基础档案</span>
            <el-button style="float: right; padding: 3px 0" type="text" @click="resetPatient">重置换人</el-button>
          </div>
          <el-form ref="patientForm" :model="workstationForm" :rules="rules" label-width="80px" @submit.native.prevent>
            <el-form-item label="姓名" prop="patientName">
              <el-autocomplete
                v-model="workstationForm.patientName"
                :fetch-suggestions="queryPatientSearch"
                placeholder="搜索库中姓名或直接输入新患者"
                @select="handlePatientSelect"
                style="width: 100%"
              >
                <template slot="append">
                  <el-button icon="el-icon-search"></el-button>
                </template>
                <template slot-scope="{ item }">
                  <span style="font-weight: bold">{{ item.patientName }}</span>
                  <span style="font-size: 13px; color: #999; margin-left:10px">{{ item.phoneNumber || '无手机号' }}</span>
                </template>
              </el-autocomplete>
            </el-form-item>
            <el-row>
              <el-col :span="12">
                <el-form-item label="性别" prop="gender">
                  <el-radio-group v-model="workstationForm.gender">
                    <el-radio label="1">男</el-radio>
                    <el-radio label="2">女</el-radio>
                    <el-radio label="0">未知</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="年龄" prop="age">
                  <el-input-number v-model="workstationForm.age" :min="0" :max="150" controls-position="right" style="width: 100%"></el-input-number>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="手机号" prop="phoneNumber">
              <el-input v-model="workstationForm.phoneNumber" placeholder="请输入患者手机号" @keyup.enter.native="submitWorkstation" />
            </el-form-item>
            <el-form-item label="联系地址" required>
              <div style="display: flex; gap: 10px;">
                <div style="flex: 2;">
                  <el-cascader
                    v-model="workstationForm.region"
                    :options="regionOptions"
                    placeholder="请选择省市区"
                    style="width: 100%"
                    clearable
                  ></el-cascader>
                </div>
                <div style="flex: 3;">
                  <el-form-item prop="address" style="margin-bottom: 0;">
                    <el-input v-model="workstationForm.address" placeholder="请输入详细地址" @keyup.enter.native="submitWorkstation" />
                  </el-form-item>
                </div>
              </div>
            </el-form-item>
            <el-form-item label="过敏史" prop="allergyHistory">
              <el-input v-model="workstationForm.allergyHistory" type="textarea" placeholder="例如：青霉素（没有请留空）" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右部分：接诊开方区 -->
      <el-col :span="12">
        <el-card shadow="never" style="height: 100%;">
          <div slot="header" class="clearfix">
            <span><i class="el-icon-document"></i> 本次就诊与开方</span>
          </div>
          <el-form ref="consultationForm" :model="workstationForm" :rules="rules" label-width="80px" @submit.native.prevent>
            <el-form-item label="临床诊断" prop="diagnosis">
              <el-input v-model="workstationForm.diagnosis" type="textarea" :rows="2" placeholder="请输入本次就诊的临床诊断记录" />
            </el-form-item>
            
            <el-form-item label="处方明细">
              <!-- 手动添加区域 -->
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
                        <span style="float: right; color: #8492a6; font-size: 13px">余量: {{ med.currentStock }}</span>
                      </el-option>
                    </el-select>
                  </el-col>
                  <el-col :span="5">
                    <el-input-number v-model="item.quantity" :min="1" placeholder="数量" style="width: 100%;" controls-position="right" />
                  </el-col>
                  <el-col :span="8">
                    <el-input v-model="item.dosage" placeholder="用法与用量 (如:每日三次)" @keyup.enter.native="submitWorkstation" />
                  </el-col>
                  <el-col :span="2" style="text-align: center;">
                    <el-button type="danger" icon="el-icon-delete" circle size="mini" @click="removePrescriptionItem(index)"></el-button>
                  </el-col>
                </el-row>
              </div>
              <el-button plain icon="el-icon-plus" size="small" @click="addPrescriptionItem" style="width: 100%; border-style: dashed; margin-bottom: 15px;">通过传统列表手动加药</el-button>

              <!-- 自然语言智能开方区域 -->
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
                  placeholder="试试用一句话描述您要开的药 (回车直接解析)..."
                  style="width: 100%"
                  @keyup.enter.native="parseNaturalLanguagePrescription"
                  clearable
                >
                  <template slot="append">
                    <el-button icon="el-icon-s-promotion" type="primary" @click="parseNaturalLanguagePrescription" style="background-color: #1890ff; color: white;">AI 提取药单</el-button>
                  </template>
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
        </el-card>

          <div style="text-align: right; margin-top: 15px;">
            <el-button type="primary" size="medium" @click="submitWorkstation" style="padding: 12px 40px; font-weight: bold; font-size: 16px; width: 100%;">
              <i class="el-icon-check"></i> 保存并完成接诊开方
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 下半部分：药房库存平铺展示区 -->
    <el-row style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="never">
          <div slot="header" class="clearfix">
            <span><i class="el-icon-first-aid-kit"></i> 药房库存速查</span>
            <el-input
              v-model="inventorySearchKeyword"
              placeholder="搜索药品名称以快速过滤..."
              prefix-icon="el-icon-search"
              size="small"
              clearable
              style="width: 250px; float: right; margin-top: -5px;"
              @keyup.enter.native="submitWorkstation"
            ></el-input>
          </div>
          
          <div v-if="filteredInventoryList.length === 0" style="text-align: center; color: #999; padding: 30px;">
            暂无该药品或库存不足
          </div>
          <el-row :gutter="15" v-else>
            <el-col :span="6" v-for="(med, idx) in filteredInventoryList" :key="idx" style="margin-bottom: 10px;">
              <el-card shadow="hover" :body-style="{ padding: '12px' }" style="background-color: #f8f9fa;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span style="font-size: 14px; font-weight: bold; color: #303133;">{{ med.itemName }}</span>
                  <el-tag size="small" :type="med.currentStock > 10 ? 'success' : 'danger'">余: {{ med.currentStock }}</el-tag>
                </div>
                <div style="font-size: 12px; color: #909399; margin-top: 8px;" v-if="med.itemCode">
                  编码: {{ med.itemCode }}
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { listPatient } from "@/api/clinic/patient";
import { listInventory } from "@/api/clinic/inventory";
import { quickConsultation } from "@/api/clinic/consultation";

export default {
  name: "Workstation",
  data() {
    return {
      // 全局提交表单
      workstationForm: {
        patientId: null,
        patientName: undefined,
        gender: "1",
        age: undefined,
        phoneNumber: undefined,
        region: [],
        address: undefined,
        allergyHistory: undefined,
        diagnosis: undefined,
        // (可选)保留这几个占位如果不使用的话
        bloodType: undefined,
        chiefComplaint: undefined
      },
      dynamicPrescription: [],
      // NLP 输入框
      nlpInput: "",
      
      // 数据源
      patientOptions: [],
      inventoryOptions: [],
      
      // 抽屉状态
      inventoryDrawer: false,
      inventorySearchKeyword: "",
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
      
      // 表单验证
      rules: {
        patientName: [{ required: true, message: "患者姓名不能为空", trigger: "blur" }],
        diagnosis: [{ required: true, message: "记录一次简单的就诊诊断", trigger: "blur" }]
      }
    };
  },
  computed: {
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
    this.initData();
  },
  activated() {
    this.initData();
  },
  methods: {
    initData() {
      this.getPatientList();
      this.getInventoryList();
    },
    getPatientList() {
      listPatient({ pageNum: 1, pageSize: 2000 }).then(response => {
        this.patientOptions = response.rows;
      });
    },
    getInventoryList() {
      listInventory({ pageNum: 1, pageSize: 1500 }).then(response => {
        this.inventoryOptions = response.rows;
      });
    },
    // ---- 患者搜索相关 ----
    queryPatientSearch(queryString, cb) {
      let results = this.patientOptions;
      if (queryString) {
        results = results.filter(p => 
          (p.patientName && p.patientName.includes(queryString)) ||
          (p.phoneNumber && p.phoneNumber.includes(queryString))
        );
      }
      // autocomplete要使用 value
      results.forEach(p => p.value = p.patientName);
      cb(results);
    },
    handlePatientSelect(item) {
      // 选中已有患者，填充其他字段
      this.workstationForm.patientId = item.patientId;
      this.workstationForm.gender = item.gender || "1";
      this.workstationForm.age = item.age;
      this.workstationForm.phoneNumber = item.phoneNumber;
      
      // 解析可能被包装在 dynamicProfile 中的附加信息
      if (item.dynamicProfile) {
        this.workstationForm.address = item.dynamicProfile.address || undefined;
        let pAllergies = item.dynamicProfile.allergies;
        this.workstationForm.allergyHistory = Array.isArray(pAllergies) ? pAllergies.join("、") : pAllergies;
      }
      this.$message.success(`已载入复诊患者【${item.patientName}】的病历资料。`);
    },
    resetPatient() {
      this.workstationForm.patientId = null;
      this.workstationForm.patientName = undefined;
      this.workstationForm.gender = "1";
      this.workstationForm.age = undefined;
      this.workstationForm.phoneNumber = undefined;
      this.workstationForm.region = [];
      this.workstationForm.address = undefined;
      this.workstationForm.allergyHistory = undefined;
      this.workstationForm.diagnosis = undefined;
      this.dynamicPrescription = [];
      this.nlpInput = "";
      this.$refs.patientForm && this.$refs.patientForm.resetFields();
    },

    // ---- 处方相关操作 ----
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
    handleMedicineChange(itemCode, index) {
      const selectedMed = this.inventoryOptions.find(med => med.itemCode === itemCode);
      if (selectedMed) {
        this.$set(this.dynamicPrescription[index], 'itemName', selectedMed.itemName);
      }
    },
    // autocomplete 获取联想列表 (药品)
    querySearchInventory(queryString, cb) {
      const allInventory = this.inventoryOptions;
      if (queryString) {
        const results = allInventory.filter(item => 
          item.itemName.toLowerCase().indexOf(queryString.toLowerCase()) > -1 && 
          item.currentStock > 0
        );
        results.forEach(item => item.value = item.itemName);
        cb(results);
      } else {
        cb([]);
      }
    },
    
    // ---- NLP解析（完全复用原处方台逻辑） ----
    parseNaturalLanguagePrescription() {
      const text = this.nlpInput.trim();
      if (!text) return;

      const cnNumberMap = {
        '〇': 0, '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
      };

      let foundDosages = [];
      const dosagePattern = /(?:每[日天]|一[日天])[一二两三四五六七八九十\d]+次|(?:每|一)次[一二两三四五六七八九十\d]+[粒包片支颗瓶剂滴毫升mlg克]+|睡前服?|饭[前后]服?|空腹服?/g;
      let textWithoutDosage = text;
      let dMatch;
      while ((dMatch = dosagePattern.exec(text)) !== null) {
        foundDosages.push({ index: dMatch.index, text: dMatch[0] });
        textWithoutDosage = textWithoutDosage.substring(0, dMatch.index) + "■".repeat(dMatch[0].length) + textWithoutDosage.substring(dMatch.index + dMatch[0].length);
      }

      let foundMeds = [];
      const sortedInventory = [...this.inventoryOptions].sort((a, b) => b.itemName.length - a.itemName.length);
      
      for (const inv of sortedInventory) {
        let searchIdx = 0;
        let idx;
        while ((idx = text.indexOf(inv.itemName, searchIdx)) !== -1) {
          let isCovered = foundMeds.some(m => idx >= m.index && idx < (m.index + m.item.itemName.length));
          if (!isCovered) {
            foundMeds.push({ index: idx, item: inv, quantity: null, dosage: [] });
            textWithoutDosage = textWithoutDosage.substring(0, idx) + "■".repeat(inv.itemName.length) + textWithoutDosage.substring(idx + inv.itemName.length);
          }
          searchIdx = idx + inv.itemName.length;
        }
      }
      
      foundMeds.sort((a, b) => a.index - b.index);

      if (foundMeds.length === 0) {
        this.$message.warning("没找到名字对得上的药品。");
        return;
      }

      let foundQuantities = [];
      const qPattern = /([0-9]+|[一二两三四五六七八九十])\s*(盒|克|粒|支|包|瓶|副|片|颗|袋|剂)/g;
      let m;
      while ((m = qPattern.exec(textWithoutDosage)) !== null) {
        let val = /^[0-9]+$/.test(m[1]) ? parseInt(m[1], 10) : cnNumberMap[m[1]];
        foundQuantities.push({ index: m.index, value: val, matched: false });
      }
      
      const loosePattern = /(?:数量为|拿|开|给|加)\s*([0-9]+|[一二两三四五六七八九十])(?!\s*(?:盒|克|粒|支|包|瓶|副|片|颗|袋|剂))/g;
      while ((m = loosePattern.exec(textWithoutDosage)) !== null) {
        let val = /^[0-9]+$/.test(m[1]) ? parseInt(m[1], 10) : cnNumberMap[m[1]];
        foundQuantities.push({ index: m.index, value: val, matched: false });
      }

      for (let med of foundMeds) {
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
        if (nearestQ && minDistanceQ < 50) {
          nearestQ.matched = true;
          med.quantity = nearestQ.value;
        }
      }

      for (let d of foundDosages) {
         let assignedMed = null;
         let minDistance = Infinity;
         for (let med of foundMeds) {
           let dist = d.index - med.index;
           if (dist > 0 && dist < minDistance) {
             minDistance = dist;
             assignedMed = med;
           }
         }
         if (!assignedMed) {
            assignedMed = foundMeds[0];
         }
         if (assignedMed) {
            assignedMed.dosage.push(d.text);
         }
      }

      let successCount = 0;
      let errorMsgs = [];
      
      for (let med of foundMeds) {
        if (!med.quantity || med.quantity <= 0) {
          errorMsgs.push(`【${med.item.itemName}】缺提取数量。`);
        } else if (med.quantity > med.item.currentStock) {
          errorMsgs.push(`库存不足：【${med.item.itemName}】剩 ${med.item.currentStock}。被拦截。`);
        } else {
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
        this.$message.success(`成功提取 ${successCount} 种药品。`);
        this.nlpInput = ''; 
      }
      if (errorMsgs.length > 0) {
        this.$message.warning(errorMsgs.join(" | "));
      }
    },

    // ---- 最终提交 ----
    submitWorkstation() {
      // 需要让左栏和右栏(实际上是两个form或分属不同部分，这里都包含在 workstationForm 了)
      this.$refs.patientForm.validate(validPatient => {
        if (validPatient) {
          this.$refs.consultationForm.validate(validConsult => {
            if (validConsult) {
              
              const payload = {
                ...this.workstationForm,
                prescriptionItems: this.dynamicPrescription.length > 0 ? this.dynamicPrescription : null
              };
              
              quickConsultation(payload).then(response => {
                this.$modal.msgSuccess("接诊开方双管完成！");
                this.resetPatient();
                // 可以加个跳转到处方台之类的，或者留在本页继续下一个人
                this.initData(); // 刷新下基础数据，防库存失效
              });

            } else {
              this.$message.warning("请完善右侧就诊和处方信息 (带星号)");
            }
          });
        } else {
          this.$message.warning("请完善左侧患者基本信息必填项");
        }
      });
    }
  }
};
</script>

<style scoped>
.app-container {
  padding: 20px;
  background-color: #f1f2f5;
  min-height: calc(100vh - 84px);
}
</style>
