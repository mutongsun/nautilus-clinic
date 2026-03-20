# 🐚 Nautilus Clinic — 海螺诊所管理系统

<p align="center">
  <img src="https://img.shields.io/badge/SpringBoot-3.x-brightgreen?style=flat-square&logo=springboot" />
  <img src="https://img.shields.io/badge/PostgreSQL-JSONB-blue?style=flat-square&logo=postgresql" />
  <img src="https://img.shields.io/badge/MyBatis--Plus-3.5%2B-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" />
</p>

> 基于 **RuoYi-SpringBoot3-Pro** 二次开发的私立诊所信息管理系统，核心亮点是利用 **PostgreSQL JSONB** 实现患者动态档案与处方的灵活存储和高效检索。

---

## 📑 目录

- [项目概述](#-项目概述)
- [技术栈](#-技术栈)
- [系统功能](#-系统功能)
- [JSONB 检索专项介绍 ⭐](#-jsonb-检索专项介绍-)
- [快速开始](#-快速开始)
- [Git 上传步骤](#-git-上传步骤)
- [项目结构](#-项目结构)
- [API 文档](#-api-文档)

---

## 🏥 项目概述

**Nautilus Clinic** 是一套面向小型私立诊所的全流程信息化管理系统，涵盖患者建档、问诊记录、处方开具、药品库存四大核心业务，并集成了 AI 辅助问诊、NLP 处方解析、RAG 知识检索等智能能力。

系统在数据层面做出了关键设计取舍：将患者的**动态体征、自定义标签、过敏史**等非结构化信息存储为 PostgreSQL **JSONB** 字段，同时将**处方明细**序列化为 JSONB 数组，从而避免了繁琐的宽表设计，并充分利用 PostgreSQL 原生 JSONB 函数实现毫秒级深度检索。

---

## 🛠 技术栈

| 层次 | 技术 | 版本 |
|---|---|---|
| 后端框架 | Spring Boot | 3.x |
| ORM | MyBatis-Plus | 3.5+ |
| 数据库 | **PostgreSQL**（JSONB 核心） | 12+ |
| 缓存 | Redis（可选） | — |
| 权限 | Spring Security + JWT | 6.x |
| 低代码 | Magic API | 2.2.2 |
| 定时任务 | Quartz | 2.5.2 |
| 前端 | Vue 3 + Element Plus | — |
| 构建 | Maven | 3.6+ |

---

## 🩺 系统功能

### 1. 患者档案管理

- **基础信息**：姓名、性别、出生日期、年龄、科别、联系方式
- **动态档案（JSONB）**：血型、过敏史、自定义标签、历次体征记录（血压、心率等）
- 支持按姓名模糊检索、按 JSONB 字段深度检索（见下方专项介绍）

### 2. 就诊记录管理

- 关联患者→问诊单→处方的完整就诊链
- 主诉、诊断结果自由文本录入
- **处方明细以 JSONB 数组存储**，每条记录包含药品名、规格、数量、用法等结构化字段
- 就诊单状态流转：`已开具 → 已发药`
- 支持 NLP 自然语言处方解析（`你好，开阿莫西林两盒` → 自动结构化）

### 3. 药品库存管理

- 药品基本信息（名称、规格、单位、库存量、进价/售价）
- **扩展属性（JSONB）**：存储不同药品的特有属性，例如冷藏标记、批号、效期等
- 自动库存扣减：发药时触发库存核减

### 4. AI 与 RAG 能力

- **NLP 处方解析**：使用正则 + 语义规则将自然语言转成结构化处方对象
- **RAG 知识检索**：基于 pgvector + Spring AI，支持向量相似度搜索临床知识库
- OpenAI 兼容接口，支持国内大模型（自定义 base-url）

### 5. 系统能力（继承自 RuoYi-Pro）

| 功能 | 说明 |
|---|---|
| 用户/角色/权限 | RBAC 三级权限体系 |
| 操作日志 | 全链路审计日志 |
| 代码生成 | MyBatis-Plus 适配模板 |
| 三级等保 | 密码周期、失败锁定、IP 黑名单 |
| 多数据库 | MySQL / PostgreSQL / 达梦 / 瀚高 / 高斯 |

---

## 🔍 JSONB 检索专项介绍 ⭐

这是本项目最具技术亮点的模块。相比传统的关系型扩展表，JSONB 方案让**动态、不规则的医疗数据**无需改表结构即可灵活扩展，同时借助 PostgreSQL 原生函数实现高性能检索。

### 数据模型设计

#### 患者动态档案 `dynamic_profile`

```sql
-- 患者表核心字段
CREATE TABLE nautilus_patient (
    patient_id   BIGINT PRIMARY KEY,
    patient_name VARCHAR(64),
    gender       CHAR(1),
    birth_date   DATE,
    -- 动态档案，所有非结构化字段存入此列
    dynamic_profile JSONB
);
```

**`dynamic_profile` 示例数据：**

```json
{
  "bloodType":  "A+",
  "tags":       ["Yorushika铁粉", "高血压", "长期随访"],
  "allergies":  ["青霉素", "春泥", "花粉"],
  "vitals": [
    { "date": "2025-12-01", "bp": "120/80", "hr": 72 },
    { "date": "2026-01-15", "bp": "135/88", "hr": 78 }
  ]
}
```

#### 处方明细 `prescription_payload`

```sql
-- 就诊记录表
CREATE TABLE nautilus_consultation (
    consultation_id    BIGINT PRIMARY KEY,
    patient_id         BIGINT,
    chief_complaint    TEXT,
    diagnosis          TEXT,
    status             CHAR(1),
    -- 处方明细列表，避免宽表设计
    prescription_payload JSONB
);
```

**`prescription_payload` 示例数据：**

```json
[
  {
    "medicineName": "阿莫西林胶囊",
    "spec":         "0.5g×24粒",
    "quantity":     2,
    "unit":         "盒",
    "dosage":       "每日三次，每次两粒",
    "unitPrice":    8.50
  },
  {
    "medicineName": "布洛芬缓释胶囊",
    "spec":         "0.3g×20粒",
    "quantity":     1,
    "unit":         "盒",
    "dosage":       "每日两次，每次一粒",
    "unitPrice":    12.00
  }
]
```

---

### JSONB 检索实现

#### Java 实体映射

通过 MyBatis-Plus 的 `JacksonTypeHandler` 实现 JSONB ↔ Java 对象的自动双向序列化：

```java
@TableName(value = "ruoyi.nautilus_patient", autoResultMap = true)
public class NautilusPatient extends BaseEntity {

    // 动态档案：自动序列化/反序列化为 Map<String, Object>
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> dynamicProfile;
}

@TableName(value = "ruoyi.nautilus_consultation", autoResultMap = true)
public class NautilusConsultation extends BaseEntity {

    // 处方明细：自动序列化/反序列化为 List<Map<String, Object>>
    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<Map<String, Object>> prescriptionPayload;
}
```

#### 核心检索逻辑

使用 `jsonb_exists()` PostgreSQL 原生函数，可以直接检索 JSONB 数组内的成员，无需 `LIKE` 或全表扫描：

```java
@Override
public List<NautilusPatient> advancedSearch(String tag, String allergy) {
    LambdaQueryWrapper<NautilusPatient> wrapper = new LambdaQueryWrapper<>();

    if (StringUtils.isNotEmpty(tag)) {
        // 检索 tags 数组中是否包含指定标签
        // 使用 {0} 占位符而非 ? 避免与 JDBC 占位符冲突
        wrapper.apply("jsonb_exists(dynamic_profile->'tags', {0})", tag);
    }

    if (StringUtils.isNotEmpty(allergy)) {
        // 检索 allergies 数组中是否包含指定过敏源
        wrapper.apply("jsonb_exists(dynamic_profile->'allergies', {0})", allergy);
    }

    return this.list(wrapper);
}
```

**生成的 SQL（以标签检索为例）：**

```sql
SELECT *
FROM ruoyi.nautilus_patient
WHERE jsonb_exists(dynamic_profile->'tags', 'Yorushika铁粉')
  AND jsonb_exists(dynamic_profile->'allergies', '青霉素');
```

#### API 接口

```http
GET /clinic/patient/advanced-search?tag=Yorushika铁粉&allergy=青霉素
Authorization: Bearer <token>
```

**响应示例：**

```json
{
  "code": 200,
  "msg": "查询成功",
  "rows": [
    {
      "patientId": "1763820471234560001",
      "patientName": "Amy",
      "gender": "F",
      "dynamicProfile": {
        "bloodType": "A+",
        "tags": ["Yorushika铁粉", "高血压"],
        "allergies": ["青霉素", "春泥"]
      }
    }
  ],
  "total": 1
}
```

#### 为什么使用 `jsonb_exists` 而非 `@>` 操作符？

| 方案 | SQL 示例 | 问题 |
|---|---|---|
| `@>` 包含操作符 | `dynamic_profile->'tags' @> '["Yorushika铁粉"]'` | 需要 JDBC `?` 占位符，与 MyBatis-Plus `wrapper.apply()` 的 `?` 冲突 |
| `jsonb_exists()` ✅ | `jsonb_exists(dynamic_profile->'tags', ?)` | 支持 MyBatis-Plus `{0}` 占位符，安全规避冲突 |

> **结论**：使用 `jsonb_exists(col->'key', {0})` 配合 MyBatis-Plus `wrapper.apply()` 是在 ORM 层安全使用 JSONB 检索的最佳实践。

#### 性能优化建议

如需在大数据量下保持高性能，可对 `dynamic_profile` 添加 GIN 索引：

```sql
-- 为 dynamic_profile 整列创建 GIN 索引（支持所有 key 的检索）
CREATE INDEX idx_patient_dynamic_profile
    ON ruoyi.nautilus_patient
    USING GIN (dynamic_profile jsonb_path_ops);

-- 仅对 tags 数组建立 GIN 索引（更精细）
CREATE INDEX idx_patient_tags
    ON ruoyi.nautilus_patient
    USING GIN ((dynamic_profile->'tags'));
```

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 |
|---|---|
| JDK | 17 或 21 |
| PostgreSQL | 12+（必须，需支持 JSONB） |
| Redis | 可选 |
| Maven | 3.6+ |
| Node.js | 16+（前端） |

### 1. 克隆项目

```bash
git clone https://github.com/Yorushikamimimi/nautilus-clinic.git
cd nautilus-clinic
```

### 2. 初始化数据库

```bash
# 创建数据库
psql -U postgres -c "CREATE DATABASE nautilus_clinic;"

# 导入系统基础表（RuoYi 系统表）
psql -U postgres -d nautilus_clinic < sql/ruoyi-pgsql.sql
psql -U postgres -d nautilus_clinic < sql/magic-api-pgsql.sql

# 导入诊所业务表（patients, consultations, inventory 等）
psql -U postgres -d nautilus_clinic < sql/clinic-pgsql.sql
```

### 3. 修改配置

编辑 `ruoyi-admin/src/main/resources/application.yml`，选择 profile：

```yaml
spring:
  profiles:
    active: devpg   # 使用 PostgreSQL 开发配置
```

编辑 `application-devpg.yml`，填入你的数据库凭据：

```yaml
spring:
  datasource:
    druid:
      master:
        url: jdbc:postgresql://localhost:5432/nautilus_clinic?currentSchema=ruoyi&stringtype=unspecified
        username: YOUR_DB_USERNAME      # 替换为实际用户名
        password: YOUR_DB_PASSWORD      # 替换为实际密码
```

同时修改 `application.yml` 中的 JWT 密钥：

```yaml
token:
  secret: YOUR_JWT_SECRET_HERE    # 替换为随机强密钥（至少32位）
```

### 4. 编译启动后端

```bash
mvn clean package -DskipTests
java -jar ruoyi-admin/target/ruoyi-admin.jar
```

### 5. 启动前端

```bash
cd ruoyi-ui
npm install
npm run dev
```

### 6. 访问系统

| 地址 | 说明 |
|---|---|
| `http://localhost:80` | 前端界面 |
| `http://localhost:8087/doc.html` | Springdoc 接口文档 |
| `http://localhost:8087/magic/web` | Magic API 低代码平台 |

> 首次登录使用系统管理员账号，**请立即修改默认密码**。

---

## 📤 Git 上传步骤

本项目已完成凭据脱敏，可安全上传。按以下步骤操作：

```bash
# 1. 进入项目目录
cd d:\Workspace\nautilus-clinic

# 2. 确认远端仓库（若已设置可跳过）
git remote -v
# 若无输出，执行：
git remote add origin https://github.com/Yorushikamimimi/nautilus-clinic.git

# 3. 确认 .gitignore 已排除 SQL dump
git status   # nautilus_clinic_dump.sql 不应出现在列表中

# 4. 暂存所有变更
git add .

# 5. 提交（附上有意义的说明）
git commit -m "feat: sanitize credentials and add clinic README

- Replace all plaintext passwords with placeholders in 10 yml configs
- Exclude nautilus_clinic_dump.sql from version control
- Add comprehensive clinic-specific README with JSONB section"

# 6. 推送到 GitHub
git push -u origin main
# 如果主分支是 master：git push -u origin master
```

> [!IMPORTANT]
> 执行 `git push` 前，请在 GitHub 仓库页面 **Settings → Branches** 确认默认分支名称（`main` 或 `master`）。

> [!WARNING]
> **强烈建议**：上传后立即在生产服务器上更新所有凭据（DB 密码、JWT Secret 等），因为历史 Git 提交中**可能仍含有旧密码**。如需彻底清除历史密码，请参考 [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)。

---

## 📁 项目结构

```
nautilus-clinic/
├── ruoyi-admin/                    # 启动模块 & 配置文件
│   └── src/main/resources/
│       ├── application.yml         # 主配置（JWT、Magic-API 等）
│       ├── application-devpg.yml   # PostgreSQL 开发配置 ← 修改此处
│       └── application-prodpg.yml  # PostgreSQL 生产配置
├── ruoyi-biz/                      # 诊所核心业务模块 ⭐
│   └── src/main/java/com/ruoyi/
│       └── clinic/
│           ├── controller/         # REST 控制器
│           │   ├── NautilusPatientController.java      # 患者管理 + JSONB 检索
│           │   ├── NautilusConsultationController.java # 就诊记录
│           │   └── NautilusInventoryController.java    # 药品库存
│           ├── domain/             # 实体类（含 JSONB 字段映射）
│           │   ├── NautilusPatient.java      # dynamicProfile JSONB
│           │   ├── NautilusConsultation.java # prescriptionPayload JSONB
│           │   └── NautilusInventory.java    # attributes JSONB
│           ├── service/            # 业务逻辑（含 JSONB 检索实现）
│           │   └── impl/NautilusPatientServiceImpl.java
│           └── util/
│               └── PrescriptionUtils.java   # NLP 处方解析工具
├── ruoyi-framework/                # 框架核心
├── ruoyi-system/                   # 系统管理模块
├── ruoyi-common/                   # 公共工具
├── ruoyi-ui/                       # Vue 3 前端
├── sql/                            # 数据库脚本
│   ├── ruoyi-pgsql.sql             # 系统基础表
│   ├── clinic-pgsql.sql            # 诊所业务表（含 JSONB 列定义）
│   └── magic-api-pgsql.sql         # Magic API 脚本
└── README.md
```

---

## 📖 API 文档

启动后访问 `http://localhost:8087/doc.html`，主要接口如下：

| 接口 | 方法 | 说明 |
|---|---|---|
| `/clinic/patient/list` | GET | 患者列表（支持姓名模糊查询） |
| `/clinic/patient/{id}` | GET | 患者详情（含 dynamicProfile JSONB） |
| `/clinic/patient/advanced-search` | GET | **JSONB 深度检索**（标签 + 过敏源） |
| `/clinic/patient` | POST | 新增患者 |
| `/clinic/consultation/list` | GET | 就诊记录列表 |
| `/clinic/consultation/quick` | POST | 快速问诊（一次性创建患者+就诊记录） |
| `/clinic/inventory/list` | GET | 药品库存列表 |

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。业务系统在 [若依 RuoYi](https://gitee.com/y_project/RuoYi-Vue) 开源生态基础上二次开发，遵循相应开源协议。
