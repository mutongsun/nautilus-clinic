"""MCP 网关工具集：全部业务工具在此声明风险等级并注册。

分层红线（开发规范 2.2）：工具内只做协议转发与结构化校验，
业务规则（库存校验、过敏拦截、事务）全部由诊所业务底座执行。
"""

from src.common.constants import AgentRole, ToolRiskLevel
from src.config.settings import get_settings
from src.mcp_gateway.decorator import mcp_tool
from src.mcp_gateway.schemas import (
    ApprovalStartIn,
    ApprovalStatusIn,
    DispenseIn,
    InventoryQueryIn,
    PatientQueryIn,
    PurchaseOrderCreateIn,
    ToolContext,
)
from src.services.clinic_client import (
    PurchaseOrderIn,
    get_clinic_client,
)
from src.workflow.conductor import get_conductor_client


@mcp_tool(
    name="query_inventory",
    description="查询诊所药品实时库存（只读），支持名称模糊匹配",
    risk_level=ToolRiskLevel.LOW,
    required_roles={AgentRole.QUERY.value, AgentRole.OPERATOR.value},
)
async def query_inventory(params: dict, context: ToolContext) -> dict:
    """查询药品库存（LOW 只读工具）。

    Args:
        params: InventoryQueryIn 结构，medicine_name 为空查全部。
        context: 网关调用上下文（已由装饰器校验）。

    Returns:
        {"items": [库存明细...], "count": 数量}
    """
    query = InventoryQueryIn.model_validate(params)
    items = await get_clinic_client().query_inventory(query.medicine_name)
    return {"items": [i.model_dump() for i in items], "count": len(items)}


@mcp_tool(
    name="query_patient",
    description="按姓名模糊查询患者档案（只读，含过敏史等动态档案）",
    risk_level=ToolRiskLevel.LOW,
    required_roles={AgentRole.QUERY.value, AgentRole.OPERATOR.value},
)
async def query_patient(params: dict, context: ToolContext) -> dict:
    """查询患者档案（LOW 只读工具）。"""
    query = PatientQueryIn.model_validate(params)
    patients = await get_clinic_client().query_patient(query.patient_name)
    return {"patients": [p.model_dump() for p in patients], "count": len(patients)}


@mcp_tool(
    name="start_purchase_approval",
    description="发起药品采购审批流程（Conductor BPM），返回流程ID供人工审批",
    risk_level=ToolRiskLevel.MEDIUM,
    required_roles={AgentRole.APPROVAL.value},
)
async def start_purchase_approval(params: dict, context: ToolContext) -> dict:
    """发起采购审批（MEDIUM：创建审批单，可撤销，非业务数据写入）。

    Returns:
        {"workflow_id": 流程ID, "status": "PENDING"}
    """
    payload = ApprovalStartIn.model_validate(params)
    workflow_id = await get_conductor_client().start_workflow(
        workflow_name=get_settings().conductor_purchase_workflow,
        correlation_id=context.trace_id,
        payload={
            "title": payload.title,
            "applicant": payload.applicant or context.user_id,
            "items": [i.model_dump() for i in payload.items],
            "remark": payload.remark,
        },
    )
    return {"workflow_id": workflow_id, "status": "PENDING"}


@mcp_tool(
    name="query_approval_status",
    description="查询采购审批流程当前状态（只读）",
    risk_level=ToolRiskLevel.LOW,
    required_roles={AgentRole.APPROVAL.value, AgentRole.OPERATOR.value},
)
async def query_approval_status(params: dict, context: ToolContext) -> dict:
    """查询审批状态（LOW 只读）。"""
    query = ApprovalStatusIn.model_validate(params)
    status = await get_conductor_client().is_approved(query.workflow_id)
    return {"workflow_id": query.workflow_id, "status": status.value}


@mcp_tool(
    name="create_purchase_order",
    description="创建药品采购订单（高风险写操作，须BPM审批通过后执行）",
    risk_level=ToolRiskLevel.HIGH,
    required_roles={AgentRole.OPERATOR.value},
    bpm_required=True,
)
async def create_purchase_order(params: dict, context: ToolContext) -> dict:
    """创建采购订单（HIGH：强制 BPM 审批通过，装饰器已二次校验 Conductor 实际状态）。"""
    payload = PurchaseOrderCreateIn.model_validate(params)
    result = await get_clinic_client().create_purchase_order(
        PurchaseOrderIn(
            supplier=payload.supplier,
            items=payload.items,
            # 幂等键透传业务底座：下游唯一索引兜底，端到端双层防重
            idempotency_key=context.idempotency_key,
            remark=payload.remark or context.user_instruction[:200],
        )
    )
    return result.model_dump()


@mcp_tool(
    name="dispense_prescription",
    description="发药并核减库存（高风险写操作，须BPM审批通过后执行）",
    risk_level=ToolRiskLevel.HIGH,
    required_roles={AgentRole.OPERATOR.value},
    bpm_required=True,
)
async def dispense_prescription(params: dict, context: ToolContext) -> dict:
    """发药核减库存（HIGH：强制 BPM 审批通过）。"""
    payload = DispenseIn.model_validate(params)
    return await get_clinic_client().dispense_prescription(payload.consultation_id)
