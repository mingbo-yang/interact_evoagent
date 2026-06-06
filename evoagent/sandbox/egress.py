"""Egress policy — guard outbound network access for web tools.

Provides SSRF protection (blocks loopback / private / link-local / reserved
addresses) and an optional host allowlist. Web tools must validate every URL —
including each redirect hop — through :func:`check_url_allowed` before issuing a
request.
"""

import ipaddress
import socket
from urllib.parse import urlparse

# Schemes we are ever willing to fetch.
_ALLOWED_SCHEMES = {"http", "https"}


def _resolved_ips(host: str) -> list[str]:
    """Resolve a hostname to all of its IP addresses (best effort)."""
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError, OSError):
        return []
    ips: list[str] = []
    for info in infos:
        sockaddr = info[4]
        if sockaddr and isinstance(sockaddr[0], str):
            ips.append(sockaddr[0])
    return ips


def _is_blocked_ip(ip_str: str) -> bool:
    """True if an IP is in a range that must never be reached from a tool.

    Uses an allow-by-public model: anything that is not globally routable is
    rejected (this covers private, loopback, link-local, reserved, and
    carrier-grade NAT / shared address space). Multicast and the unspecified
    address are also rejected explicitly as defense-in-depth.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (not ip.is_global) or ip.is_multicast or ip.is_unspecified


def check_url_allowed(
    url: str,
    allowlist: list[str] | None = None,
    allow_private: bool = False,
) -> tuple[bool, str]:
    """Validate a URL for outbound fetching.

    Args:
        url: The URL to check.
        allowlist: If provided, the host must match one of these entries
            (exact host or a suffix match like ``example.com`` matching
            ``api.example.com``).
        allow_private: When True, skip the private/loopback IP block (only for
            trusted, explicitly-configured internal use).

    Returns:
        ``(allowed, reason)``. ``reason`` explains a rejection.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return False, f"Scheme '{parsed.scheme}' is not allowed (only http/https)."
    host = parsed.hostname
    if not host:
        return False, "URL has no host."

    if allowlist:
        host_l = host.lower()
        ok = any(
            host_l == entry.lower() or host_l.endswith("." + entry.lower())
            for entry in allowlist
        )
        if not ok:
            return False, f"Host '{host}' is not in the egress allowlist."

    if not allow_private:
        ips = _resolved_ips(host)
        if not ips:
            return False, f"Could not resolve host '{host}'."
        for ip in ips:
            if _is_blocked_ip(ip):
                return False, (
                    f"Host '{host}' resolves to a blocked address ({ip}); "
                    f"refusing to fetch private/loopback/reserved targets."
                )
    return True, "ok"
