"""Conductor BPM 审批流程客户端：发起审批、查询状态、审批通过性判定。

高风险写工具的网关强校验依赖本模块（开发规范 2.4：防止 Agent 幻觉伪造"已审批"上下文）。
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any

from src.common.exceptions import BizClientError
from src.common.logging import get_logger
from src.config.settings import get_settings
from src.services.base_client import BaseHttpClient

logger = get_logger(__name__)

# 审批工作流定义目录（随网关镜像发布，启动时自动注册到 Conductor）
_DEFINITIONS_DIR = Path(__file__).parent / "definitions"


class ApprovalStatus(str, Enum):
    """审批流程状态（映射自 Conductor 工作流状态）。"""

    PENDING = "PENDING"      # 流程运行中，等待人工处理
    APPROVED = "APPROVED"    # 流程完成（人工审批通过）
    REJECTED = "REJECTED"    # 流程被终止 / 驳回
    UNKNOWN = "UNKNOWN"      # 流程不存在或状态无法解析


class ConductorClient(BaseHttpClient):
    """Conductor OSS HTTP API 客户端。"""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(base_url=settings.conductor_base_url, timeout=5.0)

    async def start_workflow(
        self, workflow_name: str, correlation_id: str, payload: dict[str, Any]
    ) -> str:
        """发起审批工作流（对下游丢失定义自愈：404 未注册时重注册后重试一次）。

        真实 Conductor 集群重启/定义被清同样会出现 "workflow not registered"，
        网关仅在自身启动时注册一次不够——此处按需自愈重注册，生产级韧性。

        Args:
            workflow_name: 工作流定义名（如 purchase_approval）。
            correlation_id: 业务关联 ID（使用 trace_id，串联审计链路）。
            payload: 业务载荷（申请标题、明细、申请人等）。

        Returns:
            Conductor 工作流实例 ID（即审计字段 bpm_workflow_id）。
        """
        try:
            workflow_id = await self._request(
                "POST",
                f"/api/workflow/{workflow_name}",
                params={"correlationId": correlation_id},
                json_body=payload,
            )
        except BizClientError as exc:
            if "not registered" not in str(exc):
                raise
            logger.warning(
                "工作流定义丢失（下游重启所致），自动重注册后重试: workflow=%s", workflow_name
            )
            await self.ensure_workflow_registered(workflow_name)
            workflow_id = await self._request(
                "POST",
                f"/api/workflow/{workflow_name}",
                params={"correlationId": correlation_id},
                json_body=payload,
            )
        return str(workflow_id)

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """查询工作流实例状态摘要。

        Args:
            workflow_id: 工作流实例 ID。

        Returns:
            含 status 字段的状态摘要（COMPLETED / RUNNING / TERMINATED 等）。
        """
        return await self._request("GET", f"/api/workflow/{workflow_id}/status")

    async def is_approved(self, workflow_id: str) -> ApprovalStatus:
        """判定审批是否通过（网关高风险写操作强校验入口）。

        状态映射规则（企业可按实际流程定义扩展，如增加人工任务输出解析）：
            COMPLETED  -> APPROVED
            TERMINATED / FAILED -> REJECTED
            RUNNING / PAUSED    -> PENDING
            404 / 其他          -> UNKNOWN

        Args:
            workflow_id: 工作流实例 ID。

        Returns:
            ApprovalStatus 审批状态枚举。
        """
        try:
            summary = await self.get_workflow_status(workflow_id)
        except BizClientError:
            return ApprovalStatus.UNKNOWN
        status = str((summary or {}).get("status", "")).upper()
        if status == "COMPLETED":
            return ApprovalStatus.APPROVED
        if status in {"TERMINATED", "FAILED", "TIMED_OUT"}:
            return ApprovalStatus.REJECTED  # 终止/失败/超时均视为未获批准（安全兜底）
        if status in {"RUNNING", "PAUSED"}:
            return ApprovalStatus.PENDING
        return ApprovalStatus.UNKNOWN

    async def ensure_workflow_registered(self, workflow_name: str) -> bool:
        """确保审批工作流已注册到 Conductor（幂等：已存在则跳过注册）。

        Args:
            workflow_name: 工作流名（同时作为 definitions/ 目录下的文件名，不含 .json 后缀）。

        Raises:
            FileNotFoundError: 工作流定义文件不存在。
        """
        def_path = _DEFINITIONS_DIR / f"{workflow_name}.json"
        if not def_path.exists():
            raise FileNotFoundError(f"工作流定义文件不存在: {def_path}")
        definition = json.loads(def_path.read_text(encoding="utf-8"))
        name = str(definition.get("name", workflow_name))
        version = int(definition.get("version", 1))

        # 已注册（200）直接返回；404 视为未注册继续
        try:
            await self._request(
                "GET", f"/api/metadata/workflow/{name}", params={"version": version}
            )
            logger.info("BPM 工作流已存在，跳过注册", extra={"workflow": name, "version": version})
            return True
        except BizClientError:
            pass

        try:
            await self._request("POST", "/api/metadata/workflow", json_body=definition)
        except BizClientError:
            # 兼容仅支持批量注册接口的 Conductor 版本：单对象失败时按数组重试
            await self._request("POST", "/api/metadata/workflow", json_body=[definition])
        logger.info("BPM 工作流注册成功", extra={"workflow": name, "version": version})
        return True


def get_conductor_client() -> ConductorClient:
    """构建 Conductor 客户端（按需创建，便于测试替换）。"""
    return ConductorClient()
