#!/bin/bash
# 初始化多数据库：Agent 平台库由 POSTGRES_DB 默认创建，此处补建诊所业务库
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE nautilus_clinic;
EOSQL
echo "01-init.sh: 数据库 nautilus_clinic 创建完成"
