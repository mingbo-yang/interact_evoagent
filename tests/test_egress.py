"""Tests for the egress policy (SSRF protection + allowlist)."""

from evoagent.sandbox import egress


def test_blocks_non_http_scheme():
    ok, reason = egress.check_url_allowed("ftp://example.com/x")
    assert not ok
    assert "scheme" in reason.lower()


def test_blocks_missing_host():
    ok, _ = egress.check_url_allowed("http:///path")
    assert not ok


def test_blocks_loopback(monkeypatch):
    monkeypatch.setattr(egress, "_resolved_ips", lambda host: ["127.0.0.1"])
    ok, reason = egress.check_url_allowed("http://localhost/x")
    assert not ok
    assert "blocked" in reason.lower()


def test_blocks_private_range(monkeypatch):
    monkeypatch.setattr(egress, "_resolved_ips", lambda host: ["10.0.0.5"])
    ok, _ = egress.check_url_allowed("http://internal.example/x")
    assert not ok


def test_blocks_link_local(monkeypatch):
    monkeypatch.setattr(egress, "_resolved_ips", lambda host: ["169.254.169.254"])
    ok, reason = egress.check_url_allowed("http://metadata/x")
    assert not ok


def test_allows_public(monkeypatch):
    monkeypatch.setattr(egress, "_resolved_ips", lambda host: ["93.184.216.34"])
    ok, reason = egress.check_url_allowed("https://example.com/x")
    assert ok
    assert reason == "ok"


def test_allowlist_rejects_other_host(monkeypatch):
    monkeypatch.setattr(egress, "_resolved_ips", lambda host: ["93.184.216.34"])
    ok, reason = egress.check_url_allowed(
        "https://evil.com/x", allowlist=["example.com"]
    )
    assert not ok
    assert "allowlist" in reason.lower()


def test_allowlist_accepts_subdomain(monkeypatch):
    monkeypatch.setattr(egress, "_resolved_ips", lambda host: ["93.184.216.34"])
    ok, _ = egress.check_url_allowed(
        "https://api.example.com/x", allowlist=["example.com"]
    )
    assert ok


def test_unresolvable_host_blocked(monkeypatch):
    monkeypatch.setattr(egress, "_resolved_ips", lambda host: [])
    ok, reason = egress.check_url_allowed("https://nope.invalid/x")
    assert not ok
    assert "resolve" in reason.lower()


def test_allow_private_bypass(monkeypatch):
    monkeypatch.setattr(egress, "_resolved_ips", lambda host: ["127.0.0.1"])
    ok, _ = egress.check_url_allowed("http://localhost/x", allow_private=True)
    assert ok
