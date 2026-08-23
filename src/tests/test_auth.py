"""P2 认证单测：JWT 签发校验 / 口令散列 / 角色权限过滤（全部离线运行）。"""

import pytest

from src.agent.nodes.dispatcher import filter_plan_by_role
from src.common.constants import USER_ROLE_ALLOWED_AGENTS, AgentRole
from src.common.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

SECRET = "unit-test-secret"


# ==================== JWT ====================

def test_jwt_roundtrip() -> None:
    """签发 -> 解析：用户名/角色/过期时间完整回传。"""
    token = create_token("alice", "admin", SECRET)
    payload = decode_token(token, SECRET)
    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"
    assert payload["exp"] > payload["iat"]


def test_jwt_expired_rejected() -> None:
    """过期令牌拒绝（负有效期构造已过期）。"""
    token = create_token("bob", "viewer", SECRET, expires_seconds=-10)
    with pytest.raises(ValueError, match="expired"):
        decode_token(token, SECRET)


def test_jwt_tampered_signature_rejected() -> None:
    """签名篡改拒绝（常数时间比较仍判不匹配）。"""
    token = create_token("carl", "admin", SECRET)
    h, p, _s = token.split(".")
    forged = f"{h}.{p}.Zm9yZ2Vk"  # 伪造签名段
    with pytest.raises(ValueError, match="signature"):
        decode_token(forged, SECRET)


def test_jwt_wrong_secret_rejected() -> None:
    """密钥不符拒绝。"""
    token = create_token("dave", "viewer", SECRET)
    with pytest.raises(ValueError, match="signature"):
        decode_token(token, "another-secret")


def test_jwt_malformed_rejected() -> None:
    """格式错误拒绝（非三段式）。"""
    with pytest.raises(ValueError, match="malformed"):
        decode_token("not.a..jwt.x", SECRET)


# ==================== 口令散列 ====================

def test_password_hash_verify() -> None:
    """正确口令通过，错误口令拒绝。"""
    stored = hash_password("S3cret!密码")
    assert verify_password("S3cret!密码", stored)
    assert not verify_password("wrong", stored)


def test_password_hash_salted() -> None:
    """同口令两次散列结果不同（随机盐），但均可通过校验。"""
    h1, h2 = hash_password("same"), hash_password("same")
    assert h1 != h2
    assert verify_password("same", h1) and verify_password("same", h2)


def test_password_malformed_stored_rejected() -> None:
    """存储格式异常安全拒绝（不抛错）。"""
    assert not verify_password("x", "not-a-valid-hash")
    assert not verify_password("x", "")


# ==================== 角色权限过滤（服务端强制） ====================

_ALL_PLAN = ["query_agent", "approval_agent", "operator_agent"]


def test_role_mapping_completeness() -> None:
    """三种用户角色的允许集合覆盖全部业务 Agent（dispatcher 越权判定依据）。"""
    all_agents = {AgentRole.QUERY.value, AgentRole.APPROVAL.value, AgentRole.OPERATOR.value}
    for role, allowed in USER_ROLE_ALLOWED_AGENTS.items():
        assert allowed <= all_agents
        assert allowed  # 禁止空集合（至少保留只读）


def test_filter_viewer_blocks_write_agents() -> None:
    """viewer 仅保留查询：审批/操作子任务全部剔除。"""
    assert filter_plan_by_role(_ALL_PLAN, "viewer") == ["query_agent"]


def test_filter_admin_keeps_all() -> None:
    """admin 全量保留（顺序不变）。"""
    assert filter_plan_by_role(_ALL_PLAN, "admin") == _ALL_PLAN


def test_filter_none_role_passthrough() -> None:
    """开发模式（user_role=None）不过滤（兼容脚本与旧调用）。"""
    assert filter_plan_by_role(_ALL_PLAN, None) == _ALL_PLAN


def test_filter_unknown_role_blocks_all() -> None:
    """未知角色安全兜底：全部剔除（宁拒勿漏）。"""
    assert filter_plan_by_role(_ALL_PLAN, "hacker") == []
