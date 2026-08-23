"""MCP 网关数据模型：调用上下文与各工具入参结构化校验。"""

from pydantic import BaseModel, Field

from src.services.clinic_client import PurchaseItem


class ToolContext(BaseModel):
    """工具调用上下文（Agent 每次调用必须显式携带，网关据此鉴权与审计）。

    将上下文作为显式参数而非 HTTP 头传递，保证传输协议无关、易于校验与测试。
    """

    user_id: str = Field(min_length=1, description="发起请求的用户ID")
    agent_role: str = Field(min_length=1, description="调用方Agent角色（PyCasbin 权限主体）")
    trace_id: str = Field(min_length=1, description="任务链路ID，多Agent协作全程相同")
    user_instruction: str = Field(default="", description="触发本次调用的用户原始指令")
    bpm_workflow_id: str | None = Field(default=None, description="关联BPM流程ID，高风险写操作必填")
    idempotency_key: str | None = Field(default=None, max_length=160,
                                        description="幂等键：写操作防重复执行（同键成功记录直接复用）")
    client_ip: str | None = Field(default=None, max_length=64, description="调用来源IP（审计溯源）")


class InventoryQueryIn(BaseModel):
    """库存查询入参（只读）。"""

    medicine_name: str = Field(default="", description="药品名称（模糊匹配），为空查全部")


class PatientQueryIn(BaseModel):
    """患者档案查询入参（只读）。"""

    patient_name: str = Field(min_length=1, description="患者姓名关键词")


class ApprovalStartIn(BaseModel):
    """发起采购审批入参。"""

    title: str = Field(min_length=1, description="申请标题")
    applicant: str = Field(default="", description="申请人（默认取上下文 user_id）")
    items: list[PurchaseItem] = Field(default_factory=list, description="采购明细")
    remark: str = Field(default="", description="申请备注")


class ApprovalStatusIn(BaseModel):
    """审批状态查询入参（只读）。"""

    workflow_id: str = Field(min_length=1, description="Conductor 工作流实例ID")


class PurchaseOrderCreateIn(BaseModel):
    """采购订单创建入参（高风险写）。"""

    supplier: str = Field(min_length=1, description="供应商")
    items: list[PurchaseItem] = Field(min_length=1, description="采购明细")
    remark: str = Field(default="", description="备注")


class DispenseIn(BaseModel):
    """发药入参（高风险写）。"""

    consultation_id: str = Field(min_length=1, description="就诊记录ID")
