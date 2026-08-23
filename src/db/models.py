"""数据库模型：审计日志表（全链路审计持久化，保留期 >= 180 天）。"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, JSON, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """ORM 基类。"""


class AuthUser(Base):
    """平台登录用户（P2 认证落地：口令 PBKDF2 散列存储，禁止明文）。"""

    __tablename__ = "auth_user"
    __table_args__ = (Index("uq_auth_user_username", "username", unique=True),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), comment="用户名（唯一）")
    password_hash: Mapped[str] = mapped_column(String(256), comment="口令散列 pbkdf2_sha256$salt$dk")
    role: Mapped[str] = mapped_column(String(32), default="viewer", comment="用户角色 admin/purchaser/viewer")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AuditLog(Base):
    """工具调用审计日志（字段与开发规范 4.1 一一对应，缺一即违规）。

    企业级强化字段：business_id（业务单据号）、idempotency_key（幂等防重键）、
    client_ip（调用来源IP，审计溯源）。已有环境升级需手动 ALTER 补列。
    """

    __tablename__ = "agent_audit_log"
    __table_args__ = (
        Index("ix_audit_trace_id", "trace_id"),
        Index("ix_audit_tool_name", "tool_name"),
        Index("ix_audit_ts", "ts"),
        Index("ix_audit_idem_key", "idempotency_key"),
        Index("ix_audit_business_id", "business_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    trace_id: Mapped[str] = mapped_column(String(64), comment="任务链路ID（多Agent全程相同）")
    user_instruction: Mapped[str] = mapped_column(Text, default="", comment="用户原始指令")
    agent_id: Mapped[str] = mapped_column(String(64), comment="执行调用的智能体角色")
    tool_name: Mapped[str] = mapped_column(String(128), comment="工具名")
    tool_input: Mapped[dict | None] = mapped_column(JSON, comment="工具入参（已脱敏）")
    tool_output: Mapped[dict | None] = mapped_column(JSON, comment="返回结果（已截断脱敏）")
    duration_ms: Mapped[int] = mapped_column(Integer, comment="耗时（毫秒）")
    status: Mapped[str] = mapped_column(String(32), comment="结果状态")
    risk_level: Mapped[str] = mapped_column(String(8), comment="工具风险等级")
    operator_user_id: Mapped[str] = mapped_column(String(64), default="", comment="操作用户ID")
    operator_role: Mapped[str] = mapped_column(String(64), default="", comment="操作Agent角色")
    bpm_workflow_id: Mapped[str | None] = mapped_column(String(128), comment="关联BPM流程ID（写操作必填）")
    business_id: Mapped[str | None] = mapped_column(String(128), comment="业务单据号（订单号/流程ID）")
    idempotency_key: Mapped[str | None] = mapped_column(String(160), comment="幂等键：同键写操作防重")
    client_ip: Mapped[str | None] = mapped_column(String(64), comment="调用来源IP（审计溯源）")
