# ===== MCP 网关服务镜像（与 Agent 镜像同源构建上下文，仅启动命令不同）=====
FROM python:3.11-slim

# 镜像源可选注入（默认官方源，海外 CI 可用；国内本地构建经 .env 传 build-arg 加速）
ARG APT_MIRROR=""
ARG PIP_INDEX_URL=""

RUN if [ -n "${APT_MIRROR}" ]; then \
        sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources || true; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN if [ -n "${PIP_INDEX_URL}" ]; then \
        pip install --no-cache-dir -i ${PIP_INDEX_URL} -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . /app/src

RUN useradd -m appuser && chown -R appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8101

# FastMCP HTTP 传输，服务路径 /mcp；策略文件随 src/mcp_gateway/policy 一并打入镜像
CMD ["python", "-m", "src.mcp_gateway.main"]
