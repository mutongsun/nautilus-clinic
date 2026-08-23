# ===== MCP 网关服务镜像（与 Agent 镜像同源构建上下文，仅启动命令不同）=====
FROM python:3.11-slim

# 镜像源可通过 build-arg 覆盖（海外构建：--build-arg PIP_INDEX_URL=https://pypi.org/simple）
ARG APT_MIRROR=mirrors.tuna.tsinghua.edu.cn
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources || true \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} -r requirements.txt

COPY . /app/src

RUN useradd -m appuser && chown -R appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8101

# FastMCP HTTP 传输，服务路径 /mcp；策略文件随 src/mcp_gateway/policy 一并打入镜像
CMD ["python", "-m", "src.mcp_gateway.main"]
