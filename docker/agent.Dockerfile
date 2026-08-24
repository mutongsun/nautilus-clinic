# ===== Agent 服务镜像（python:3.11-slim，依赖层/代码层分离，禁止 latest）=====
FROM python:3.11-slim

# 镜像源可选注入（默认官方源，海外 CI 可用；国内本地构建经 .env 传 build-arg 加速：
#   APT_MIRROR=mirrors.tuna.tsinghua.edu.cn
#   PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple）
ARG APT_MIRROR=""
ARG PIP_INDEX_URL=""

# ① 系统依赖层（curl 供健康检查使用）
RUN if [ -n "${APT_MIRROR}" ]; then \
        sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources || true; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ② Python 依赖层（仅 requirements.txt 变动时重建，提升缓存命中）
COPY requirements.txt .
RUN if [ -n "${PIP_INDEX_URL}" ]; then \
        pip install --no-cache-dir -i ${PIP_INDEX_URL} -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# ③ 代码层（日常改动只重建此层；开发模式被 volume 挂载覆盖实现热生效）
COPY . /app/src

# ④ 非 root 运行（安全基线）
RUN useradd -m appuser && chown -R appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8100

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8100"]
