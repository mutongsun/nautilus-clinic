# 项目统一开发规范（团队工程化规范）

> 适用范围：本仓库全部 Python 后端代码（`src/`）、CLI 脚手架（`cli/`）及配套设施。
> 业务底座（`ruoyi-*` 模块，Java）遵循其既有 RuoYi 工程规范，此处不重复约束。
> 本规范为**强制规范**，代码评审（Code Review）按本规范执行，违反红线条款一票否决。

---

## 目录

- [1. 目录规范](#1-目录规范)
- [2. 代码规范](#2-代码规范)
- [3. Git 分支规范](#3-git-分支规范)
- [4. 日志规范](#4-日志规范)
- [5. 评审红线清单](#5-评审红线清单)

---

## 1. 目录规范（严格统一）

企业 Agent 后端统一目录结构，**任何新增模块必须归入对应目录，禁止在根目录散放文件**：

```
src/
├── agent/           # LangGraph 智能体编排（调度/查询/审批/操作等多Agent、状态池、任务分发）
├── mcp_gateway/     # MCP 工具网关、PyCasbin 权限策略、参数校验、审计埋点
├── services/        # 业务系统对接服务（诊所/ERP/中台 API 客户端，统一超时/重试/降级）
├── workflow/        # BPM 审批流程调用（Conductor 流程发起、状态查询、回调处理）
├── common/          # 工具函数、异常定义、常量枚举（禁止放业务逻辑）
├── config/          # 配置文件、配置加载（pydantic-settings，禁止散落硬编码配置）
├── db/              # 数据库模型（SQLModel/SQLAlchemy）、迁移脚本（alembic）
├── api/             # FastAPI 路由（仅做参数声明与响应组装，禁止写业务逻辑）
└── tests/           # 单元测试（目录结构与 src/ 一一镜像）
```

### 1.1 分层职责边界（强制）

| 层 | 允许 | 禁止 |
|---|---|---|
| `api/` | 参数声明、鉴权入口、响应组装 | 业务判断、直接访问数据库 |
| `agent/` | 意图识别、任务编排、状态管理 | **任何业务规则判断**、直接调用业务系统 API |
| `mcp_gateway/` | 权限拦截、参数校验、审计、工具注册 | 业务事务逻辑（下沉业务系统） |
| `services/` | 外部系统 API 封装、超时/重试/降级 | 绕过网关直接暴露给 Agent |
| `workflow/` | BPM 流程编排调用 | 在流程代码里写业务校验 |
| `common/` | 纯工具函数、常量、异常类 | 依赖任何上层模块 |

### 1.2 命名规范

- Python 模块/文件：`snake_case`，如 `purchase_order_client.py`；
- 类名：`PascalCase`，如 `InventoryQueryAgent`；
- 常量：`UPPER_SNAKE_CASE`，如 `TOOL_RISK_LEVEL_HIGH`；
- 每个业务系统对接服务统一以 `系统名 + Client` 命名，如 `ClinicClient`、`ErpClient`。

---

## 2. 代码规范

### 2.1 语言与风格

- Python 严格遵循 **PEP8**（CI 使用 `ruff check` + `ruff format` 强制卡点）；
- 类型注解：所有函数签名必须标注入参与返回类型；
- 所有工具函数、接口必须写**中文文档注释**（docstring），格式如下：

```python
def query_inventory(medicine_name: str, include_expired: bool = False) -> list[InventoryItem]:
    """查询诊所药品实时库存（只读工具）。

    通过 MCP 网关调用诊所系统库存接口，仅返回数据，不产生任何写入。

    Args:
        medicine_name: 药品名称，支持模糊匹配。
        include_expired: 是否包含已过效期批次，默认 False。

    Returns:
        库存明细列表，按效期升序排列。

    Raises:
        ToolPermissionDenied: 当前 Agent 角色无该工具调用权限。
    """
```

### 2.2 分层逻辑红线（一票否决）

- **禁止 Agent 层写业务判断逻辑**，业务校验全部下沉网关/业务系统。Agent 层只负责「调度谁、传什么」，不负责「允不允许、对不对」；
- 判断标准：代码中出现 `if 库存不足`、`if 金额超过` 等业务规则分支且位于 `agent/` 目录，即为违规。

### 2.3 外部请求规范（强制四件套）

所有外部接口请求（业务系统 API、LLM API、BPM API）必须同时具备：

1. **超时**：显式设置 `timeout`，禁止裸调；
2. **重试**：幂等接口配置有限次重试（建议 `tenacity`，指数退避，最多 3 次）；
3. **异常捕获**：捕获并转译为内部异常，禁止裸 `except` 吞异常；
4. **参数校验**：出入口参数使用 pydantic 模型校验。

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5))
async def get_stock(self, medicine_name: str) -> list[InventoryItem]:
    """调用诊所系统库存查询接口（带超时、重试、异常转译）。"""
    try:
        resp = await self._client.get(
            "/clinic/inventory/list",
            params={"medicineName": medicine_name},
            timeout=5.0,  # ① 超时
        )
        resp.raise_for_status()
        return [InventoryItem.model_validate(i) for i in resp.json().get("rows", [])]  # ④ 参数校验
    except httpx.TimeoutException as exc:  # ③ 异常捕获与转译
        raise BizSystemUnavailable("诊所系统库存接口超时") from exc
```

### 2.4 写操作风险等级标注（强制）

所有写操作工具必须标注风险等级，**高风险操作强制走 BPM**。风险等级定义于 `common/constants.py`：

| 等级 | 常量 | 定义 | 处置要求 |
|---|---|---|---|
| 低 | `TOOL_RISK_LOW` | 只读查询，无副作用 | 网关权限校验后直接执行 |
| 中 | `TOOL_RISK_MEDIUM` | 可逆写操作（状态流转、软删除） | 网关校验 + 审计 + 可回滚 |
| 高 | `TOOL_RISK_HIGH` | 不可逆/资金/库存/处方类写入 | **强制 Conductor BPM 人工审批通过后方可执行** |

MCP 工具注册示例：

```python
@mcp_tool(
    name="create_purchase_order",
    risk_level=TOOL_RISK_HIGH,          # 风险等级标注（强制）
    required_roles={"biz-operator"},    # PyCasbin 角色约束（强制）
    bpm_approved=True,                  # 声明必须审批通过后才可执行（高风险强制）
)
async def create_purchase_order(order: PurchaseOrderIn) -> OrderResult:
    """创建药品采购订单（高风险写工具，需 BPM 审批通过后执行）。"""
    ...
```

> 网关在执行前会二次校验 `bpm_approved` 声明与 Conductor 实际审批状态是否一致，防止 Agent 幻觉伪造「已审批」上下文。

---

## 3. Git 分支规范（大厂标准）

### 3.1 分支模型

| 分支 | 用途 | 保护规则 |
|---|---|---|
| `main` | 稳定可运行版本，随时可发布 | **禁止直接提交**，仅接受 `dev` → `main` 的 PR（需 ≥1 人评审 + CI 通过） |
| `dev` | 开发主分支，日常集成 | 禁止 force push，PR 合入需 CI 通过 |
| `feature/xxx` | 新功能分支 | 从 `dev` 切出，完成后合回 `dev` |
| `fix/xxx` | bug 修复分支 | 从 `dev` 切出，完成后合回 `dev`；线上紧急修复从 `main` 切 `hotfix/xxx` |

### 3.2 分支命名示例

```bash
git checkout -b feature/multi-agent-scheduler   # 新功能：多智能体调度
git checkout -b fix/audit-log-missing-trace-id  # 修复：审计日志缺失链路ID
```

### 3.3 提交信息规范（Conventional Commits）

```text
<type>(<scope>): <subject>

<body（可选，说明为什么）>
```

| type | 说明 |
|---|---|
| `feat` | 新功能 |
| `fix` | bug 修复 |
| `refactor` | 重构（不改行为） |
| `perf` | 性能优化 |
| `test` | 测试 |
| `docs` | 文档 |
| `chore` | 构建/工程化 |

示例：`feat(mcp_gateway): 工具执行前强制校验BPM审批状态，防止幻觉伪造已审批上下文`

### 3.4 协作流程

1. 从 `dev` 切出 `feature/` 或 `fix/` 分支开发；
2. 开发自测通过（含单元测试）后提交 PR/MR 至 `dev`；
3. CI 检查（lint + 单测 + 镜像构建）+ 至少 1 人评审通过后合入；
4. 每个迭代节点由 `dev` 合入 `main` 并打 tag（`vX.Y.Z`）。

---

## 4. 日志规范（企业审计级）

### 4.1 工具调用审计（每条必须记录）

**每条工具调用必须记录以下字段**，缺一即为违规（由 MCP 网关统一埋点，业务代码不得绕过）：

| 字段 | 说明 |
|---|---|
| `user_instruction` | 用户原始指令 |
| `agent_id` | 执行调用的智能体 ID（多Agent场景必填） |
| `trace_id` | 任务链路 ID（同一次多Agent协作全程相同） |
| `tool_name` | 工具名 |
| `tool_input` | 工具入参（敏感字段脱敏） |
| `tool_output` | 返回结果（超长截断，敏感字段脱敏） |
| `duration_ms` | 耗时（毫秒） |
| `status` | 结果状态：`SUCCESS` / `PERMISSION_DENIED` / `VALIDATION_FAILED` / `BIZ_ERROR` / `TIMEOUT` |
| `operator_identity` | 操作身份（用户ID + Agent角色） |
| `risk_level` | 工具风险等级 |
| `bpm_workflow_id` | 关联的审批流程 ID（写操作必填） |

审计日志示例（JSON 结构化输出，入库 + 文件双写）：

```json
{
  "ts": "2026-08-23T10:15:32.118+08:00",
  "trace_id": "trace-9f3a2b",
  "user_instruction": "查一下缺货药品，顺便发起采购",
  "agent_id": "agent-biz-query-01",
  "tool_name": "query_inventory",
  "tool_input": {"medicine_name": "阿莫西林胶囊"},
  "tool_output": {"rows": [{"qty": 2, "status": "LOW_STOCK"}], "truncated": false},
  "duration_ms": 143,
  "status": "SUCCESS",
  "operator_identity": {"user_id": "u1024", "agent_role": "biz-query"},
  "risk_level": "LOW",
  "bpm_workflow_id": null
}
```

### 4.2 错误日志（必须输出三要素）

错误日志必须输出：

1. **堆栈信息**（`logger.exception(...)` 或显式携带 `exc_info`）；
2. **请求 ID**（`trace_id`，与审计日志、响应体一致，支持全链路排查）；
3. **上下文信息**（用户ID、Agent ID、工具名、关键入参）。

```python
try:
    result = await clinic_client.create_order(order)
except BizSystemUnavailable:
    logger.exception(
        "创建采购订单失败: 工具=create_purchase_order trace_id=%s user_id=%s order_no=%s",
        ctx.trace_id, ctx.user_id, order.order_no,
    )
    raise
```

### 4.3 其他约定

- 日志统一 JSON 结构化输出，禁止裸 `print`；
- 敏感信息（密码、Token、API Key、患者身份证号）入库前必须脱敏；
- 审计日志保留期 ≥ 180 天，仅审计角色可查询，查询行为本身也记入审计。

---

## 5. 评审红线清单

PR 评审时以下条款**一票否决**：

| # | 红线 |
|---|---|
| 1 | Agent 层（`src/agent/`）出现业务规则判断逻辑 |
| 2 | 写操作工具未标注风险等级，或高风险工具未声明 `bpm_approved` |
| 3 | 任何密钥、地址、连接串硬编码（必须走 `.env` / 配置中心） |
| 4 | 外部请求缺少超时 / 重试 / 异常捕获 / 参数校验任一项 |
| 5 | 工具调用绕过 MCP 网关（Agent 直连业务系统 API / 数据库） |
| 6 | 工具调用缺审计埋点，或审计字段不全 |
| 7 | 直接向 `main` 分支推送提交 |
| 8 | 写操作未携带幂等键（idempotency_key）或幂等逻辑被绕过 |
| 9 | 业务参数（供应商/库存水位/接口路径/流程ID）硬编码而非走配置 |

### 5.1 企业级稳定性规范（Phase 1 落地）

- **幂等防重**：写操作（MEDIUM/HIGH）必须携带幂等键（`trace_id:工具名:参数指纹`，由 `GatewayClient.make_idempotency_key` 生成）；网关执行前查审计表，同键 SUCCESS 记录直接复用结果（审计状态 `SUCCESS_IDEMPOTENT_HIT`），防止重试/重复点击造成重复下单；幂等查库失败降级放行（不阻断业务）。
- **熔断降级**：所有外部系统客户端（继承 `BaseHttpClient`）内置三态熔断器（CLOSED→OPEN→HALF_OPEN），连续失败达阈值（`BREAKER_FAILURE_THRESHOLD`）快速失败，冷却期（`BREAKER_RECOVERY_SECONDS`）后半开探测恢复；4xx 业务错误不计入熔断。
- **配置外置**：业务规则（安全水位/默认供应商/接口路径）全部环境变量管理（见 `.env.example`），禁止代码硬编码。
- **友好错误**：API 层全局异常处理，已知业务错误返回错误码+可读信息，未预期异常只留日志、前端统一提示，禁止堆栈外泄。

### 5.2 认证与角色权限规范（Phase 2 落地）

- **JWT 用户认证**：`AUTH_ENABLED=true` 时 `/chat*` 强制 Bearer JWT（HS256，标准库实现于 `common/security.py`，12h 有效期）；用户身份取自令牌 `sub`，**禁止信任请求体 user_id**；口令 PBKDF2-SHA256（10万轮迭代+随机盐）散列存储于 `auth_user` 表，禁止明文。
- **种子账号**：首次启动自动播种 `admin/purchaser/viewer`（见 `SEED_USERS`），**生产环境登录后必须立即改密**。
- **角色权限双防线（服务端强制）**：用户角色 -> 允许 Agent 角色映射（`USER_ROLE_ALLOWED_AGENTS`）；第一道防线在调度器（`filter_plan_by_role` 越权子任务直接剔除），第二道在网关客户端（角色断言，即使计划被绕过也拒绝调用）；viewer 仅只读。
- **异步任务**：长链路对话必须走 `POST /chat/async`（立即返回 task_id）+ `GET /chat/tasks/{id}` 轮询；任务状态（PENDING/RUNNING/OK/PARTIAL/FAILED）存 Redis（TTL 1h），异常兜底 FAILED 不悬空；多实例部署需演进为 Celery/RQ 分布式队列。
- **会话外置**：对话历史写 Redis（每用户最近 20 条，TTL 7 天，`/chat/sessions/me` 查询），进程重启/多实例不丢上下文。
- **HTTPS**：生产流量必须 TLS（`--profile tls` Nginx 反代，安全响应头 HSTS/nosniff/DENY）；`X-Forwarded-For` 透传真实 client_ip 入审计。

### 5.3 CI/CD 流水线规范（Phase 3 落地）

**流水线拓扑**（`.github/workflows/`，GitHub Actions）：

| 工作流 | 触发 | 内容 | 时长预期 |
|---|---|---|---|
| `ci.yml` / lint | PR + push(main/dev) | ruff 严重错误级检查（E9/F63/F7/F82/F401，配置 `.ruff.toml`） | 秒级 |
| `ci.yml` / unit-tests | PR + push | 容器化 pytest（构建 agent 镜像 + postgres/redis 服务，`PYTHONPATH=/app`） | ~3min |
| `ci.yml` / java-build | **路径过滤**（`ruoyi-*`/`pom.xml`/clinic.Dockerfile 变更才触发） | Maven 编译 ruoyi-admin，jar 上传 artifact（7 天） | ~5min |
| `e2e.yml` / mock-stack-e2e | push(main) + 关键路径 PR + 手动 | 全栈启动 → 幂等/熔断/半开恢复 → `scripts/ci_e2e.sh`（认证/角色/异步/审批）→ BPM 通过+驳回链路 | ~8min |
| `e2e.yml` / clinic-stack-e2e | **仅手动**（勾选 `with_clinic`） | 真实 Java 底座构建 + 健康检查 + 库存接口冒烟 + 真实落库幂等 | ~15min |

**强制规范**：
1. PR 必须绿（lint + unit-tests）方可合并；Java 变更额外要求 java-build 通过；
2. main 分支 push 自动跑全量 e2e；发布前手动触发 `with_clinic` 真实底座链路；
3. e2e 冒烟统一走 `scripts/ci_e2e.sh`（CI 与本地同一份脚本，`BASE_URL`/`MOCK_URL` 可覆盖），禁止为通过 CI 单独改脚本；
4. 新增功能必须同步补单测（unit-tests 覆盖）与冒烟断言（ci_e2e.sh 对应用例），测试缺失视为 PR 不完整；
5. 失败排查：workflow 失败步骤自动导出服务日志 + 审计表尾部 20 条（见 e2e.yml `if: failure()` 步骤）。
