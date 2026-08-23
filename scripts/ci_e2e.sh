#!/usr/bin/env bash
# =============================================================================
# CI/本地共用 e2e 冒烟脚本：P2 全链路验证（认证/角色/异步/审批/落库）
#
# 前置条件（CI 由 e2e.yml 准备；本地手动执行前自行确认）：
#   - docker compose 栈已启动：postgres redis mock-backend mcp-gateway agent-service
#   - .env 已就绪（AUTH_ENABLED=true）
#   - agent-service 可达 http://localhost:8100，mock 控制端 http://localhost:9000
#
# 用法：bash scripts/ci_e2e.sh
#   退出码 0=全部通过；1=存在失败项（汇总表打印 PASS/FAIL）
# =============================================================================
set -u

# 目标地址可覆盖：CI 容器内跑时 MOCK_URL=http://mock-backend:9000（同网络容器名）
BASE="${BASE_URL:-http://localhost:8100}"
MOCK="${MOCK_URL:-http://localhost:9000}"
PASS=0; FAIL=0
declare -a RESULTS=()

report() { # report <PASS|FAIL> <用例名> <详情>
  RESULTS+=("$1|$2|$3")
  if [ "$1" = "PASS" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
  printf "  [%s] %-28s %s\n" "$1" "$2" "$3"
}

json_field() { # json_field <json串> <字段> —— 无 jq 环境的简易提取（取首次出现=顶层字段，避免贪婪匹配落入嵌套）
  printf '%s' "$1" | grep -o "\"$2\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -1 \
    | sed 's/.*"\([^"]*\)"$/\1/'
}

wait_task() { # wait_task <token> <task_id> <最长秒> —— 轮询至终态，echo 终态 JSON
  local token="$1" task_id="$2" deadline=$(( $(date +%s) + $3 )) resp status
  while [ "$(date +%s)" -lt "$deadline" ]; do
    resp=$(curl -sf -H "Authorization: Bearer $token" "$BASE/chat/tasks/$task_id") || { sleep 2; continue; }
    status=$(json_field "$resp" status)
    case "$status" in OK|PARTIAL|FAILED) printf '%s' "$resp"; return 0;; esac
    sleep 2
  done
  return 1
}

echo "=================================================================="
echo " P2 e2e 冒烟：认证 / 角色权限 / 异步任务 / BPM 审批 / 真实落库"
echo "=================================================================="

# ---------- ① 服务健康 ----------
health=$(curl -sf "$BASE/health" 2>/dev/null || true)
[ -n "$health" ] && report PASS "服务健康检查" "$health" \
                || { report FAIL "服务健康检查" "agent-service 不可达"; echo "中止：服务未就绪"; exit 1; }

# ---------- ② 未登录访问应 401 ----------
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/chat" \
  -H 'Content-Type: application/json' -d '{"message":"查库存"}')
[ "$code" = "401" ] && report PASS "未登录拦截(401)" "/chat 无令牌" \
                   || report FAIL "未登录拦截(401)" "实际 HTTP $code"

# ---------- ③ 错误口令应 401 ----------
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"wrong"}')
[ "$code" = "401" ] && report PASS "错误口令拒绝(401)" "" \
                   || report FAIL "错误口令拒绝(401)" "实际 HTTP $code"

# ---------- ④ admin/viewer 登录 ----------
admin_login=$(curl -sf -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}') || { report FAIL "admin登录" "请求失败"; exit 1; }
ADMIN_TOKEN=$(json_field "$admin_login" token)
ADMIN_ROLE=$(json_field "$admin_login" role)
[ -n "$ADMIN_TOKEN" ] && [ "$ADMIN_ROLE" = "admin" ] \
  && report PASS "admin登录" "role=$ADMIN_ROLE" || report FAIL "admin登录" "令牌/角色异常"

viewer_login=$(curl -sf -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d '{"username":"viewer","password":"Viewer@123"}') || { report FAIL "viewer登录" "请求失败"; exit 1; }
VIEWER_TOKEN=$(json_field "$viewer_login" token)
[ -n "$VIEWER_TOKEN" ] && report PASS "viewer登录" "role=viewer" || report FAIL "viewer登录" "令牌为空"

# ---------- ⑤ 异步提交 + 审批前 BPM 拦截 ----------
curl -sf -X POST "$MOCK/demo/reset" >/dev/null 2>&1 || true
resp=$(curl -sf -X POST "$BASE/chat/async" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"message":"查一下阿莫西林胶囊库存，缺货的话向国药控股发起采购审批并自动下单"}') \
  || { report FAIL "异步提交" "请求失败"; exit 1; }
TASK1=$(json_field "$resp" task_id)
[ -n "$TASK1" ] && report PASS "异步提交" "task=$TASK1" || { report FAIL "异步提交" "未返回task_id"; exit 1; }

result1=$(wait_task "$ADMIN_TOKEN" "$TASK1" 90) \
  && report PASS "异步任务完成" "status=$(json_field "$result1" status)" \
  || report FAIL "异步任务完成" "轮询超时"

case "$result1" in
  *BPM_PENDING*) report PASS "审批前BPM拦截" "操作Agent被拦截" ;;
  "")            : ;;
  *)             report FAIL "审批前BPM拦截" "未见BPM_PENDING" ;;
esac
WID=$(printf '%s' "$result1" | grep -o '"workflow_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 \
  | sed 's/.*"\([^"]*\)"$/\1/')

# ---------- ⑥ viewer 角色过滤（仅查询，无审批/下单） ----------
resp=$(curl -sf -X POST "$BASE/chat/async" -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -d '{"message":"查一下阿莫西林胶囊库存，缺货的话向国药控股下单采购"}') || true
TASK2=$(json_field "$resp" task_id)
if [ -n "$TASK2" ]; then
  result2=$(wait_task "$VIEWER_TOKEN" "$TASK2" 60) || result2=""
  case "$result2" in
    *query_inventory*start_purchase_approval*|*query_inventory*create_purchase_order*)
      report FAIL "viewer角色过滤" "结果含越权工具调用" ;;
    *query_inventory*) report PASS "viewer角色过滤" "仅执行只读查询" ;;
    *)                  report FAIL "viewer角色过滤" "结果异常" ;;
  esac
else
  report FAIL "viewer角色过滤" "提交失败"
fi

# ---------- ⑦ Task API 审批通过 → 执行订单落库 ----------
[ -n "$WID" ] || { report FAIL "审批执行" "未取得workflow_id"; WID=""; }
if [ -n "$WID" ]; then
  curl -sf -X POST "$MOCK/demo/approve" >/dev/null || report FAIL "Task API审批" "mock回调失败"
  resp=$(curl -sf -X POST "$BASE/chat/async" -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "{\"message\":\"审批已通过，向国药控股执行订单 workflow_id=$WID\"}") || true
  TASK3=$(json_field "$resp" task_id)
  result3=$(wait_task "$ADMIN_TOKEN" "$TASK3" 90) || result3=""
  status3=$(json_field "$result3" status)
  [ "$status3" = "OK" ] && report PASS "审批后执行(status=OK)" "订单已创建" \
                      || report FAIL "审批后执行" "status=$status3"
fi

# ---------- ⑧ Redis 会话回读 ----------
session=$(curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/chat/sessions/me") || session=""
echo "$session" | grep -q '"role":"assistant"' \
  && report PASS "Redis会话回读" "含助手答复" \
  || report FAIL "Redis会话回读" "会话为空或异常"

# ---------- 汇总 ----------
echo "=================================================================="
echo " 汇总：PASS=$PASS FAIL=$FAIL"
echo "=================================================================="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
