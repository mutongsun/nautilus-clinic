# Docker 容器化开发规范

> 适用范围：本项目全部服务的本地开发环境。本规范为**强制规范**，所有服务必须容器化，禁止裸机启动（业务底座单独调试除外，见 [docs/CLINIC.md](./CLINIC.md)）。

---

## 目录

- [1. 规范目标](#1-规范目标)
- [2. 容器化服务清单](#2-容器化服务清单)
- [3. 镜像规范](#3-镜像规范)
- [4. 本地开发规范](#4-本地开发规范)
- [5. 网络规范](#5-网络规范)
- [6. 数据持久化规范](#6-数据持久化规范)
- [7. 启动规范（唯一启动方式）](#7-启动规范唯一启动方式)
- [8. 开发、测试、环境隔离规范](#8-开发测试环境隔离规范)

---

## 1. 规范目标

解决本地环境不一致、依赖混乱、服务启动复杂问题，实现**一次构建、随处运行**，完全对标互联网公司本地开发流程：

- 新成员 clone 代码后，`docker-compose up -d` 一条命令即可拉起全部服务；
- 本地零依赖：不需要安装 Python/JDK/Node/PostgreSQL；
- 环境强制一致：所有人使用相同版本的基础镜像与依赖锁定文件；
- 配置与代码分离：环境变量统一托管 `.env`，一套编排多环境复用。

---

## 2. 容器化服务清单

本项目所有组件全部容器化：

| 分类 | 服务 | 说明 |
|---|---|---|
| 平台核心 | Agent 服务 | FastAPI + LangGraph（多智能体编排） |
| 平台核心 | MCP 网关服务 | FastMCP + PyCasbin 权限/审计 |
| 平台核心 | Conductor BPM | Netflix Conductor-OSS 工作流审批引擎 |
| 平台核心 | PostgreSQL | 统一数据存储（Agent 状态/审计日志/业务数据） |
| 平台核心 | Redis | 缓存 / 会话（可选） |
| 业务底座 | Nautilus Clinic | 诊所管理系统（Spring Boot 3 后端 + Vue 3 前端） |
| 扩展底座（可选） | JSH-ERP | 进销存业务系统 |
| 扩展底座（可选） | NocoBase | 通用业务中台 |

---

## 3. 镜像规范

### 3.1 基础镜像

- Python 服务统一使用 **`python:3.11-slim`** 基础镜像，轻量安全；
- Java 业务底座统一使用固定 tag 的 JRE 镜像（如 `eclipse-temurin:21-jre-jammy`）；
- **禁止使用 `latest` 标签**，全部固定版本号（含依赖锁定：`requirements.txt` 精确到版本、`package-lock.json` / `pnpm-lock.yaml` 提交入库）。

### 3.2 Dockerfile 分层优化

依赖层、代码层分离，代码改动不触发依赖重装，提升构建速度与缓存命中率：

```dockerfile
# ---------- Agent 服务 Dockerfile 示例 ----------
FROM python:3.11-slim

# ① 系统依赖层（变动极少）
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ② Python 依赖层（仅 requirements.txt 变动时重建）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ③ 代码层（日常改动只重建此层）
COPY src/ ./src/

# ④ 运行配置
ENV PYTHONUNBUFFERED=1
EXPOSE 8100
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8100"]
```

### 3.3 其他要求

- 镜像内**禁止打包任何密钥**（构建时通过 `--build-arg` + `.env` 注入，或运行时注入）；
- `.dockerignore` 必须排除 `.git`、`node_modules`、`__pycache__`、`.env`、`*.sql dump`；
- 生产镜像基于多阶段构建，最终镜像不包含构建工具链。

---

## 4. 本地开发规范

### 4.1 零本地依赖

- **本地不安装任何项目依赖**，全部在容器内运行；
- 本地只需安装：Docker（20.10+）、Docker Compose（v2+）、Git、IDE。

### 4.2 代码挂载热生效

代码目录挂载到容器，实现**本地修改、容器热生效**：

```yaml
# docker-compose.yml（开发模式）节选
services:
  agent-service:
    build: ./docker/agent
    volumes:
      - ./src:/app/src          # 代码挂载：本地改代码，容器内立即生效
      - ./cli:/app/cli
    env_file: .env
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8100 --reload  # 热重载
```

常用开发命令：

```bash
docker-compose up -d                          # 启动全部服务
docker-compose logs -f agent-service          # 跟踪某服务日志
docker-compose exec agent-service pytest      # 容器内跑单测（本地无需装 pytest）
docker-compose restart mcp-gateway            # 重启单个服务
docker-compose down                           # 停止并移除容器（数据卷保留）
```

### 4.3 环境变量统一托管

- 环境变量统一托管 **`.env` 文件**，`docker-compose.yml` 通过 `env_file` 引用；
- **禁止硬编码密钥、地址**（数据库密码、LLM API Key、JWT Secret 等）；
- 仓库只提交 `.env.example` 模板，`.env` 一律加入 `.gitignore`：

```bash
# .env.example 示例（提交入库的模板）
POSTGRES_VERSION=16
POSTGRES_PASSWORD=change-me
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.example.com/v1
AGENT_PORT=8100
MCP_GATEWAY_PORT=8101
```

---

## 5. 网络规范

### 5.1 统一网络

所有服务加入统一 docker network，**服务间使用容器名通信**（不写 IP、不写 localhost）：

```yaml
networks:
  nautilus-net:
    driver: bridge
```

```python
# 服务间调用一律使用容器名作为主机名
CLINIC_API_BASE = "http://nautilus-clinic:8087"   # ✅ 容器名通信
# 禁止: "http://localhost:8087"                   # ❌ 容器内 localhost 指向自身
```

### 5.2 端口统一规划（避免冲突）

| 服务 | 宿主机端口 | 容器端口 | 对外暴露 |
|---|---|---|---|
| Agent 服务（FastAPI） | `8100` | `8100` | 是 |
| MCP 网关（FastMCP） | `8101` | `8101` | 是 |
| Conductor UI | `5000` | `5000` | 是 |
| Conductor Server | — | `8080` | 否（仅内网） |
| 诊所系统后端 | `8087` | `8087` | 是 |
| 诊所系统前端 | `8090` | `80` | 是 |
| PostgreSQL | `5432` | `5432` | 是（开发期） |
| Redis | `6379` | `6379` | 否（仅内网） |
| JSH-ERP（可选） | `8091` | `8091` | 是 |
| NocoBase（可选） | `8092` | `8092` | 是 |

### 5.2.1 业务底座双模式（Mock / 真实 Java）

| 模式 | 启动命令 | 说明 |
|---|---|---|
| Mock 模式（默认演示） | `docker compose --profile mock up -d` | `mock-backend` 以网络别名顶替 `conductor-server`（及未启动真实诊所时的演示诊所） |
| 真实模式 | `docker compose --profile mock up -d --force-recreate mock-backend` + `docker compose --profile clinic up -d --build nautilus-clinic` | 真实 Java 诊所系统（RuoYi）提供库存查询与采购下单（PostgreSQL 落库 + `idempotency_key` 唯一索引下游幂等）；mock 仅保留 Conductor BPM 模拟 |

> 真实模式注意事项：① mock 必须以新配置重建（诊所别名已摘除，避免 DNS 冲突）；② 真实诊所依赖 `nautilus_clinic` 库（initdb 自动初始化，存量卷需手动导入 `sql/clinic-pgsql.sql`）；③ 首次构建需拉取 Maven 依赖（已配置阿里云镜像源）。

### 5.2.2 HTTPS（--profile tls）

P2 提供自签证书 TLS 反代（生产替换为正式证书或云 LB）：

```bash
# ① 生成自签证书（推荐容器内生成，规避 Windows openssl 缺配置问题；certs 目录已 gitignore）
docker run --rm -v "${PWD}/docker/nginx/certs:/certs" python:3.11-slim \
  sh -c "openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /certs/server.key -out /certs/server.crt -subj '/CN=localhost' \
  -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'"

# ② 启动并验证
docker compose --profile tls up -d --no-deps tls-proxy
curl -sk https://localhost:8443/health   # 自签证书需 -k（生产正式证书免此参数）
```

配置要点：TLSv1.2/1.3、HSTS/nosniff/DENY 安全响应头、`X-Forwarded-For` 透传真实 client_ip 供审计溯源、300s 读超时兜底长任务。

> 端口规划以 `docker-compose.yml` 为唯一事实来源；新增服务必须先在本文档登记端口，防止冲突。

---

## 6. 数据持久化规范

- 数据库、业务数据**全部挂载 volume 持久化**，容器删除不丢失业务数据：

```yaml
volumes:
  pg-data:          # PostgreSQL 数据
  redis-data:       # Redis 持久化
  conductor-data:   # Conductor 工作流/任务数据
  clinic-uploads:   # 业务底座附件
  nocobase-data:    # NocoBase 数据（启用时）

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pg-data:/var/lib/postgresql/data
      - ./sql:/docker-entrypoint-initdb.d   # 首次启动自动初始化表结构
```

- 命名卷（named volume）优先于绑定挂载存放数据；代码目录才使用绑定挂载；
- `docker-compose down` 不删数据卷；确需清库重置使用 `docker-compose down -v`（**危险操作，仅本地开发允许**）。

---

## 7. 启动规范（唯一启动方式）

本地开发统一命令：

```bash
docker-compose up -d
```

- **禁止**绕过编排单独 `docker run` 启动项目服务；
- **禁止**用裸机进程替代容器启动（业务底座单独调试场景见 [docs/CLINIC.md](./CLINIC.md)，调试完必须回到容器环境验证）；
- 所有服务启动必须配置**健康检查**，异常**自动重启**：

```yaml
services:
  agent-service:
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s

  postgres:
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

- 服务间依赖必须声明 `depends_on: condition: service_healthy`，保证启动顺序（如 Agent 依赖 MCP 网关与 PostgreSQL 健康）。

---

## 8. 开发、测试、环境隔离规范

- **本地开发环境**：统一使用 `docker-compose.yml`（默认 dev 模式：代码挂载 + 热重载 + 调试日志）；
- **禁止开发环境连接测试/生产数据**：数据库、业务系统地址一律从 `.env` 读取并按环境隔离，CI 中校验开发配置不得出现测试/生产网段与凭据；
- 环境文件按需拆分：`.env.dev` / `.env.test` / `.env.prod`，提交模板不提交实文件；
- 所有服务启动健康检查，异常自动重启（`restart: unless-stopped`）；
- 生产部署使用独立的 `docker-compose.prod.yml`（override）：关闭代码挂载与 `--reload`、使用构建镜像 + 固定 tag、日志落盘轮转。

---

## 附：常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| 服务间调用 `Connection refused` | 使用了 `localhost` 访问其他服务 | 改用容器名通信（见 [5.1](#51-统一网络)） |
| 改了代码容器内不生效 | 挂载未生效或未开热重载 | 确认 `volumes` 挂载 + `--reload`；仍无效则 `docker-compose restart <svc>` |
| 首次启动表结构为空 | 未挂载初始化 SQL | 确认 `./sql` 挂载到 `/docker-entrypoint-initdb.d`（仅首次建卷生效） |
| 端口冲突 | 宿主机端口被占用 | 按端口规划表调整，并同步更新本文档 |
| 容器反复重启 | 健康检查失败 | `docker-compose logs <svc>` 查看失败原因，修复后自动恢复 |
| Conductor 镜像拉取被拒（not in the allowlist） | 国内镜像加速器（如 DaoCloud）仅代理白名单内的 docker.io 镜像 | 在 Docker Engine 配置中为 `conductoross/*` 配置直连或其他加速器；或在能直连的环境 `docker pull` 后导入 |
| 构建时 apt/pip 极慢 | 容器内直连 debian/PyPI 官源 | Dockerfile 已内置清华镜像源，可通过 `--build-arg PIP_INDEX_URL` / `APT_MIRROR` 覆盖 |
| 基础镜像个别层拉取卡死（同字节数停滞） | 加速器对特定二进制内容连接重置 | 换镜像域直拉再重 tag：`docker pull dockerproxy.net/library/<image>` 后 `docker tag` 为标准名 |
| mock/真实底座切换后仍打到旧服务 | 网关 httpx 长连接复用旧容器 IP，且 mcp-gateway 无 `--reload` | 切换底座后必须 `docker compose restart mcp-gateway`（重置连接池与代码） |
| 幂等验证"没发请求就成功" | 网关幂等缓存持久在审计表，固定测试键命中历史 SUCCESS | 验证脚本使用每次随机的幂等键（uuid 后缀） |
