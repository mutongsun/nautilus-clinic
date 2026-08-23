"""企业级稳定性真实链路验证：幂等防重 / 熔断快速失败 / 半开恢复。

通过 fastmcp Client 直连 MCP 网关（与 Agent 服务同一真实链路：网关拦截管道全部生效），
宿主机按阶段编排：

  # ① 幂等：同键重复下单，下游订单数不应增长
  docker compose restart mock-backend mcp-gateway   # 熔断器归零、订单计数归零
  docker compose exec agent-service python scripts/verify_enterprise.py idem

  # ② 熔断：拉闸下游，观察耗时骤降（重试退避 ~1.5s -> 快速失败 <10ms）
  docker compose stop mock-backend
  docker compose exec agent-service python scripts/verify_enterprise.py breaker

  # ③ 半开恢复：冷却期（默认30s）后下游复活，探测成功恢复闭合
  docker compose start mock-backend && sleep 32
  docker compose exec agent-service python scripts/verify_enterprise.py recover
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import httpx
from fastmcp import Client

from src.agent.gateway_client import GatewayClient
from src.config.settings import get_settings

MOCK = "http://mock-backend:9000"
WORKFLOW_ID = "wf-demo-001"

CTX_BASE = {
    "user_id": "u-verify",
    "agent_role": "agent-operator",
    "trace_id": "trace-idem-verify",
    "user_instruction": "企业级稳定性验证",
    "client_ip": "172.24.0.1",
}
PARAMS = {
    "supplier": "国药控股",
    "items": [{"medicine_name": "阿莫西林胶囊", "quantity": 8, "unit_price": 8.5}],
}


async def call_tool(tool: str, params: dict, ctx: dict) -> dict:
    """经 MCP 协议调用网关工具（与 Agent 服务完全相同的真实链路）。"""
    async with Client(get_settings().mcp_gateway_url) as client:
        result = await client.call_tool(tool, {"params": params, "context": ctx})
        return GatewayClient._parse_result(result)


async def _clinic_mode() -> str | None:
    """探测 nautilus-clinic 域名背后是真实 Java 还是 mock 别名。

    判别依据：mock 独有端点 GET /demo/workflows 的响应体——
      mock 返回实例字典（可为空 {}，但绝无 code 字段）；
      真实 Java（RuoYi）把未匹配路径包装为 HTTP 200 + {"code":401,"msg":...}
      （注意：不能用状态码判别，Java 对未知路径也返回 200）。
    Returns: "mock" | "real" | None（域名不可达）。
    """
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            inventory = await c.get("http://nautilus-clinic:8087/clinic/agent/inventory")
            if inventory.status_code != 200:
                return None
            probe = await c.get("http://nautilus-clinic:8087/demo/workflows")
            body = probe.json() if probe.headers.get("content-type", "").startswith("application/json") else {}
            return "real" if isinstance(body, dict) and body.get("code") == 401 else "mock"
    except Exception:  # noqa: BLE001
        return None


async def orders_count() -> int:
    """读取下游真实下单数（幂等观测点）。

    自动适配三种形态：
    - 真实模式（--profile clinic，Java 底座）：查真实库
      nautilus_clinic.ruoyi.nautilus_purchase_order 行数（asyncpg）；
    - Mock 别名模式（CI：runtime alias 把 nautilus-clinic 指到 mock）：
      读该 mock 实例的 /demo/orders 计数器（与 8087 下单端口同进程，计数一致）；
    - Mock 模式：读本地 MOCK 域名计数器。
    """
    mode = await _clinic_mode()
    if mode == "mock":
        async with httpx.AsyncClient(timeout=3) as c:
            return (await c.get("http://nautilus-clinic:9000/demo/orders")).json().get("count", -1)
    if mode == "real":
        import asyncpg

        from src.config.settings import get_settings

        # DATABASE_URL: postgresql+asyncpg://user:pwd@postgres:5432/nautilus_agent -> 换库名
        url = get_settings().database_url.replace("+asyncpg", "")
        host = url.split("@")[1].split(":")[0]
        port = url.split("@")[1].split(":")[1].split("/")[0]
        user, pwd = url.split("://")[1].split("@")[0].split(":")
        conn = await asyncpg.connect(host=host, port=int(port), user=user,
                                     password=pwd, database="nautilus_clinic")
        try:
            return await conn.fetchval("SELECT count(*) FROM ruoyi.nautilus_purchase_order")
        finally:
            await conn.close()
    async with httpx.AsyncClient(timeout=3) as c:
        return (await c.get(f"{MOCK}/demo/orders")).json().get("count", -1)


async def mock_post(path: str) -> dict:
    """调用 mock 演示控制端点。"""
    async with httpx.AsyncClient(timeout=5) as c:
        return (await c.post(f"{MOCK}{path}")).json()


def banner(title: str) -> None:
    """打印阶段横幅。"""
    print("\n" + "=" * 66)
    print(f" {title}")
    print("=" * 66)


async def phase_idem() -> None:
    """阶段①：幂等防重验证（同键复用，异键新单）。"""
    banner("阶段① 幂等防重：同幂等键重复下单，下游订单数不应增长")
    await mock_post("/demo/reset")
    base = await orders_count()
    print(f"下游订单基线数: {base}")

    # 幂等键每次运行唯一：网关审计表幂等缓存持久化（跨重启），
    # 固定键会被历史成功记录命中而跳过下游调用，导致验证失真
    import uuid

    run = uuid.uuid4().hex[:6]
    key_a, key_b = f"idem-A-{run}", f"idem-B-{run}"

    # 发起真实审批工作流（准真实 Conductor：唯一 UUID 实例，禁止固定流程ID）
    # 并即时审批通过，使后续高风险下单可执行
    start_ctx = dict(CTX_BASE, agent_role="agent-approval",
                     trace_id=f"trace-idem-start-{run}", idempotency_key=f"bpm-start-{run}")
    start = await call_tool("start_purchase_approval",
                            {"title": f"幂等验证采购（{run}）", "items": PARAMS["items"]},
                            start_ctx)
    if not isinstance(start, dict) or not start.get("workflow_id"):
        print(f"✘ 审批流程发起失败: {start!r}")
        return
    wid = start["workflow_id"]
    await mock_post("/demo/approve")  # 通过所有挂起审批（Task API 语义）
    print(f"审批流程已发起并通过: {wid[:13]}…")

    ctx_a = dict(CTX_BASE, bpm_workflow_id=wid, idempotency_key=key_a)
    ctx_b = dict(CTX_BASE, bpm_workflow_id=wid, idempotency_key=key_b)

    r1 = await call_tool("create_purchase_order", PARAMS, ctx_a)
    c1 = await orders_count()
    print(f"① 首次下单(key=A): order_id={r1.get('order_id')}  下游订单数={c1}")

    r2 = await call_tool("create_purchase_order", PARAMS, ctx_a)
    c2 = await orders_count()
    reused = "✔ 复用缓存，未真实下单" if c2 == c1 else "✘ 下游订单增长，幂等失效！"
    print(f"② 同键重复(key=A): order_id={r2.get('order_id')}  下游订单数={c2}  {reused}")

    r3 = await call_tool("create_purchase_order", PARAMS, ctx_b)
    c3 = await orders_count()
    verdict = "✔ 异键正常新单" if c3 == c2 + 1 else "✘ 异键未生成新单！"
    print(f"③ 异键下单(key=B): order_id={r3.get('order_id')}  下游订单数={c3}  {verdict}")

    ok = c1 == base + 1 and c2 == c1 and c3 == c2 + 1
    print(f"\n结论: {'✔ 幂等生效（同键零重复下单）' if ok else '✘ 幂等异常，检查审计表'}")
    print("审计佐证（宿主机执行）:")
    print(f"  docker compose exec postgres psql -U nautilus -d nautilus_agent -t -c "
          f"\"SELECT status,count(*) FROM agent_audit_log WHERE idempotency_key='{key_a}' GROUP BY status;\"")


async def phase_breaker() -> None:
    """阶段②：熔断验证（下游已拉闸，观察耗时从退避重试骤降到快速失败）。"""
    banner("阶段② 熔断快速失败：下游已停止，连续失败达阈值后不再打下游")
    rounds = 6
    for i in range(1, rounds + 1):
        ctx = dict(CTX_BASE, trace_id=f"trace-breaker-{i:02d}")
        t0 = time.perf_counter()
        try:
            await call_tool("query_inventory", {"medicine_name": ""}, ctx)
            outcome, mark = "成功", ""
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "熔断" in msg:
                outcome, mark = "熔断快速失败（未打下游）", "◀── 熔断器生效"
            else:
                outcome, mark = "下游失败（重试耗尽）", ""
        dur = (time.perf_counter() - t0) * 1000
        print(f"第{i}次调用: {dur:8.0f} ms  {outcome}  {mark}")
    print("\n判读: 前几次耗时含重试退避(数百ms~秒级)，熔断打开后 <10ms 即返回 → 下游被保护")


async def phase_recover() -> None:
    """阶段③：半开恢复验证（冷却期后下游复活，探测成功恢复闭合）。"""
    banner("阶段③ 半开恢复：下游已恢复，冷却期后探测成功 → 熔断器闭合")
    ctx = dict(CTX_BASE, trace_id="trace-recover-01")
    try:
        data = await call_tool("query_inventory", {"medicine_name": ""}, ctx)
        count = data.get("count", "?")
        print(f"恢复调用: 成功，返回 {count} 条库存 → ✔ 熔断器已恢复闭合")
    except Exception as exc:  # noqa: BLE001
        print(f"恢复调用: 仍失败（{str(exc)[:80]}）→ 冷却期未到或下游未恢复，稍后重试")


def main() -> None:
    """按命令行参数分发验证阶段。"""
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    match phase:
        case "idem":
            asyncio.run(phase_idem())
        case "breaker":
            asyncio.run(phase_breaker())
        case "recover":
            asyncio.run(phase_recover())
        case _:
            print(__doc__)
            sys.exit(1)


if __name__ == "__main__":
    main()
