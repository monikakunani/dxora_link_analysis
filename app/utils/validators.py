import ipaddress
import socket
from urllib.parse import urlparse


class URLValidationError(ValueError):
    """Raised when a URL is invalid."""
    pass


class SSRFError(ValueError):
    """Raised when a URL targets a private/internal network address."""
    pass


# Private / reserved IP ranges that should be blocked
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_private_ip(ip_str: str) -> bool:
    """Return True for any address that should not be reached by this service."""
    try:
        ip = ipaddress.ip_address(ip_str)
        # IPv4-mapped IPv6 addresses must be checked using their embedded IPv4.
        candidate = ip.ipv4_mapped if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped else ip
        if not candidate.is_global:
            return True
        for network in _BLOCKED_NETWORKS:
            if candidate.version == network.version and candidate in network:
                return True
        return False
    except ValueError:
        return False


def resolve_and_check(hostname: str) -> list[str]:
    """
    Resolve a hostname via DNS and verify ALL returned IPs are public.

    Returns the list of safe resolved IP strings.

    Raises:
        URLValidationError: If the hostname cannot be resolved.
        SSRFError: If any resolved IP is private/internal.
    """
    try:
        addr_infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise URLValidationError(f"Could not resolve hostname: {hostname}")

    resolved_ips: list[str] = []
    for _family, _, _, _, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        if is_private_ip(ip_str):
            raise SSRFError(
                f"URL resolves to a private/internal IP address ({ip_str})"
            )
        if ip_str not in resolved_ips:
            resolved_ips.append(ip_str)

    if not resolved_ips:
        raise URLValidationError(f"No addresses found for hostname: {hostname}")

    return resolved_ips


def validate_url(url: str) -> str:
    """
    Validate a URL for correctness and SSRF safety.

    Performs DNS resolution and checks all returned IPs against
    private/reserved ranges.  The resolved IPs are NOT returned here
    because the fetch layer pins the connection to a validated IP
    separately (see website_extractor.py).

    Args:
        url: The URL string to validate.

    Returns:
        The validated URL string.

    Raises:
        URLValidationError: If the URL is malformed.
        SSRFError: If the URL resolves to a private/internal address.
    """
    # Basic parsing
    try:
        parsed = urlparse(url)
    except Exception:
        raise URLValidationError("Could not parse URL")

    # Scheme check
    if parsed.scheme not in ("http", "https"):
        raise URLValidationError("Only http and https URLs are supported")

    # Host check
    hostname = parsed.hostname
    if not hostname:
        raise URLValidationError("URL must include a valid hostname")

    if parsed.username is not None or parsed.password is not None:
        raise URLValidationError("URLs containing username or password are not allowed")

    try:
        port = parsed.port
    except ValueError as exc:
        raise URLValidationError("URL contains an invalid port") from exc
    expected_port = 443 if parsed.scheme == "https" else 80
    if port not in (None, expected_port):
        raise URLValidationError("Only the standard HTTP and HTTPS ports are allowed")

    # Block obvious local hostnames
    blocked_hostnames = {"localhost", "0.0.0.0", "127.0.0.1", "::1", "[::1]"}
    if hostname.lower() in blocked_hostnames:
        raise SSRFError("Access to localhost is not allowed")

    # DNS resolution check — verifies all resolved IPs are public
    resolve_and_check(hostname)

    return url
