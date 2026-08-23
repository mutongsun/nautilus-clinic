"""FastMCP 网关服务：注册全部工具 + 健康检查路由。"""

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from src.mcp_gateway.registry import get_registered_tools


def create_mcp() -> FastMCP:
    """构建 MCP 网关实例并挂载全部已注册工具。"""
    mcp = FastMCP(name="nautilus-mcp-gateway")

    # 导入 tools 模块触发 @mcp_tool 注册（幂等，重复导入无副作用）
    import src.mcp_gateway.tools  # noqa: F401

    # 注册表结构：{工具名: (ToolSpec, 包装函数)}，注意解包层级
    for _tool_name, (spec, fn) in get_registered_tools().items():
        mcp.tool(name=spec.name, description=spec.description)(fn)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> PlainTextResponse:
        """网关健康检查端点（docker-compose healthcheck 探测目标）。"""
        return PlainTextResponse("ok")

    return mcp
