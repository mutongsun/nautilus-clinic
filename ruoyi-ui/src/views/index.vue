<template>
  <div class="app-container home">
    <el-row :gutter="20" class="home-header">
      <el-col :span="24">
        <h2 class="home-title">Nautilus Clinic Management System</h2>
        <p class="home-subtitle">
          门诊业务、药品库存、处方开立与基础运营管理
        </p>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="home-cards">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover" class="module-card">
          <div slot="header"><span>门诊接诊</span></div>
          <p class="module-desc">患者登记、挂号与接诊相关功能入口。</p>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover" class="module-card">
          <div slot="header"><span>药品与库存</span></div>
          <p class="module-desc">药品目录、批次效期与库存管理。</p>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover" class="module-card">
          <div slot="header"><span>处方与收费</span></div>
          <p class="module-desc">处方开立、费用项与结算相关流程。</p>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover" class="module-card">
          <div slot="header"><span>系统与权限</span></div>
          <p class="module-desc">用户、角色、菜单与系统参数配置。</p>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="home-meta">
      <el-col :span="24">
        <p class="version-line">
          <b>系统版本</b> v{{ version }}
        </p>
      </el-col>
    </el-row>
  </div>
</template>

<script>
export default {
  name: "Index",
  data() {
    return {
      version: "1.0.0"
    }
  }
}
</script>

<style scoped lang="scss">
.home {
  font-size: 14px;
  color: #606266;

  .home-title {
    margin: 0 0 8px;
    font-size: 22px;
    font-weight: 600;
    color: #303133;
  }

  .home-subtitle {
    margin: 0;
    color: #909399;
    line-height: 1.6;
  }

  .home-header {
    margin-bottom: 24px;
  }

  .home-cards {
    margin-bottom: 8px;
  }

  .module-card {
    margin-bottom: 16px;

    .module-desc {
      margin: 0;
      min-height: 48px;
      line-height: 1.6;
    }
  }

  .version-line {
    margin-top: 8px;
    color: #909399;
    font-size: 13px;
  }
}
</style>
