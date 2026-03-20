<template>
  <div class="app-container">
    <!-- 🚨 库存预警面板 -->
    <el-row :gutter="16" v-if="alertData.lowStock.length > 0 || alertData.expiringSoon.length > 0" style="margin-bottom: 16px;">
      <el-col :span="12" v-if="alertData.lowStock.length > 0">
        <el-card shadow="hover" style="border-left: 4px solid #f56c6c; border-radius: 8px;">
          <div slot="header" style="display: flex; align-items: center; justify-content: space-between;">
            <span style="font-weight: bold; color: #f56c6c;">
              <i class="el-icon-warning"></i> 低库存预警
            </span>
            <el-badge :value="alertData.lowStock.length" type="danger" />
          </div>
          <div v-for="item in alertData.lowStock" :key="'low-'+item.itemCode" style="margin-bottom: 8px;">
            <el-tag type="danger" size="small" effect="plain" style="margin-right: 6px;">
              {{ item.itemCode }}
            </el-tag>
            <span style="font-weight: 500;">{{ item.itemName }}</span>
            <span style="float: right; color: #f56c6c; font-weight: bold;">
              仅剩 {{ item.currentStock }} / 阈值 {{ item.alertThreshold }}
            </span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12" v-if="alertData.expiringSoon.length > 0">
        <el-card shadow="hover" style="border-left: 4px solid #e6a23c; border-radius: 8px;">
          <div slot="header" style="display: flex; align-items: center; justify-content: space-between;">
            <span style="font-weight: bold; color: #e6a23c;">
              <i class="el-icon-date"></i> 近效期 / 已过期预警
            </span>
            <el-badge :value="alertData.expiringSoon.length" type="warning" />
          </div>
          <div v-for="item in alertData.expiringSoon" :key="'exp-'+item.itemCode" style="margin-bottom: 8px;">
            <el-tag :type="isExpired(item.expiryDate) ? 'danger' : 'warning'" size="small" effect="plain" style="margin-right: 6px;">
              {{ isExpired(item.expiryDate) ? '已过期' : daysUntilExpiry(item.expiryDate) + '天后' }}
            </el-tag>
            <span style="font-weight: 500;">{{ item.itemName }}</span>
            <span style="float: right; color: #909399; font-size: 13px;">
              {{ parseTime(item.expiryDate, '{y}-{m}-{d}') }}
              <template v-if="item.batchNo"> | 批次 {{ item.batchNo }}</template>
            </span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-bottom: 20px; border-radius: 8px; border: none;">
      <el-form :model="queryParams" ref="queryForm" size="small" :inline="true" v-show="showSearch" label-width="68px">
        <el-form-item label="药品编码" prop="itemCode">
          <el-input
            v-model="queryParams.itemCode"
            placeholder="请输入药品编码"
            clearable
            @keyup.enter.native="handleQuery"
          />
        </el-form-item>
        <el-form-item label="药品名称" prop="itemName">
          <el-input
            v-model="queryParams.itemName"
            placeholder="请输入药品名称"
            clearable
            @keyup.enter.native="handleQuery"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="el-icon-search" size="mini" @click="handleQuery">搜索</el-button>
          <el-button icon="el-icon-refresh" size="mini" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" style="border-radius: 8px; border: none;">
      <el-row :gutter="10" class="mb8">
        <el-col :span="1.5">
          <el-button
            type="primary"
            plain
            icon="el-icon-plus"
            size="mini"
            @click="handleAdd"
            v-hasPermi="['clinic:inventory:add']"
          >新增药品库</el-button>
        </el-col>
        <right-toolbar :showSearch.sync="showSearch" @queryTable="getList"></right-toolbar>
      </el-row>

      <el-table v-loading="loading" :data="inventoryList" @selection-change="handleSelectionChange" style="width: 100%">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="药品编码" align="center" prop="itemCode" />
        <el-table-column label="药品名称" align="center" prop="itemName" min-width="150" show-overflow-tooltip />
        <el-table-column label="当前库存" align="center" prop="currentStock" width="150">
          <template slot-scope="scope">
            <el-tag
              v-if="scope.row.currentStock <= scope.row.alertThreshold"
              type="danger"
              effect="dark"
              size="medium"
              style="padding: 0 10px; border-radius: 4px;"
            >
              <i class="el-icon-warning"></i> 仅剩 {{ scope.row.currentStock }} (告警)
            </el-tag>
            <el-tag
              v-else
              type="success"
              plain
              size="medium"
              style="padding: 0 10px; border-radius: 4px;"
            >
              <i class="el-icon-circle-check"></i> 充足 {{ scope.row.currentStock }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预警阈值" align="center" prop="alertThreshold" width="100" />
        <el-table-column label="单价(元)" align="center" prop="price" width="100">
          <template slot-scope="scope">
            <span style="font-weight: bold; color: #ff9900;">¥ {{ scope.row.price }}</span>
          </template>
        </el-table-column>
        <el-table-column label="批次号" align="center" prop="batchNo" width="130" show-overflow-tooltip />
        <el-table-column label="有效期至" align="center" prop="expiryDate" width="130">
          <template slot-scope="scope">
            <template v-if="scope.row.expiryDate">
              <el-tag
                v-if="isExpired(scope.row.expiryDate)"
                type="danger"
                effect="dark"
                size="small"
              >
                <i class="el-icon-warning"></i> 已过期 {{ parseTime(scope.row.expiryDate, '{y}-{m}-{d}') }}
              </el-tag>
              <el-tag
                v-else-if="isExpiringSoon(scope.row.expiryDate)"
                type="warning"
                size="small"
              >
                ⚠️ {{ daysUntilExpiry(scope.row.expiryDate) }}天后过期
              </el-tag>
              <span v-else style="color: #67c23a;">{{ parseTime(scope.row.expiryDate, '{y}-{m}-{d}') }}</span>
            </template>
            <span v-else style="color: #c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="150">
          <template slot-scope="scope">
            <el-button
              size="mini"
              type="text"
              icon="el-icon-edit"
              @click="handleUpdate(scope.row)"
              v-hasPermi="['clinic:inventory:edit']"
            >修改</el-button>
            <el-button
              size="mini"
              type="text"
              icon="el-icon-delete"
              style="color: #f56c6c;"
              @click="handleDelete(scope.row)"
              v-hasPermi="['clinic:inventory:remove']"
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

    <!-- 添加或修改库存盘点对话框 -->
    <el-dialog :title="title" :visible.sync="open" width="500px" append-to-body :close-on-click-modal="false" custom-class="nautilus-dialog">
      <el-form ref="form" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="药品编码" prop="itemCode">
          <el-select 
            v-model="form.itemCode" 
            filterable 
            allow-create
            default-first-option
            placeholder="请选择或输入新药品编码" 
            :disabled="form.itemId !== undefined && form.itemId !== null"
            @change="handleItemCodeChange"
            style="width: 100%;"
          >
            <el-option
              v-for="item in inventoryList"
              :key="item.itemCode"
              :label="item.itemCode"
              :value="item.itemCode"
            ></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="药品名称" prop="itemName">
          <el-select 
            v-model="form.itemName" 
            filterable 
            allow-create
            default-first-option
            placeholder="请选择或输入新药品名称"
            @change="handleItemNameChange"
            style="width: 100%;"
          >
            <el-option
              v-for="item in inventoryList"
              :key="'name-' + item.itemCode"
              :label="item.itemName"
              :value="item.itemName"
            ></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="当前库存" v-if="isRestockMode">
          <span style="font-weight: bold; font-size: 16px; color: #409EFF; margin-right: 15px;">{{ originalStock }}</span>
          <el-input-number v-model="form.currentStock" :min="1" placeholder="填入新增数字" style="width: 150px;" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">(新增入库数)</span>
        </el-form-item>
        <el-form-item label="当前库存" prop="currentStock" v-else>
          <el-input-number v-model="form.currentStock" :min="0" placeholder="请输入库存数量" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="预警阈值" prop="alertThreshold" v-if="!isRestockMode">
          <el-input-number v-model="form.alertThreshold" :min="1" placeholder="库存低于此值将触发红色告警" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="单价(元)" prop="price" v-if="!isRestockMode">
          <el-input-number v-model="form.price" :min="0.01" :precision="2" :step="0.1" placeholder="请输入单价" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="批次/备注" prop="remark">
          <el-input v-model="form.remark" placeholder="非必填，可输入进货备注信息" />
        </el-form-item>
        <el-row :gutter="10">
          <el-col :span="12">
            <el-form-item label="批次号" prop="batchNo">
              <el-input v-model="form.batchNo" placeholder="如 20260201A" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="有效期至" prop="expiryDate">
              <el-date-picker
                v-model="form.expiryDate"
                type="date"
                value-format="yyyy-MM-dd"
                placeholder="请选择有效期"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <div slot="footer" class="dialog-footer">
        <el-button type="primary" @click="submitForm">确 定</el-button>
        <el-button @click="cancel">取 消</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { listInventory, getInventory, delInventory, addInventory, updateInventory, getInventoryAlerts } from "@/api/clinic/inventory";

export default {
  name: "Inventory",
  data() {
    return {
      // 遮罩层
      loading: false,
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
      // 库存数据表格
      inventoryList: [],
      // 预警数据
      alertData: {
        lowStock: [],
        expiringSoon: []
      },
      // 弹出层标题
      title: "",
      // 是否显示弹出层
      open: false,
      // 查询参数
      queryParams: {
        pageNum: 1,
        pageSize: 10,
        itemCode: null,
        itemName: null,
      },
      // 表单参数
      form: {},
      // 表单校验
      rules: {
        itemCode: [
          { required: true, message: "药品编码不能为空", trigger: "blur" }
        ],
        itemName: [
          { required: true, message: "药品名称不能为空", trigger: "blur" }
        ],
        currentStock: [
          { required: true, message: "库存数量不能为空", trigger: "blur" }
        ],
        price: [
          { required: true, message: "单价不能为空", trigger: "blur" }
        ]
      }
    };
  },
  computed: {
    isRestockMode() {
      // 如果是编辑模式（有主键），则不是补货模式
      if (this.form.itemId !== undefined && this.form.itemId !== null) return false;
      if (!this.form.itemCode) return false;
      return this.inventoryList.some(item => item.itemCode === this.form.itemCode);
    },
    originalStock() {
      if (!this.isRestockMode) return 0;
      const item = this.inventoryList.find(i => i.itemCode === this.form.itemCode);
      return item ? item.currentStock : 0;
    }
  },
  created() {
    this.getList();
    this.loadAlerts();
  },
  activated() {
    this.getList();
    this.loadAlerts();
  },
  methods: {
    /** 查询库存列表 */
    getList() {
      this.loading = true;
      listInventory(this.queryParams).then(response => {
        this.inventoryList = response.rows;
        this.total = response.total;
        this.loading = false;
      });
    },
    /** 加载预警数据 */
    loadAlerts() {
      getInventoryAlerts().then(response => {
        this.alertData = response.data || { lowStock: [], expiringSoon: [] };
      }).catch(() => {});
    },
    // 取消按钮
    cancel() {
      this.open = false;
      this.reset();
    },
    // 表单重置
    reset() {
      this.form = {
        itemId: null,
        itemCode: null,
        itemName: null,
        currentStock: 0,
        alertThreshold: 10,
        price: null,
        batchNo: null,
        expiryDate: null,
        remark: null
      };
      this.resetForm("form");
    },
    /** 搜索按钮操作 */
    handleQuery() {
      this.queryParams.pageNum = 1;
      this.getList();
    },
    /** 重置按钮操作 */
    resetQuery() {
      this.resetForm("queryForm");
      this.handleQuery();
    },
    // 多选框选中数据
    handleSelectionChange(selection) {
      this.ids = selection.map(item => item.itemId)  // ✅ 使用正确的主键字段 itemId
      this.single = selection.length!==1
      this.multiple = !selection.length
    },
    /** 新增按钮操作 */
    handleAdd() {
      this.reset();
      this.open = true;
      this.title = "新增库存";
    },
    /** 修改按钮操作 */
    handleUpdate(row) {
      this.reset();
      const itemId = row.itemId || this.ids  // ✅ 使用 itemId
      // 直接用行数据回显（包含完整的 itemId）
      if (row.itemId) {
        this.form = Object.assign({}, row);
        this.open = true;
        this.title = "修改库存";
      } else {
        getInventory(itemId).then(response => {
          this.form = response.data;
          this.open = true;
          this.title = "修改库存";
        });
      }
    },
    /** 提交按钮 */
    submitForm() {
      this.$refs["form"].validate(valid => {
        if (valid) {
          if (this.form.itemId != null) {
            // ✅ 编辑模式：有 itemId，调用 PUT /clinic/inventory
            updateInventory(this.form).then(response => {
              this.$modal.msgSuccess("修改成功");
              this.open = false;
              this.getList();
            });
          } else {
            // ✅ 新增/补货模式：无 itemId，调用 POST /clinic/inventory -> upsertInventory()
            addInventory(this.form).then(response => {
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
      const itemIds = row.itemId || this.ids;  // ✅ 使用 itemId
      this.$modal.confirm('是否确认删除库存编号为"' + itemIds + '"的数据项？').then(function() {
        return delInventory(itemIds);
      }).then(() => {
        this.getList();
        this.$modal.msgSuccess("删除成功");
      }).catch(() => {});
    },
    /** 药品编码联动选择 */
    handleItemCodeChange(selectedCode) {
      if (!selectedCode) return;
      const selectedItem = this.inventoryList.find(item => item.itemCode === selectedCode);
      if (selectedItem) {
        this.form.itemName = selectedItem.itemName;
        if (this.form.itemId == null) {  // ✅ 使用 itemId
          // 仅补货
          this.form.currentStock = 1; 
        } else {
          // 修改原有记录
          this.form.price = selectedItem.price;
          this.form.alertThreshold = selectedItem.alertThreshold;
        }
      }
    },
    /** 药品名称联动选择 */
    handleItemNameChange(selectedName) {
      if (!selectedName) return;
      const selectedItem = this.inventoryList.find(item => item.itemName === selectedName);
      if (selectedItem) {
        if (this.form.itemId === undefined || this.form.itemId === null) {
          this.form.itemCode = selectedItem.itemCode;
          this.form.currentStock = 1;
        } else {
          this.form.price = selectedItem.price;
          this.form.alertThreshold = selectedItem.alertThreshold;
        }
      }
    },
    /** 判断是否已过期 */
    isExpired(dateStr) {
      if (!dateStr) return false;
      return new Date(dateStr) < new Date();
    },
    /** 判断是否 30 天内即将过期 */
    isExpiringSoon(dateStr) {
      if (!dateStr) return false;
      const diff = new Date(dateStr) - new Date();
      return diff > 0 && diff <= 30 * 24 * 60 * 60 * 1000;
    },
    /** 计算剩余天数 */
    daysUntilExpiry(dateStr) {
      if (!dateStr) return 0;
      return Math.ceil((new Date(dateStr) - new Date()) / (24 * 60 * 60 * 1000));
    }
  }
};
</script>

<style scoped>
/* 可选：定制一些优雅的弹窗视觉优化 */
::v-deep .nautilus-dialog {
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}
::v-deep .nautilus-dialog .el-dialog__header {
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 15px;
}
</style>
