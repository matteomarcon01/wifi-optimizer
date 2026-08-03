#!/usr/bin/env python3
"""Run a read-only, sanitized Wi-Fi path baseline on macOS or Linux."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit


DEFAULT_URLS = (
    "https://example.com/",
    "https://www.cloudflare.com/cdn-cgi/trace",
)


@dataclass
class CommandResult:
    returncode: int | None
    stdout: str
    stderr: str
    error: str | None = None


def run(command: list[str], timeout: float) -> CommandResult:
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    environment["LANG"] = "C"
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            env=environment,
            text=True,
            timeout=timeout,
        )
        return CommandResult(result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return CommandResult(None, "", "", "command timed out")
    except OSError as exc:
        return CommandResult(None, "", "", f"{type(exc).__name__}: {exc}")


def detect_gateway(system: str) -> str | None:
    if system == "Darwin" and shutil.which("route"):
        result = run(["route", "-n", "get", "default"], 5)
        match = re.search(r"^\s*gateway:\s+(\S+)", result.stdout, re.MULTILINE)
        return match.group(1) if match else None

    if system == "Linux" and shutil.which("ip"):
        result = run(["ip", "route", "show", "default"], 5)
        match = re.search(r"\bvia\s+(\S+)", result.stdout)
        return match.group(1) if match else None

    return None


def validate_gateway(value: str) -> str:
    if not value or any(character.isspace() for character in value):
        raise ValueError("gateway must be an IP address without whitespace")

    address, separator, scope = value.partition("%")
    if separator and (not scope or not re.fullmatch(r"[A-Za-z0-9_.-]+", scope)):
        raise ValueError("gateway has an invalid IPv6 scope")
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError as exc:
        raise ValueError("gateway must be an IPv4 or IPv6 address") from exc
    if separator and parsed.version != 6:
        raise ValueError("only IPv6 gateways may include a scope")
    return value


def select_gateway(manual_gateway: str | None, system: str) -> tuple[str | None, str]:
    if manual_gateway is not None:
        return validate_gateway(manual_gateway), "manual"

    detected = detect_gateway(system)
    if detected is None:
        return None, "unavailable"
    try:
        return validate_gateway(detected), "auto"
    except ValueError:
        return None, "unavailable"


def validate_https_url(value: str) -> str:
    if not value or any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("endpoint must not be empty or contain whitespace")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("endpoint is not a valid URL") from exc
    if parsed.scheme.lower() != "https":
        raise ValueError("endpoint must use https://")
    if not parsed.hostname:
        raise ValueError("endpoint must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("endpoint must not contain credentials")
    try:
        parsed.hostname.encode("idna")
    except UnicodeError as exc:
        raise ValueError("endpoint host is invalid") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("endpoint port is invalid")
    return value


def sanitize_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return "<invalid-url>"
    if not host:
        return "<invalid-url>"

    address = host.partition("%")[0]
    try:
        ipaddress.ip_address(address)
        display_host = "<ip-address>"
    except ValueError:
        display_host = host.lower()
    authority = f"{display_host}:{port}" if port is not None else display_host
    return f"https://{authority}"


def sanitize_error(value: str | None, endpoint: str) -> str | None:
    if not value:
        return None
    sanitized = value.replace(endpoint, sanitize_url(endpoint))

    address_pattern = re.compile(
        r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])"
        r"|(?<![\w:])\[?(?:[0-9A-Fa-f]{0,4}:){2,}[0-9A-Fa-f:%]+\]?(?![\w:])"
    )

    def redact_address(match: re.Match[str]) -> str:
        candidate = match.group(0).strip("[]")
        candidate = candidate.partition("%")[0]
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return match.group(0)
        return "<ip-address>"

    return address_pattern.sub(redact_address, sanitized)[:240]


def parse_ping(output: str) -> dict[str, Any]:
    loss_match = re.search(r"([\d.]+)%\s+packet loss", output)
    timing_match = re.search(
        r"(?:round-trip|rtt)[^=]*=\s*"
        r"([\d.]+)/([\d.]+)/([\d.]+)(?:/([\d.]+))?\s*ms",
        output,
    )
    parsed: dict[str, Any] = {
        "packet_loss_percent": float(loss_match.group(1)) if loss_match else None,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "jitter_ms": None,
    }
    if timing_match:
        parsed.update(
            {
                "min_ms": float(timing_match.group(1)),
                "avg_ms": float(timing_match.group(2)),
                "max_ms": float(timing_match.group(3)),
                "jitter_ms": float(timing_match.group(4)) if timing_match.group(4) else None,
            }
        )
    return parsed


def probe_gateway(gateway: str, count: int, interval: float, system: str) -> dict[str, Any]:
    if not shutil.which("ping"):
        return {"status": "skipped", "reason": "ping is unavailable"}

    if system == "Windows":
        command = ["ping", "-n", str(count), "-w", str(max(1000, int(interval * 1000))), gateway]
        timeout = count * max(interval, 1.0) + 10
    else:
        command = ["ping", "-c", str(count), "-i", str(interval), gateway]
        timeout = count * interval + 10

    result = run(command, timeout)
    combined = "\n".join((result.stdout, result.stderr))
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "summary": parse_ping(combined),
        "error": result.error,
    }


def probe_http(urls: list[str], attempts: int, timeout: float) -> dict[str, Any]:
    if not shutil.which("curl"):
        return {"status": "skipped", "reason": "curl is unavailable", "results": []}

    results: list[dict[str, Any]] = []
    write_format = "%{http_code}\t%{time_connect}\t%{time_total}"
    for family in (4, 6):
        for url in urls:
            validate_https_url(url)
            for attempt in range(1, attempts + 1):
                result = run(
                    [
                        "curl",
                        "-q",
                        f"-{family}",
                        "--proto",
                        "=https",
                        "--max-time",
                        str(timeout),
                        "--max-filesize",
                        "65536",
                        "-o",
                        "/dev/null",
                        "-sS",
                        "-w",
                        write_format,
                        "--",
                        url,
                    ],
                    timeout + 3,
                )
                fields = result.stdout.strip().split("\t")
                raw_error = result.error or (result.stderr.strip() or None)
                results.append(
                    {
                        "family": f"IPv{family}",
                        "url": sanitize_url(url),
                        "attempt": attempt,
                        "ok": result.returncode == 0 and len(fields) == 3 and fields[0] != "000",
                        "http_code": fields[0] if len(fields) == 3 else None,
                        "connect_seconds": float(fields[1]) if len(fields) == 3 else None,
                        "total_seconds": float(fields[2]) if len(fields) == 3 else None,
                        "error": sanitize_error(raw_error, url),
                    }
                )
    successful = sum(1 for result in results if result["ok"])
    if successful == len(results):
        status = "ok"
    elif successful:
        status = "partial"
    else:
        status = "failed"
    return {"status": status, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run read-only local-gateway and HTTPS checks without collecting Wi-Fi credentials."
    )
    parser.add_argument("--gateway", help="Default gateway address; auto-detected on macOS and Linux")
    parser.add_argument("--count", type=int, default=50, help="Local ping count (default: 50)")
    parser.add_argument("--interval", type=float, default=0.2, help="Seconds between pings (default: 0.2)")
    parser.add_argument("--url", action="append", dest="urls", help="HTTPS endpoint; repeat for multiple endpoints")
    parser.add_argument("--http-attempts", type=int, default=2, help="Attempts per endpoint and IP family")
    parser.add_argument("--timeout", type=float, default=8.0, help="Per-request timeout in seconds")
    parser.add_argument("--skip-http", action="store_true", help="Skip HTTPS checks")
    args = parser.parse_args()

    if args.count < 1 or args.count > 500:
        parser.error("--count must be between 1 and 500")
    if args.interval < 0.2 or args.interval > 10:
        parser.error("--interval must be between 0.2 and 10 seconds")
    if args.http_attempts < 1 or args.http_attempts > 10:
        parser.error("--http-attempts must be between 1 and 10")
    if args.timeout < 1 or args.timeout > 60:
        parser.error("--timeout must be between 1 and 60 seconds")

    system = platform.system()
    try:
        gateway, gateway_source = select_gateway(args.gateway, system)
    except ValueError as exc:
        parser.error(f"--gateway {exc}")
    try:
        urls = [validate_https_url(url) for url in (args.urls or DEFAULT_URLS)]
    except ValueError as exc:
        parser.error(f"--url {exc}")
    output: dict[str, Any] = {
        "schema_version": 2,
        "platform": system,
        "gateway_available": gateway is not None,
        "gateway_detected": gateway_source == "auto",
        "gateway_source": gateway_source,
        "gateway_probe": (
            probe_gateway(gateway, args.count, args.interval, system)
            if gateway
            else {"status": "skipped", "reason": "default gateway was not detected"}
        ),
        "https_probe": (
            {"status": "skipped", "reason": "disabled", "results": []}
            if args.skip_http
            else probe_http(urls, args.http_attempts, args.timeout)
        ),
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
