# SQL 脚本来源分类（发布前整理用）

> 说明：便于区分「框架模板 DDL」与「本项目业务/运维脚本」。若建库流程有变化，以实际部署文档为准。

## A. 框架 / 中间件初始化（模板遗留，与具体门诊业务无直接对应）

| 文件 | 说明 |
|------|------|
| `ruoyi-mysql.sql` / `ruoyi-pgsql.sql` / `ruoyi-highgo.sql` / `ruoyi-gauss.sql` | 若依基架库表与基础数据（多数据库方言）。新建环境通常需要其一。 |
| `auto-increment-gauss.sql` / `auto-increment-pgsql-highgo.sql` | 部分方言下的自增/序列补偿脚本。 |
| `magic-api-mysql.sql` / `magic-api-pgsql.sql` | Magic-API 相关表结构。是否启用取决于是否使用 Magic-API。 |

## B. 本项目增量 / 业务相关（建议保留并随功能演进）

| 文件 | 说明 |
|------|------|
| `add_inventory_batch_expiry.sql` | 库存批次、效期等业务字段或表调整。 |
| `add_workstation_menu.sql` | 工位等功能菜单初始化（含 `sys_menu` 插入）。 |

## 前端展示（已实现）

- 侧边栏动态菜单在 `ruoyi-ui/src/store/modules/permission.js` 中会过滤掉 `path === 'tool'` 的根菜单（系统工具：表单构建、代码生成等）。若需恢复展示，删除该过滤逻辑即可。
- 顶栏已移除「源码 / 帮助」外链图标，避免模板感入口。

## C. 候选后续动作（不在本阶段执行）

- 将 A 类脚本择机移至 `docs/reference/` 或子模块文档，仅当团队约定「仓库内不再保留完整基架 DDL」时再做。
- **ruoyi-generator 模块**：模板自带代码生成器；当前不物理删除，若确认不再使用可列为「模块移除候选」，另开任务处理。

## D. 需要人工确认

- 生产/演示环境实际使用的是 **哪一份** 基架 DDL（PostgreSQL / MySQL / 其他）以及与 `add_*.sql` 的执行顺序。
- `magic-api-*.sql` 是否在生产启用；未启用时可不执行，避免冗余表。
