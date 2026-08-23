"""认证与令牌：HS256 JWT（标准库实现，零第三方依赖）+ PBKDF2 口令散列。

JWT 结构与 PyJWT 完全兼容：base64url(header).base64url(payload).base64url(HMAC-SHA256)。
口令散列格式：pbkdf2_sha256$<iterations>$<salt-hex>$<dk-hex>（随机盐，常数时间比较）。
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

_PBKDF2_ITER = 100_000
_TOKEN_TTL = 12 * 3600  # 令牌有效期 12 小时


def _b64url(data: bytes) -> str:
    """base64url 编码（无填充）。"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_dec(s: str) -> bytes:
    """base64url 解码（自动补齐填充）。"""
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(password: str) -> str:
    """生成口令散列（随机 16 字节盐，PBKDF2-SHA256 10万轮迭代）。"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITER)
    return f"pbkdf2_sha256${_PBKDF2_ITER}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验口令（常数时间比较，格式异常一律拒绝不抛错）。"""
    try:
        algo, iters, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), digest)
    except (ValueError, AttributeError):
        return False


def create_token(username: str, role: str, secret: str,
                 expires_seconds: int = _TOKEN_TTL) -> str:
    """签发 HS256 JWT（sub=用户名, role=用户角色, iat/exp=时间戳）。"""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": username, "role": role, "iat": now, "exp": now + expires_seconds}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64url(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"


def decode_token(token: str, secret: str) -> dict:
    """校验并解析 JWT（签名常数时间比较 + exp 过期检查）。

    Raises:
        ValueError: 令牌格式错误 / 签名不符 / 已过期。
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed token")
    h, p, s = parts
    expected = _b64url(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(s, expected):
        raise ValueError("bad signature")
    payload = json.loads(_b64url_dec(p))
    if int(payload.get("exp", 0)) < time.time():
        raise ValueError("token expired")
    return payload
