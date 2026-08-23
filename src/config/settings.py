"""统一配置加载：全部来自环境变量（.env / docker-compose env_file），禁止硬编码密钥与地址。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """平台全局配置项（字段名与环境变量名一一对应，大小写不敏感）。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ===== 运行环境 =====
    app_env: str = "dev"          # dev / test / prod
    log_level: str = "INFO"

    # ===== 服务端口（容器内端口，宿主机映射见 docker-compose.yml）=====
    agent_port: int = 8100
    mcp_gateway_port: int = 8101

    # ===== LLM =====
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # ===== MCP 网关（Agent 通过容器名访问，见 Docker 规范 5.1）=====
    mcp_gateway_url: str = "http://mcp-gateway:8101/mcp"

    # ===== Conductor BPM =====
    conductor_base_url: str = "http://conductor-server:8080"
    conductor_purchase_workflow: str = "purchase_approval"

    # ===== 业务底座（诊所系统）=====
    clinic_api_base: str = "http://nautilus-clinic:8087"
    clinic_api_token: str = ""

    # ===== 业务规则（企业可配置，禁止硬编码）=====
    inventory_safety_threshold: float = 10.0   # 库存安全水位：低于此值判定缺货并触发采购建议
    purchase_default_supplier: str = ""        # 默认供应商（为空则要求用户指令提供，不再写死演示值）
    inventory_list_path: str = "/clinic/agent/inventory"          # 库存查询接口路径（业务底座Agent视图）
    purchase_order_path: str = "/clinic/agent/purchase/order"     # 采购下单接口路径（对接真实ERP时替换）
    dispense_path: str = "/clinic/consultation/dispense"         # 发药接口路径

    # ===== 稳定性：熔断 / 幂等 =====
    breaker_failure_threshold: int = 5         # 连续失败 N 次触发熔断
    breaker_recovery_seconds: float = 30.0     # 熔断冷却时长（半开探测间隔）
    idempotency_enabled: bool = True           # 写操作幂等防重开关

    # ===== API 安全 =====
    api_auth_enabled: bool = False             # X-API-Key 校验（服务间调用场景）
    api_auth_key: str = ""                     # API Key（生产走密钥管理服务注入）
    auth_enabled: bool = False                 # P2 用户认证：/chat 与 /auth 需要 JWT（生产开启）
    auth_jwt_secret: str = "nautilus-dev-jwt-secret-change-me-32b"  # JWT 签名密钥（生产必须替换）

    # ===== 数据库（Agent 状态 / 审计日志）=====
    database_url: str = "postgresql+asyncpg://nautilus:change-me@postgres:5432/nautilus_agent"

    # ===== Redis（可选，预留）=====
    redis_url: str = "redis://redis:6379/0"


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例（进程内缓存）。"""
    return Settings()
