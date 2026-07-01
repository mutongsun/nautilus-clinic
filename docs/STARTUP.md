# Nautilus Clinic 本地启动指南

> 项目路径：`/Users/yang/Workspace/SelfProject/nautilus-clinic`
> 最后更新：2026-07-01

## 环境

| 依赖 | 来源 | 端口 | 凭据 |
|------|------|------|------|
| PostgreSQL 16 | Docker `rag-nexus-pg` | `5433` | `postgres` / `postgres` |
| Redis 7 | Docker `redis-local` | `6379` | 密码 `local_dev_only` |
| Java 21 | mise 管理 | — | — |
| Node 24 | mise 管理 | — | — |

## 前置条件（一次性）

```bash
# 1. 启动 Docker 容器
docker start rag-nexus-pg redis-local

# 2. 创建数据库（若未创建）
docker exec -i rag-nexus-pg psql -U postgres -c "CREATE DATABASE nautilus_clinic;"

# 3. 创建 schema + 导入表结构（若未导入）
docker exec -i rag-nexus-pg psql -U postgres -d nautilus_clinic -c "CREATE SCHEMA IF NOT EXISTS ruoyi;"
docker exec -i rag-nexus-pg psql -U postgres -d nautilus_clinic -f - < sql/ruoyi-pgsql.sql

# 4. 安装所有模块到本地 Maven 仓库（代码有改动后需重跑）
mvn install -DskipTests

# 5. 修前端 bin 权限（仅首次，macOS 常见问题）
chmod +x ruoyi-ui/node_modules/.bin/*
```

## 日常启动

```bash
# 1. 确保 Docker 容器运行中
docker start rag-nexus-pg redis-local

# 2. 启动后端（端口 8087）
cd ruoyi-admin
mvn spring-boot:run -Dspring.profiles.active=devpg

# 3. 新终端，启动前端（端口 8080）
cd ruoyi-ui
npm run dev -- --port 8080
```

## 连线验证

```bash
# 后端
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:8087/

# 前端
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:8080/
```

## 登录

| 项目 | 值 |
|------|-----|
| 地址 | `http://localhost:8080` |
| 账号 | `admin` |
| 密码 | `admin123` |
| 验证码 | 数学计算型（可通过 DB `sys_config` 表关闭） |

## 配置文件

- 后端主配置：`ruoyi-admin/src/main/resources/application.yml`
- 后端环境配置：`ruoyi-admin/src/main/resources/application-devpg.yml`
- 前端开发配置：`ruoyi-ui/.env.development`
- Webpack dev server：`ruoyi-ui/vue.config.js`

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `vue-cli-service: Permission denied` | macOS 下 node_modules bin 无执行权限 | `chmod +x ruoyi-ui/node_modules/.bin/*` |
| Redis 连接拒绝 | Docker 容器未启动 | `docker start redis-local` |
| 验证码已失效 | 验证码开了但没传 | DB 关掉：`UPDATE ruoyi.sys_config SET config_value='false' WHERE config_key='sys.account.captchaEnabled';` |
| 模块找不到 | 没 `mvn install` | `mvn install -DskipTests` |
| 端口被占用 | 上次进程未杀 | `lsof -ti:8087 \| xargs kill -9` |
