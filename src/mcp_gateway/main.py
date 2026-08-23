"""MCP 网关服务启动入口（容器内端口 8101，唯一实例化处）。

启动顺序：初始化审计表 -> 启动 FastMCP（HTTP 传输，路径 /mcp）。
"""

import asyncio

from fastmcp import FastMCP

from src.common.logging import get_logger, setup_logging
from src.config.settings import get_settings
from src.db.engine import init_db
from src.mcp_gateway.server import create_mcp

logger = get_logger(__name__)


def main() -> None:
    """网关服务主入口。"""
    settings = get_settings()
    setup_logging(settings.log_level)

    async def _prestart() -> None:
        """启动前置：审计日志表初始化 + BPM 审批工作流注册（失败仅告警，不阻断网关启动）。"""
        try:
            await init_db()
        except Exception:  # noqa: BLE001
            logger.exception("审计表初始化失败（将继续以JSON日志兜底启动）")

        # Conductor 冷启动较慢，有限次重试注册审批工作流（定义见 src/workflow/definitions/）
        # CI/编排环境中 mock 与网关常被并行重启：窗口须覆盖下游就绪延迟
        from src.workflow.conductor import get_conductor_client

        for attempt in range(1, 7):
            try:
                await get_conductor_client().ensure_workflow_registered(
                    settings.conductor_purchase_workflow
                )
                break
            except Exception:  # noqa: BLE001
                if attempt == 6:
                    logger.exception("BPM 工作流注册失败（网关仍将启动，可手动重试）")
                else:
                    await asyncio.sleep(5)

    asyncio.run(_prestart())

    mcp: FastMCP = create_mcp()
    logger.info(
        "MCP 网关启动",
        extra={"port": settings.mcp_gateway_port, "endpoint": "/mcp"},
    )
    mcp.run(transport="http", host="0.0.0.0", port=settings.mcp_gateway_port)


if __name__ == "__main__":
    main()
