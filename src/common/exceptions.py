"""内部异常体系：所有异常携带错误码前缀，便于跨 MCP 边界传递后还原语义。"""

from src.common.constants import AuditStatus


class BaseAppError(Exception):
    """平台基础异常。

    所有自定义异常必须继承本类；str 形式统一为 "[错误码] 错误信息"，
    以便工具错误经由 MCP 边界序列化后，调用侧仍可解析出错误码。
    """

    code: str = "INTERNAL_ERROR"
    audit_status: AuditStatus = AuditStatus.BIZ_ERROR

    def __init__(self, message: str) -> None:
        super().__init__(f"[{self.code}] {message}")
        self.message = message

    def __str__(self) -> str:  # noqa: D105
        return f"[{self.code}] {self.message}"


class ToolPermissionDenied(BaseAppError):
    """Agent 角色无该 MCP 工具调用权限（PyCasbin 拦截）。"""

    code = "PERMISSION_DENIED"
    audit_status = AuditStatus.PERMISSION_DENIED


class ParamValidationError(BaseAppError):
    """工具入参 / 调用上下文参数校验失败。"""

    code = "VALIDATION_FAILED"
    audit_status = AuditStatus.VALIDATION_FAILED


class BizSystemUnavailable(BaseAppError):
    """下游业务系统不可用（超时、连接失败、5xx）。"""

    code = "BIZ_SYSTEM_UNAVAILABLE"
    audit_status = AuditStatus.TIMEOUT


class BizClientError(BaseAppError):
    """下游业务系统返回 4xx 业务错误（参数不合法、业务规则拒绝等）。"""

    code = "BIZ_CLIENT_ERROR"
    audit_status = AuditStatus.BIZ_ERROR


class BPMNotApprovedError(BaseAppError):
    """高风险写操作未获得 BPM 审批通过即尝试执行（网关强制拦截）。"""

    code = "BPM_NOT_APPROVED"
    audit_status = AuditStatus.BPM_NOT_APPROVED


class BPMPendingError(BaseAppError):
    """高风险写操作对应的审批流程仍在等待人工处理。"""

    code = "BPM_PENDING"
    audit_status = AuditStatus.BPM_PENDING
