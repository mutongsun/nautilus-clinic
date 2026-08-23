"""诊所业务底座（Nautilus Clinic）API 客户端。

只封装协议细节（地址、鉴权、响应结构），不写业务规则——
库存校验、过敏拦截、处方规则等全部下沉在诊所系统内部（分层职责边界，见开发规范 1.1）。
"""

from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.services.base_client import BaseHttpClient


# ---------- 数据模型（出入参结构化校验） ----------

class InventoryItem(BaseModel):
    """药品库存明细（诊所系统 /clinic/inventory/list 返回行）。"""

    medicine_name: str = Field(alias="medicineName", description="药品名称")
    spec: str = Field(default="", description="规格")
    unit: str = Field(default="", description="单位")
    stock_qty: float = Field(default=0, alias="quantity", description="当前库存量")
    unit_price: float = Field(default=0, alias="salePrice", description="售价")
    attributes: dict[str, Any] = Field(default_factory=dict, description="扩展属性（批号/效期等）")

    model_config = {"populate_by_name": True}


class PatientBrief(BaseModel):
    """患者摘要信息（诊所系统 /clinic/patient/list 返回行）。"""

    patient_id: str = Field(alias="patientId", description="患者ID")
    patient_name: str = Field(alias="patientName", description="患者姓名")
    gender: str = Field(default="", description="性别")
    dynamic_profile: dict[str, Any] = Field(default_factory=dict, description="动态档案（过敏史/标签等）")

    model_config = {"populate_by_name": True}


class PurchaseItem(BaseModel):
    """采购单行项目（alias 对齐业务底座 Java DTO 驼峰契约）。"""

    medicine_name: str = Field(min_length=1, alias="medicineName", description="药品名称")
    quantity: float = Field(gt=0, description="采购数量")
    unit_price: float = Field(default=0, ge=0, alias="unitPrice", description="单价")

    model_config = {"populate_by_name": True}


class PurchaseOrderIn(BaseModel):
    """采购订单创建入参（alias 对齐业务底座 Java DTO 驼峰契约）。"""

    supplier: str = Field(min_length=1, description="供应商")
    items: list[PurchaseItem] = Field(min_length=1, description="采购明细")
    idempotency_key: str | None = Field(default=None, max_length=160, alias="idempotencyKey",
                                        description="幂等键：透传业务底座，下游唯一索引兜底（端到端双层幂等）")
    remark: str = Field(default="", description="备注")

    model_config = {"populate_by_name": True}


class OrderResult(BaseModel):
    """采购订单创建结果。"""

    order_id: str = Field(alias="orderId", description="订单号")
    status: str = Field(default="CREATED", description="订单状态")

    model_config = {"populate_by_name": True}


# ---------- 客户端 ----------

class ClinicClient(BaseHttpClient):
    """诊所系统 HTTP 客户端（继承超时 / 重试 / 异常转译能力）。"""

    def __init__(self) -> None:
        settings = get_settings()
        headers = {"Authorization": f"Bearer {settings.clinic_api_token}"} if settings.clinic_api_token else {}
        super().__init__(base_url=settings.clinic_api_base, timeout=5.0, headers=headers)

    async def query_inventory(self, medicine_name: str = "") -> list[InventoryItem]:
        """查询药品库存（只读，业务底座 Agent 视图接口）。

        Args:
            medicine_name: 药品名称（模糊匹配），为空表示查询全部。

        Returns:
            库存明细列表。
        """
        from src.config.settings import get_settings

        data = await self._request(
            "GET", get_settings().inventory_list_path,
            params={"medicineName": medicine_name} if medicine_name else None,
        )
        rows = (data or {}).get("rows", [])
        return [InventoryItem.model_validate(r) for r in rows]

    async def query_patient(self, patient_name: str) -> list[PatientBrief]:
        """按姓名模糊查询患者档案（只读，含 JSONB 动态档案）。

        Args:
            patient_name: 患者姓名关键词。

        Returns:
            患者摘要列表。
        """
        data = await self._request(
            "GET", "/clinic/patient/list", params={"patientName": patient_name}
        )
        rows = (data or {}).get("rows", [])
        return [PatientBrief.model_validate(r) for r in rows]

    async def create_purchase_order(self, order: PurchaseOrderIn) -> OrderResult:
        """创建采购订单（高风险写操作，仅允许在 BPM 审批通过后由网关调用）。

        接口路径经配置 PURCHASE_ORDER_PATH 管理：对接真实 ERP 时改配置即可，无需改代码。

        Args:
            order: 采购订单入参。

        Returns:
            订单创建结果（含下游返回的真实订单号，禁止本地生成伪造单号）。
        """
        from src.config.settings import get_settings

        data = await self._request(
            "POST", get_settings().purchase_order_path, json_body=order.model_dump(by_alias=True)
        )
        return OrderResult.model_validate(data)

    async def dispense_prescription(self, consultation_id: str) -> dict[str, Any]:
        """发药并核减库存（高风险写操作，接口路径经 DISPENSE_PATH 配置）。

        Args:
            consultation_id: 就诊记录 ID。

        Returns:
            发药结果（含核减后的库存信息）。
        """
        from src.config.settings import get_settings

        return await self._request(
            "POST", get_settings().dispense_path, json_body={"consultationId": consultation_id}
        )


@lru_cache
def get_clinic_client() -> ClinicClient:
    """获取诊所客户端单例（进程内复用连接池）。"""
    return ClinicClient()
