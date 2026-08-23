"""审计埋点：每条工具调用记录全链路字段（JSON 日志 + 数据库双写）。

数据库写入为尽力而为（best-effort）：DB 故障时仅记错误日志、不阻断业务调用，
但 JSON 审计日志始终落地，满足"审计先于业务"的企业合规要求。
"""

import time
from typing import Any

from src.common.constants import AUDIT_OUTPUT_TRUNCATE, ToolRiskLevel
from src.common.logging import get_logger, sanitize

logger = get_logger("audit")


def _truncate(value: Any, limit: int = AUDIT_OUTPUT_TRUNCATE) -> Any:
    """截断超长字符串字段，防止超大结果拖垮日志与审计表。"""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "...[truncated]"
    if isinstance(value, dict):
        return {k: _truncate(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate(v, limit) for v in value]
    return value


class AuditRecorder:
    """工具调用审计记录器。"""

    async def record(
        self,
        *,
        trace_id: str,
        user_instruction: str,
        agent_id: str,
        tool_name: str,
        tool_input: Any,
        tool_output: Any,
        duration_ms: int,
        status: str,
        operator_user_id: str,
        operator_role: str,
        risk_level: ToolRiskLevel | str,
        bpm_workflow_id: str | None = None,
        business_id: str | None = None,
        idempotency_key: str | None = None,
        client_ip: str | None = None,
    ) -> None:
        """记录一条工具调用审计（字段与开发规范 4.1 一一对应）。

        Args 各参数说明见开发规范 4.1 审计字段表；入参与出参自动脱敏、超长截断。
        """
        payload = {
            "trace_id": trace_id,
            "user_instruction": user_instruction,
            "agent_id": agent_id,
            "tool_name": tool_name,
            "tool_input": _truncate(sanitize(tool_input)) if tool_input is not None else None,
            "tool_output": _truncate(sanitize(tool_output)) if tool_output is not None else None,
            "duration_ms": duration_ms,
            "status": status,
            "operator_identity": {"user_id": operator_user_id, "agent_role": operator_role},
            "risk_level": str(getattr(risk_level, "value", risk_level)),
            "bpm_workflow_id": bpm_workflow_id,
            "business_id": business_id,
            "idempotency_key": idempotency_key,
            "client_ip": client_ip,
        }
        logger.info("TOOL_AUDIT", extra={"audit": payload})
        await self._write_db(payload)

    async def find_success_by_idempotency_key(
        self, idempotency_key: str, tool_name: str
    ) -> dict[str, Any] | None:
        """按幂等键查询最近一条成功审计（写操作幂等防重的依据）。

        Returns:
            命中返回 {"tool_output": ..., "business_id": ...}；未命中返回 None；
            数据库不可用时返回 None（降级放行执行，不阻断业务）。
        """
        try:
            from sqlalchemy import select

            from src.db.engine import get_session_factory
            from src.db.models import AuditLog

            async with get_session_factory()() as session:
                stmt = (
                    select(AuditLog)
                    .where(
                        AuditLog.idempotency_key == idempotency_key,
                        AuditLog.tool_name == tool_name,
                        AuditLog.status == "SUCCESS",
                    )
                    .order_by(AuditLog.id.desc())
                    .limit(1)
                )
                row = (await session.execute(stmt)).scalar_one_or_none()
                if row is None:
                    return None
                return {"tool_output": row.tool_output, "business_id": row.business_id}
        except Exception:  # noqa: BLE001 —— 幂等查库失败必须降级放行，不能阻断业务
            logger.exception("幂等键查询失败（降级放行执行）: key=%s tool=%s", idempotency_key, tool_name)
            return None

    async def _write_db(self, payload: dict[str, Any]) -> None:
        """审计入库（尽力而为，失败不阻断业务但必须留痕）。"""
        try:
            # 延迟导入，避免与 db 模块产生加载期循环依赖
            from src.db.engine import get_session_factory
            from src.db.models import AuditLog

            operator = payload["operator_identity"]
            async with get_session_factory()() as session:
                session.add(
                    AuditLog(
                        trace_id=payload["trace_id"],
                        user_instruction=payload["user_instruction"],
                        agent_id=payload["agent_id"],
                        tool_name=payload["tool_name"],
                        tool_input=payload["tool_input"],
                        tool_output=payload["tool_output"],
                        duration_ms=payload["duration_ms"],
                        status=payload["status"],
                        risk_level=payload["risk_level"],
                        operator_user_id=operator["user_id"],
                        operator_role=operator["agent_role"],
                        bpm_workflow_id=payload.get("bpm_workflow_id"),
                        business_id=payload.get("business_id"),
                        idempotency_key=payload.get("idempotency_key"),
                        client_ip=payload.get("client_ip"),
                    )
                )
                await session.commit()
        except Exception:  # noqa: BLE001 —— 审计DB故障不允许影响业务链路
            logger.exception(
                "审计日志入库失败(已落地JSON日志兜底): trace_id=%s tool=%s ts=%s",
                payload.get("trace_id"), payload.get("tool_name"), time.time(),
            )


_recorder: AuditRecorder | None = None


def get_audit_recorder() -> AuditRecorder:
    """获取审计记录器单例。"""
    global _recorder
    if _recorder is None:
        _recorder = AuditRecorder()
    return _recorder
