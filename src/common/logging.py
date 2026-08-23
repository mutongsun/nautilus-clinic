"""JSON 结构化日志：统一输出格式、审计脱敏、错误三要素（堆栈/请求ID/上下文）。

禁止业务代码使用 print；统一通过 get_logger 获取 JSON 格式 logger。
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

# 入库 / 输出前必须脱敏的字段名（大小写不敏感）
SENSITIVE_KEYS = {"password", "token", "api_key", "apikey", "secret", "authorization", "id_card", "credential"}

# 标准日志属性（这些之外的 record 属性视为业务附加字段原样输出）
_RESERVED = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "taskName"}


def sanitize(value: Any) -> Any:
    """递归脱敏：将敏感字段值替换为 ***，其余结构原样保留。

    Args:
        value: 任意可 JSON 序列化的结构（dict / list / 标量）。

    Returns:
        脱敏后的同构数据。
    """
    if isinstance(value, dict):
        return {
            k: ("***" if str(k).lower() in SENSITIVE_KEYS else sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    """将 LogRecord 序列化为单行 JSON，便于采集与检索。"""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D102
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # 附加字段（业务通过 extra 传入）
        for key, val in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                try:
                    json.dumps(val, ensure_ascii=False, default=str)
                except (TypeError, ValueError):
                    val = str(val)
                payload[key] = val
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


_configured = False


def setup_logging(level: str = "INFO") -> None:
    """初始化根 logger（幂等），全进程只配置一次。

    Args:
        level: 日志级别字符串，如 INFO / DEBUG。
    """
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()
    root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger（JSON 格式由 setup_logging 统一保证）。"""
    return logging.getLogger(name)
