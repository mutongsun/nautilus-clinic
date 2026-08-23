"""@mcp_tool 装饰器：网关统一拦截管道。

执行顺序（开发规范 2.2 / 2.4 强制 + 企业级强化）：
    ① 上下文校验（ToolContext pydantic 校验）
    ② 权限拦截（PyCasbin，拒绝即审计 PERMISSION_DENIED）
    ③ 幂等防重（写操作带 idempotency_key 且已有成功记录 → 直接复用上次结果，
       防止重试/重复点击造成重复下单、重复发起审批）
    ④ 高风险 BPM 强校验（必须有 workflow_id 且 Conductor 实际状态为 APPROVED，
       防止 Agent 幻觉伪造"已审批"上下文）
    ⑤ 执行工具本体（入参由工具内部 pydantic 校验）
    ⑥ 全链路审计（成功 / 失败均落审计，含 business_id / idempotency_key / client_ip）
"""

import time
from collections.abc import Awaitable, Callable
from functools import wraps

from pydantic import ValidationError

from src.common.constants import AuditStatus, ToolRiskLevel
from src.common.exceptions import (
    BaseAppError,
    BPMNotApprovedError,
    BPMPendingError,
    ParamValidationError,
    ToolPermissionDenied,
)
from src.common.logging import get_logger
from src.config.settings import get_settings
from src.mcp_gateway.audit import get_audit_recorder
from src.mcp_gateway.permission import check_tool_permission
from src.mcp_gateway.registry import ToolSpec, register_tool
from src.mcp_gateway.schemas import ToolContext

logger = get_logger(__name__)


def _extract_business_id(output: dict | None) -> str | None:
    """从工具输出提取业务单据号（订单号/流程ID），供审计检索与幂等关联。"""
    if not isinstance(output, dict):
        return None
    for key in ("order_id", "workflow_id", "consultation_id"):
        value = output.get(key)
        if value:
            return str(value)
    return None


async def _bpm_is_approved(workflow_id: str) -> str:
    """查询 Conductor 审批状态（独立函数便于测试 monkeypatch）。"""
    from src.workflow.conductor import ApprovalStatus, get_conductor_client

    status = await get_conductor_client().is_approved(workflow_id)
    return status.value if isinstance(status, ApprovalStatus) else str(status)


def mcp_tool(
    *,
    name: str,
    description: str,
    risk_level: ToolRiskLevel,
    required_roles: frozenset[str] | set[str],
    bpm_required: bool = False,
) -> Callable[[Callable[..., Awaitable[dict]]], Callable[[dict, dict], Awaitable[dict]]]:
    """声明并注册一个 MCP 网关工具。

    Args:
        name: 工具唯一名。
        description: 工具描述（暴露给 Agent 的选型依据）。
        risk_level: 风险等级；HIGH 必须同时 bpm_required=True。
        required_roles: 允许调用的 Agent 角色（声明式文档；强制以 Casbin 策略为准）。
        bpm_required: 是否强制 BPM 审批通过后才可执行。

    Raises:
        ValueError: HIGH 风险工具未声明 bpm_required。
    """
    if risk_level is ToolRiskLevel.HIGH and not bpm_required:
        raise ValueError(f"高风险工具 {name} 必须声明 bpm_required=True（开发规范 2.4）")

    def decorator(fn: Callable[..., Awaitable[dict]]) -> Callable[[dict, dict], Awaitable[dict]]:
        @wraps(fn)
        async def wrapper(params: dict, context: dict) -> dict:
            """网关统一拦截管道（权限 -> BPM -> 执行 -> 审计）。"""
            started = time.perf_counter()

            # ① 上下文校验
            try:
                ctx = ToolContext.model_validate(context or {})
            except ValidationError as exc:
                raise ParamValidationError(f"调用上下文不合法: {exc.errors()[:3]}") from exc

            async def audit(status: AuditStatus | str, output: dict | None = None,
                            bpm_id: str | None = ctx.bpm_workflow_id,
                            business_id: str | None = None) -> None:
                """记录本条审计（成功失败共用，保证全链路留痕）。"""
                await get_audit_recorder().record(
                    trace_id=ctx.trace_id,
                    user_instruction=ctx.user_instruction,
                    agent_id=ctx.agent_role,
                    tool_name=name,
                    tool_input=params,
                    tool_output=output,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    status=str(getattr(status, "value", status)),
                    operator_user_id=ctx.user_id,
                    operator_role=ctx.agent_role,
                    risk_level=risk_level,
                    bpm_workflow_id=bpm_id,
                    business_id=business_id or _extract_business_id(output),
                    idempotency_key=ctx.idempotency_key,
                    client_ip=ctx.client_ip,
                )

            # ② 权限拦截（最小权限体系）
            if not check_tool_permission(ctx.agent_role, name):
                await audit(AuditStatus.PERMISSION_DENIED)
                raise ToolPermissionDenied(f"角色 {ctx.agent_role} 无工具 {name} 调用权限")

            # ③ 幂等防重：同幂等键已有成功记录 → 直接复用上次结果（不重复执行写操作）
            if (
                get_settings().idempotency_enabled
                and risk_level is not ToolRiskLevel.LOW
                and ctx.idempotency_key
            ):
                hit = await get_audit_recorder().find_success_by_idempotency_key(
                    ctx.idempotency_key, name
                )
                if hit is not None:
                    logger.info(
                        "幂等命中，复用历史成功结果: tool=%s key=%s business_id=%s",
                        name, ctx.idempotency_key, hit.get("business_id"),
                    )
                    cached = hit.get("tool_output") or {}
                    await audit("SUCCESS_IDEMPOTENT_HIT", output=dict(cached),
                                business_id=hit.get("business_id"))
                    return dict(cached)

            # ④ 高风险写操作 BPM 强校验
            if risk_level is ToolRiskLevel.HIGH:
                if not ctx.bpm_workflow_id:
                    await audit(AuditStatus.BPM_NOT_APPROVED)
                    raise BPMNotApprovedError(f"工具 {name} 为高风险写操作，必须携带 bpm_workflow_id")
                approval = await _bpm_is_approved(ctx.bpm_workflow_id)
                if approval == "APPROVED":
                    pass  # 审批通过，放行执行
                elif approval == "PENDING":
                    await audit(AuditStatus.BPM_PENDING)
                    raise BPMPendingError(f"审批流程 {ctx.bpm_workflow_id} 等待人工处理中")
                else:
                    await audit(AuditStatus.BPM_NOT_APPROVED)
                    raise BPMNotApprovedError(
                        f"审批流程 {ctx.bpm_workflow_id} 状态为 {approval}，禁止执行写操作"
                    )

            # ⑤ 执行工具本体（业务异常统一转审计后向上抛出）
            try:
                result = await fn(params, ctx)
            except BaseAppError as exc:
                await audit(exc.audit_status)
                raise
            except Exception as exc:  # noqa: BLE001 —— 未预期异常：记堆栈+审计+上抛
                logger.exception(
                    "工具执行异常: tool=%s trace_id=%s user_id=%s agent=%s",
                    name, ctx.trace_id, ctx.user_id, ctx.agent_role,
                )
                await audit(AuditStatus.BIZ_ERROR)
                raise BaseAppError(f"工具 {name} 内部错误: {exc}") from exc

            # ⑥ 成功审计
            await audit(AuditStatus.SUCCESS, output=result)
            return result

        register_tool(
            ToolSpec(
                name=name,
                description=description,
                risk_level=risk_level,
                required_roles=frozenset(required_roles),
                bpm_required=bpm_required,
            ),
            wrapper,
        )
        return wrapper

    return decorator
