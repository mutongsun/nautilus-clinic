#!/bin/bash
# 导入诊所业务底座表结构（挂载于 /clinic-sql 的 sql/*.sql，目录为空则跳过）
# 执行顺序：RuoYi 系统表 -> Magic API -> 其他业务脚本（按文件名排序）
set -e

if ! ls /clinic-sql/*.sql >/dev/null 2>&1; then
    echo "02-clinic-schema.sh: /clinic-sql 无 SQL 脚本，跳过诊所表结构导入"
    exit 0
fi

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d nautilus_clinic -c "CREATE SCHEMA IF NOT EXISTS ruoyi;"

for f in /clinic-sql/ruoyi-pgsql.sql \
         /clinic-sql/magic-api-pgsql.sql \
         /clinic-sql/region-pgsql.sql \
         /clinic-sql/clinic-pgsql.sql; do
    if [ -f "$f" ]; then
        echo "02-clinic-schema.sh: 导入 $f"
        psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d nautilus_clinic -f "$f" || {
            echo "02-clinic-schema.sh: $f 导入失败（含 IF NOT EXISTS 兼容问题则可忽略）"
        }
    fi
done
echo "02-clinic-schema.sh: 诊所表结构导入完成"
