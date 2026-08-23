"""模拟采购审批任务：本地一键演示完整业务闭环（无需启动任何外部系统）。

演示流程（README 5.3 落地场景的本地复现）：
  阶段一  复合指令「查库存 + 发起采购审批 + 自动下单」
            调度Agent拆分3子任务 → 查询Agent发现缺货 → 审批Agent发起Conductor流程
            → 操作Agent尝试下单 → 网关BPM强校验拦截（PENDING，未审批禁止写入）
  阶段二  模拟审批人在 Conductor 点击【通过】（附真实环境等价 curl）
  阶段三  指令「审批已通过，执行订单 workflow_id=...」
            审批Agent确认 APPROVED → 操作Agent下单 → 网关BPM校验放行 → 订单创建成功

真实性说明：LangGraph 编排、Casbin 权限拦截、网关 BPM 强校验、审计埋点全部走真实代码，
仅对诊所 API / Conductor / LLM / 审计DB / MCP传输 打桩模拟。

BPM 排查日志（三层视角，用于定位流程状态流转问题）：
  [Conductor]  原始 API 交互（发起/查询工作流的等价 HTTP 调用与返回）
  [BPM校验]    网关强校验的原始状态 -> APPROVED/PENDING/REJECTED 映射判定与放行/拦截结论
  [BPM轨迹]    带毫秒时间戳的状态流转时间线（演示结束汇总打印，可对照审计日志 trace_id）

用法：
  容器内（推荐，零本地依赖）：docker-compose exec agent-service python scripts/demo_approval.py
  本地裸跑（需 pip install -r src/requirements.txt）：python scripts/demo_approval.py
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# 仓库根加入 sys.path（兼容从 scripts/ 目录直接运行）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台中文输出兜底

WORKFLOW_ID = "wf-demo-001"
# 模拟 Conductor 工作流状态（阶段二由 RUNNING 翻转为 COMPLETED）
APPROVAL_STATE: dict[str, str] = {WORKFLOW_ID: "RUNNING"}
ORDER_LOG: list[dict] = []
# BPM 状态流转时间线：(时间戳, 事件, 详情)，演示结束汇总打印
BPM_TIMELINE: list[tuple[str, str, str]] = []


def record_bpm(event: str, detail: str) -> None:
    """记录一条 BPM 状态流转轨迹（实时打印 + 追加时间线，供结尾汇总）。"""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    BPM_TIMELINE.append((ts, event, detail))
    print(f"    [BPM轨迹] {ts} {event} | {detail}")


def banner(title: str) -> None:
    """打印阶段横幅。"""
    print("\n" + "=" * 62)
    print(f" {title}")
    print("=" * 62)


def install_mocks() -> None:
    """安装外部系统模拟补丁。

    打桩范围：诊所API、Conductor、LLM（降级纯规则分发）、审计DB（改打印）、
    MCP传输层（进程内直调注册表）。网关拦截管道与多智能体编排保持全真实。
    """
    from src.agent import llm as llm_mod
    from src.services import clinic_client as cc
    from src.workflow import conductor as cd

    # LLM 降级为纯规则分发：保证演示确定性、离线可跑
    llm_mod.get_chat_model = lambda: None

    # ---- 诊所业务底座模拟 ----
    async def fake_query_inventory(self, medicine_name=""):
        print(f"    [诊所系统] GET /clinic/inventory/list (medicineName={medicine_name!r})")
        return [
            cc.InventoryItem.model_validate({
                "medicineName": "阿莫西林胶囊", "spec": "0.5g×24粒", "unit": "盒",
                "quantity": 2, "salePrice": 8.5,   # 库存2盒 < 安全水位10 → 缺货
            })
        ]

    async def fake_create_order(self, order):
        print(f"    [诊所系统] POST /clinic/purchase/order 供应商={order.supplier} 明细={len(order.items)}项")
        ORDER_LOG.append(order.model_dump())
        return cc.OrderResult.model_validate({"orderId": "PO-20260823-001", "status": "CREATED"})

    cc.ClinicClient.query_inventory = fake_query_inventory
    cc.ClinicClient.create_purchase_order = fake_create_order

    # ---- Conductor BPM 模拟（含三层排查日志：原始API / 网关映射判定 / 流转轨迹） ----
    async def fake_start(self, workflow_name, correlation_id, payload):
        items = payload.get("items", [])
        print(f"    [Conductor] POST /api/workflow/{workflow_name} (correlationId={correlation_id})")
        print(f"    [Conductor]   审批单: {payload.get('title')!r} 申请人={payload.get('applicant')} 明细={len(items)}项")
        for i, item in enumerate(items, 1):
            print(f"    [Conductor]     {i}. {item.get('medicine_name')} x{item.get('quantity')} @{item.get('unit_price')}")
        print(f"    [Conductor]   返回 workflowId={WORKFLOW_ID}")
        record_bpm("发起工作流", f"{WORKFLOW_ID} 进入 RUNNING（WAIT 节点挂起，等待人工审批）")
        return WORKFLOW_ID

    async def fake_status(self, workflow_id):
        status = APPROVAL_STATE.get(workflow_id, "UNKNOWN")
        print(f"    [Conductor] GET /api/workflow/{workflow_id}/status -> {status}")
        return {"workflowId": workflow_id, "status": status}

    cd.ConductorClient.start_workflow = fake_start
    cd.ConductorClient.get_workflow_status = fake_status

    # 网关强校验映射追踪：真实 is_approved 代码路径外包一层日志（不影响判定逻辑）
    _orig_is_approved = cd.ConductorClient.is_approved

    async def traced_is_approved(self, workflow_id):
        result = await _orig_is_approved(self, workflow_id)
        raw = APPROVAL_STATE.get(workflow_id, "UNKNOWN")
        verdict = "放行写入" if result.value == "APPROVED" else "拦截写入"
        print(f"    [BPM校验] {workflow_id}: Conductor原始状态={raw} -> 网关映射={result.value}（{verdict}）")
        record_bpm("网关强校验", f"{workflow_id} 原始={raw} 判定={result.value} -> {verdict}")
        return result

    cd.ConductorClient.is_approved = traced_is_approved

    # ---- 审计入库改打印（JSON 审计日志仍真实输出；无 PostgreSQL 环境不报错） ----
    from src.mcp_gateway.audit import AuditRecorder

    async def fake_write_db(self, payload):
        print(
            f"    [审计入库] {payload['tool_name']:<26} -> {payload['status']:<18}"
            f" risk={payload['risk_level']:<6} bpm={payload['bpm_workflow_id']}"
        )

    AuditRecorder._write_db = fake_write_db

    # ---- MCP 传输层改进程内直调（Agent -> 网关注册表，拦截管道全真实） ----
    import src.mcp_gateway.tools  # noqa: F401  导入触发 @mcp_tool 注册
    from src.agent import gateway_client as gc
    from src.mcp_gateway.registry import TOOL_REGISTRY

    async def fake_call(self, state, role, tool_name, params):
        """组装真实 ToolContext 后直调网关包装函数（权限/BPM/审计全部生效）。"""
        context = {
            "user_id": state["user_id"],
            "agent_role": role.value,
            "trace_id": state["trace_id"],
            "user_instruction": state["user_instruction"],
            "bpm_workflow_id": state.get("pending_workflow_id"),
        }
        _, fn = TOOL_REGISTRY[tool_name]
        return await fn(params, context)

    gc.GatewayClient.call = fake_call


async def run_phase(graph, instruction: str, trace_id: str) -> dict:
    """驱动一次完整多智能体协作（等价于 POST /chat）。"""
    state = {
        "messages": [{"role": "user", "content": instruction}],
        "user_id": "u-demo",
        "user_instruction": instruction,
        "trace_id": trace_id,
        "results": [],
    }
    return await graph.ainvoke(state)


def print_answer(final_state: dict) -> None:
    """打印面向用户的最终答复。"""
    from src.agent.graph import compose_answer

    print("\n最终答复：")
    for line in compose_answer(final_state).splitlines():
        print(f"  {line}")


async def main() -> None:
    """演示主流程：三阶段完整业务闭环。"""
    install_mocks()
    from src.agent.graph import build_graph
    from src.common.logging import setup_logging

    setup_logging("INFO")
    graph = build_graph()

    # ================= 阶段一：复合指令（查询+审批+下单） =================
    banner("阶段一：发起「查库存 + 采购审批 + 自动下单」复合指令")
    ins1 = "查一下阿莫西林胶囊库存，缺货的话发起采购审批并自动下单"
    print(f"用户指令：{ins1}\n")
    f1 = await run_phase(graph, ins1, "trace-demo-01")
    print_answer(f1)
    print("\n>>> 关键效果：操作Agent已尝试下单，但网关BPM强校验拦截（PENDING），")
    print(">>> 未获人工审批前，任何高风险写操作都无法执行。")

    # ================= 阶段二：模拟人工审批 =================
    banner("阶段二：模拟审批人在 Conductor 点击【通过】")
    print("真实环境等价操作（Conductor UI 或 Task API）：")
    print(f"  # 1.查询待审批任务")
    print(f"  curl http://localhost:5000/api/tasks/in_progress/workflow/{WORKFLOW_ID}/wait_for_human_approval")
    print(f"  # 2.审批通过（output.approved=\"false\" 即驳回）")
    print(f"  curl -X POST http://localhost:5000/api/tasks -H \"Content-Type: application/json\" \\")
    print(f"    -d '{{\"workflowInstanceId\":\"{WORKFLOW_ID}\",\"taskReferenceName\":\"wait_for_human_approval\","
          f"\"status\":\"COMPLETED\",\"output\":{{\"approved\":\"true\"}}}}'")
    before = APPROVAL_STATE[WORKFLOW_ID]
    print(f"\n>>> 审批动作前状态检查：{WORKFLOW_ID} = {before}")
    APPROVAL_STATE[WORKFLOW_ID] = "COMPLETED"
    print(f">>> 审批动作后状态检查：{WORKFLOW_ID} = {APPROVAL_STATE[WORKFLOW_ID]}")
    record_bpm(
        "人工审批通过",
        f"{WORKFLOW_ID} {before} -> COMPLETED（TERMINATE 终态，workflowOutput.approvalResult=APPROVED）",
    )

    # ================= 阶段三：审批通过后继续执行 =================
    banner("阶段三：携带流程ID继续执行订单")
    ins3 = f"审批已通过，执行订单 workflow_id={WORKFLOW_ID}"
    print(f"用户指令：{ins3}\n")
    f3 = await run_phase(graph, ins3, "trace-demo-02")
    print_answer(f3)

    print("\n订单落库结果：")
    print(json.dumps(ORDER_LOG, ensure_ascii=False, indent=2))

    # ================= 收尾：BPM 状态流转轨迹汇总 =================
    banner("BPM 状态流转轨迹汇总（排查流程状态问题用）")
    print(f"  {'时间戳':<14}{'事件':<8}详情")
    print("  " + "-" * 56)
    for ts, event, detail in BPM_TIMELINE:
        print(f"  {ts:<14}{event:<8}{detail}")

    # ================= 收尾说明 =================
    banner("演示完成：全链路安全闭环")
    print("  1. 未审批先下单  -> 网关 BPM 强校验拦截（阶段一）")
    print("  2. 人工审批通过  -> Conductor 工作流 COMPLETED（阶段二）")
    print("  3. 凭流程ID下单  -> 网关二次核验 Conductor 实际状态后放行（阶段三）")
    print("  4. 全部工具调用均已审计留痕（trace-demo-01 / trace-demo-02 可检索）")


if __name__ == "__main__":
    asyncio.run(main())
