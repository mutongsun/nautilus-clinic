"""演示用 Mock：Conductor BPM 准真实模拟 + 诊所备用接口。

Conductor 部分复刻真实集群核心语义（与 src/workflow/definitions/purchase_approval.json 一致）：

  POST /api/metadata/workflow                  注册工作流定义（GET 探测 404/200，幂等注册）
  POST /api/workflow/{name}?correlationId=x    启动实例 -> 返回唯一 workflowId（UUID，非固定值）
  GET  /api/workflow/{id}/status               实例状态 RUNNING/COMPLETED/FAILED（未知ID返回404）
  GET  /api/tasks/in_progress/workflow/{id}/{ref}   查询挂起中的 WAIT 审批任务（拿 taskId）
  POST /api/tasks                              审批回调（真实 Task API 语义）：
        body={workflowInstanceId, taskReferenceName, taskId, status=COMPLETED,
              output={approved: "true"|"false"}}
        DECISION 复刻流程定义：approved="true" -> COMPLETED(APPROVED)
                              其他/缺失      -> FAILED(REJECTED，缺省驳回兜底)

演示控制端点（9000 端口，前端按钮用，内部走同一 Task API 语义）：
  POST /demo/approve    完成所有挂起审批（全部通过）
  POST /demo/reset      清空全部工作流实例
  GET  /demo/workflows  查看全部实例状态（排查用）

诊所接口（真实 Java 底座未启动时的备用演示，--profile clinic 启动后不生效）：
  GET  /clinic/agent/inventory            库存查询
  POST /clinic/agent/purchase/order       采购下单（含计数器）
  POST /clinic/consultation/dispense      发药

生产对接真实 Conductor 后本服务整体下线（换 CONDUCTOR_BASE_URL 即可，平台代码零改动）。
"""

import json
import re
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ==================== Conductor 准真实状态机 ====================

WORKFLOW_DEFS: dict[str, dict] = {}   # 工作流名 -> 定义（metadata 注册）
WORKFLOWS: dict[str, dict] = {}       # workflowId -> 实例（状态机）

# purchase_approval.json 的 WAIT 审批任务引用名（Task API 按此查询/回调）
HUMAN_TASK_REF = "wait_for_human_approval"


def _start_workflow(name: str, correlation_id: str, payload: dict) -> str:
    """启动工作流实例：唯一 UUID，首任务 WAIT 挂起（等待人工审批回调）。"""
    wid = str(uuid.uuid4())
    WORKFLOWS[wid] = {
        "name": name,
        "correlationId": correlation_id,
        "status": "RUNNING",
        "input": payload,
        "output": None,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "tasks": {
            HUMAN_TASK_REF: {
                "taskId": str(uuid.uuid4()),
                "taskDefName": HUMAN_TASK_REF,
                "status": "IN_PROGRESS",
                "output": None,
            }
        },
    }
    return wid


def _complete_task(body: dict) -> tuple[int, object]:
    """审批任务回调：复刻 purchase_approval.json 的 DECISION + TERMINATE 终态流转。"""
    wid = str(body.get("workflowInstanceId", ""))
    ref = str(body.get("taskReferenceName", ""))
    wf = WORKFLOWS.get(wid)
    task = (wf or {}).get("tasks", {}).get(ref)
    if wf is None or task is None:
        return 404, {"error": f"task not found: {wid}/{ref}"}
    if wf["status"] != "RUNNING":
        return 409, {"error": f"workflow already {wf['status']}"}
    if body.get("taskId") != task["taskId"]:
        return 400, {"error": "taskId mismatch"}
    if body.get("status") != "COMPLETED":
        return 400, {"error": f"unsupported task status: {body.get('status')}"}

    task["output"] = body.get("output") or {}
    task["status"] = "COMPLETED"
    # DECISION caseValueParam: $.wait_for_human_approval.output.approved
    approved = str(task["output"].get("approved", "")).lower()
    if approved == "true":  # decisionCases."true" -> TERMINATE COMPLETED
        wf["status"] = "COMPLETED"
        wf["output"] = {"approvalResult": "APPROVED"}
    else:                   # decisionCases."false"/defaultCase -> TERMINATE FAILED（缺省驳回兜底）
        wf["status"] = "FAILED"
        wf["output"] = {"approvalResult": "REJECTED",
                        "reason": "APPROVAL_OUTPUT_MISSING" if not approved else ""}
    return 200, {"taskId": task["taskId"], "status": "COMPLETED"}


# ==================== 诊所备用演示数据 ====================

ORDERS: dict[str, int] = {"count": 0}

INVENTORY = {
    "code": 200,
    "rows": [
        {"medicineName": "布洛芬缓释胶囊", "spec": "0.3g×20粒", "unit": "盒",
         "quantity": 56, "salePrice": 12.0},
        {"medicineName": "阿莫西林胶囊", "spec": "0.5g×24粒", "unit": "盒",
         "quantity": 2, "salePrice": 8.5},
    ],
}


class Handler(BaseHTTPRequestHandler):
    """Mock 请求处理器（8080=Conductor / 8087=诊所备用 / 9000=演示控制）。"""

    def _send(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8") if not isinstance(obj, str) \
            else obj.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",
                         "text/plain" if isinstance(obj, str) else "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------------- GET ----------------
    def do_GET(self) -> None:  # noqa: N802
        path, port = self.path, self.server.server_port
        print(f"[mock] GET  {port} {path}")

        # ---- Conductor：metadata 探测（未注册 404 -> 网关幂等注册）----
        m = re.match(r"^/api/metadata/workflow/([^/?]+)", path)
        if m:
            name = m.group(1)
            if name in WORKFLOW_DEFS:
                return self._send(WORKFLOW_DEFS[name])
            return self._send({"error": f"workflow not found: {name}"}, 404)

        # ---- Conductor：实例状态（未知ID 404 -> 平台映射 UNKNOWN 安全拒绝）----
        m = re.match(r"^/api/workflow/([^/]+)/status", path)
        if m:
            wf = WORKFLOWS.get(m.group(1))
            if wf is None:
                return self._send({"error": "no such workflow"}, 404)
            return self._send({
                "workflowId": m.group(1),
                "workflowType": wf["name"],
                "status": wf["status"],
                "output": wf["output"],
                "correlationId": wf["correlationId"],
            })

        # ---- Conductor：查询挂起中的人工审批任务（审批人拿 taskId）----
        m = re.match(rf"^/api/tasks/in_progress/workflow/([^/]+)/{HUMAN_TASK_REF}", path)
        if m:
            wf = WORKFLOWS.get(m.group(1))
            if wf is None:
                return self._send({"error": "no such workflow"}, 404)
            task = wf["tasks"].get(HUMAN_TASK_REF)
            if wf["status"] == "RUNNING" and task and task["status"] == "IN_PROGRESS":
                return self._send([{
                    "taskId": task["taskId"],
                    "taskDefName": HUMAN_TASK_REF,
                    "workflowInstanceId": m.group(1),
                    "status": "IN_PROGRESS",
                }])
            return self._send([])  # 已终态：无挂起任务

        # ---- 演示控制：查看全部实例 ----
        if path == "/demo/workflows":
            return self._send({
                wid: {"status": wf["status"], "output": wf["output"],
                      "name": wf["name"], "createdAt": wf["createdAt"]}
                for wid, wf in WORKFLOWS.items()
            })

        # ---- 诊所备用 ----
        if path.startswith("/clinic/agent/inventory") or path.startswith("/clinic/inventory"):
            return self._send(INVENTORY)

        if path == "/health":
            return self._send({"status": "ok", "service": "mock-conductor"})
        self._send({"error": f"not found: {path}"}, 404)

    # ---------------- POST ----------------
    def do_POST(self) -> None:  # noqa: N802
        path, port = self.path, self.server.server_port
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except ValueError:
            payload = {}
        print(f"[mock] POST {port} {path} {json.dumps(payload, ensure_ascii=False)[:160]}")

        # ---- Conductor：注册工作流定义（兼容单对象与数组两种形式）----
        if path.startswith("/api/metadata/workflow"):
            defs = payload if isinstance(payload, list) else [payload]
            for d in defs:
                if isinstance(d, dict) and d.get("name"):
                    WORKFLOW_DEFS[d["name"]] = d
            return self._send("registered")

        # ---- Conductor：审批任务回调（DECISION -> 终态流转）----
        if path == "/api/tasks":
            status, body = _complete_task(payload)
            return self._send(body, status)

        # ---- Conductor：启动工作流实例 -> 唯一 UUID ----
        m = re.match(r"^/api/workflow/([^/?]+)", path)
        if m:
            name = m.group(1)
            if name not in WORKFLOW_DEFS:
                return self._send({"error": f"workflow not registered: {name}"}, 404)
            corr = None
            qm = re.search(r"correlationId=([^&]+)", path)
            if qm:
                corr = qm.group(1)
            return self._send(_start_workflow(name, corr or "", payload))

        # ---- 演示控制：一键通过所有挂起审批（内部走 Task API 语义）----
        if path == "/demo/approve":
            approved = []
            for wid, wf in WORKFLOWS.items():
                if wf["status"] == "RUNNING":
                    _complete_task({
                        "workflowInstanceId": wid,
                        "taskReferenceName": HUMAN_TASK_REF,
                        "taskId": wf["tasks"][HUMAN_TASK_REF]["taskId"],
                        "status": "COMPLETED",
                        "output": {"approved": "true"},
                    })
                    approved.append(wid)
            return self._send({"approved": approved, "msg": f"已通过 {len(approved)} 个审批"})

        if path == "/demo/reset":
            WORKFLOWS.clear()
            return self._send({"msg": "工作流实例已清空"})

        # ---- 诊所备用 ----
        if path == "/clinic/agent/purchase/order":
            ORDERS["count"] += 1
            order_no = f"PO-{datetime.now().strftime('%Y%m%d')}-{ORDERS['count']:03d}"
            return self._send({"orderId": order_no, "status": "CREATED"})
        if path == "/clinic/consultation/dispense":
            return self._send({"code": 200, "msg": "发药成功，库存已核减"})
        self._send({"error": f"not found: {path}"}, 404)

    def log_message(self, *_args) -> None:
        """覆盖默认访问日志（已在上层打印简式日志）。"""


if __name__ == "__main__":
    import threading

    # 三个端口同时监听，模拟真实端口分布：
    #   8080 Conductor API（网络别名 conductor-server）
    #   8087 诊所备用（真实 Java 底座未启动时才被解析到）
    #   9000 演示控制端点（宿主机映射，前端按钮/排查用）
    servers = [ThreadingHTTPServer(("0.0.0.0", p), Handler) for p in (8080, 8087, 9000)]
    for srv in servers[1:]:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("[mock] Conductor 准真实模拟启动 :8080(API) :8087(诊所备用) :9000(演示控制)")
    print("[mock] Task API 审批回调: POST /api/tasks {workflowInstanceId,taskId,output.approved}")
    servers[0].serve_forever()
