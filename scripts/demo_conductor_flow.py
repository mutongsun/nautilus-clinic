"""Conductor 审批链路全流程演示：从工作流发起到 Task API 回调闭环。

模拟真实 Conductor 集群交互（容器内访问 conductor-server:8080，由准真实 mock 提供）：

  链路A（审批通过）：
    ① 发起采购审批 -> 唯一 workflowId（UUID，证明真实实例化）
    ② 未审批即下单 -> 网关 BPM 强校验拦截（BPM_PENDING）
    ③ 审批人 Task API 回调（GET 挂起任务拿 taskId -> POST /api/tasks approved=true）
       -> DECISION 流转 -> 工作流 COMPLETED
    ④ 再下单 -> 网关放行 -> 真实 Java 底座落库（PO- 单号）
  链路B（审批驳回）：
    ⑤ 新流程 -> 回调 approved=false -> FAILED
    ⑥ 下单 -> 网关 BPM 拒绝（BPM_NOT_APPROVED），零落库

用法（容器内，与平台服务同一网络）：
  docker compose exec agent-service python scripts/demo_conductor_flow.py
"""

import asyncio
import sys
import uuid as uuid_mod
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import httpx
from fastmcp import Client

from src.agent.gateway_client import GatewayClient
from src.config.settings import get_settings

CONDUCTOR = "http://conductor-server:8080"
TASK_REF = "wait_for_human_approval"

TIMELINE: list[tuple[str, str]] = []


def log(event: str, detail: str = "") -> None:
    """打印并记录时间线事件。"""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    TIMELINE.append((ts, event))
    print(f"  [{ts}] {event}{(' | ' + detail) if detail else ''}")


def banner(title: str) -> None:
    """打印阶段横幅。"""
    print("\n" + "=" * 66)
    print(f" {title}")
    print("=" * 66)


async def call_tool(tool: str, params: dict, ctx: dict) -> tuple[dict | None, str | None]:
    """经 MCP 协议调用网关工具；返回 (结果, 错误摘要)。"""
    async with Client(get_settings().mcp_gateway_url) as client:
        try:
            result = await client.call_tool(tool, {"params": params, "context": ctx})
            return GatewayClient._parse_result(result), None
        except Exception as exc:  # noqa: BLE001 —— 网关拒绝属于预期分支
            return None, str(exc)


def ctx_of(trace: str, wid: str | None = None, idem: str | None = None) -> dict:
    """组装网关调用上下文。"""
    return {
        "user_id": "u-bpm-demo",
        "agent_role": "agent-operator",
        "trace_id": trace,
        "user_instruction": "Conductor 审批链路演示",
        "bpm_workflow_id": wid,
        "idempotency_key": idem,
        "client_ip": "172.24.0.1",
    }


ORDER_PARAMS = {
    "supplier": "国药控股",
    "items": [{"medicineName": "阿莫西林胶囊", "quantity": 8, "unitPrice": 8.5}],
}


async def conductor_get(path: str) -> httpx.Response:
    """直连 Conductor API（模拟审批人视角）。"""
    async with httpx.AsyncClient(timeout=5) as c:
        return await c.get(f"{CONDUCTOR}{path}")


async def conductor_post(path: str, body: dict) -> httpx.Response:
    """直连 Conductor API（Task API 回调）。"""
    async with httpx.AsyncClient(timeout=5) as c:
        return await c.post(f"{CONDUCTOR}{path}", json=body)


async def approve_via_task_api(wid: str, approved: bool) -> None:
    """真实审批操作复刻：查挂起任务 -> Task API 回调 -> DECISION 流转。"""
    resp = await conductor_get(f"/api/tasks/in_progress/workflow/{wid}/{TASK_REF}")
    tasks = resp.json()
    if not tasks:
        print(f"  ⚠ 无挂起任务（工作流已终态）")
        return
    task_id = tasks[0]["taskId"]
    log(f"审批人查到挂起任务 taskId={task_id[:8]}…")
    callback = await conductor_post("/api/tasks", {
        "workflowInstanceId": wid,
        "taskReferenceName": TASK_REF,
        "taskId": task_id,
        "status": "COMPLETED",
        "output": {"approved": "true" if approved else "false"},
    })
    if callback.status_code == 200:
        state = await conductor_get(f"/api/workflow/{wid}/status")
        wf = state.json()
        log(f"Task API 回调 approved={approved} -> DECISION 流转 -> 工作流 {wf['status']}",
            str(wf.get("output", "")))
    else:
        print(f"  ⚠ 回调失败: {callback.status_code} {callback.text[:100]}")


async def main() -> None:
    """全链路演示主流程。"""
    run = uuid_mod.uuid4().hex[:6]

    # ============ 链路A：审批通过 ============
    banner("链路A：发起审批 -> 拦截 -> Task API 通过 -> 放行下单（真实落库）")

    log("① 审批Agent 发起采购审批流程")
    data, err = await asyncio.wait_for(_start_as_approval(run), timeout=15)
    if err or not data:
        print(f"  ✘ 发起失败: {err}")
        return
    wid = data["workflow_id"]
    is_uuid = len(wid) == 36 and wid.count("-") == 4
    log(f"工作流已启动 workflowId={wid[:13]}…", "UUID 唯一实例" if is_uuid else "非UUID！")

    log("② 未审批直接下单 -> 预期网关拦截")
    _, err = await call_tool("create_purchase_order", ORDER_PARAMS,
                             ctx_of(f"trace-bpm-a-{run}", wid, f"idem-a1-{run}"))
    verdict = "✔ 拦截成功" if err and "BPM_PENDING" in err else "✘ 未拦截！"
    log(f"网关强校验结果: {verdict}", (err or "")[:70])

    log("③ 审批人通过 Task API 完成审批（真实回调语义）")
    await approve_via_task_api(wid, approved=True)

    log("④ 审批通过后下单 -> 预期放行并真实落库")
    data, err = await call_tool("create_purchase_order", ORDER_PARAMS,
                                ctx_of(f"trace-bpm-a-{run}", wid, f"idem-a2-{run}"))
    if data:
        log(f"下单成功 order_id={data.get('order_id')} status={data.get('status')}", "真实Java落库")
    else:
        log(f"✘ 下单失败: {(err or '')[:90]}")

    # ============ 链路B：审批驳回 ============
    banner("链路B：发起审批 -> Task API 驳回 -> 拒绝写入（零落库）")

    log("⑤ 发起新流程并驳回")
    data, _ = await asyncio.wait_for(_start_as_approval(run + "r"), timeout=15)
    if not data:
        print("  ✘ 发起失败")
        return
    wid_r = data["workflow_id"]
    await approve_via_task_api(wid_r, approved=False)

    log("⑥ 驳回后下单 -> 预期 BPM 拒绝")
    _, err = await call_tool("create_purchase_order", ORDER_PARAMS,
                             ctx_of(f"trace-bpm-b-{run}", wid_r, f"idem-b-{run}"))
    verdict = "✔ 已拒绝" if err and "BPM_NOT_APPROVED" in err else f"结果异常: {(err or '')[:70]}"
    log(f"网关强校验结果: {verdict}")

    # ============ 汇总 ============
    banner("BPM 状态流转时间线")
    for ts, event in TIMELINE:
        print(f"  {ts}  {event}")
    print("\n宿主机取证：")
    print("  docker compose logs mock-backend --tail 30        # Task API 回调日志")
    print("  docker compose exec postgres psql -U nautilus -d nautilus_clinic \\")
    print("    -c \"SELECT order_no,total_amount FROM ruoyi.nautilus_purchase_order ORDER BY id DESC LIMIT 3;\"")
    print("  docker compose exec postgres psql -U nautilus -d nautilus_agent \\")
    print(f"    -c \"SELECT status,count(*) FROM agent_audit_log WHERE trace_id LIKE 'trace-bpm-%{run}' GROUP BY 1;\"")


async def _start_as_approval(run: str) -> tuple[dict | None, str | None]:
    """以 agent-approval 角色发起审批（start_purchase_approval 仅该角色可调）。"""
    ctx = {
        "user_id": "u-bpm-demo",
        "agent_role": "agent-approval",
        "trace_id": f"trace-bpm-{run}",
        "user_instruction": "Conductor 审批链路演示",
        "idempotency_key": f"bpm-start-{run}",
        "client_ip": "172.24.0.1",
    }
    return await call_tool("start_purchase_approval", {
        "title": f"阿莫西林采购申请（{run}）",
        "items": ORDER_PARAMS["items"],
    }, ctx)


if __name__ == "__main__":
    asyncio.run(main())
