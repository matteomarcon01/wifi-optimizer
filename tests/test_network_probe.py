from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import network_probe as probe  # noqa: E402


class CommandTests(unittest.TestCase):
    def test_run_forces_stable_english_output(self) -> None:
        completed = subprocess.CompletedProcess(["tool"], 0, "ok", "")
        with mock.patch.object(probe.subprocess, "run", return_value=completed) as run_mock:
            result = probe.run(["tool"], 1)

        self.assertEqual(result.returncode, 0)
        environment = run_mock.call_args.kwargs["env"]
        self.assertEqual(environment["LC_ALL"], "C")
        self.assertEqual(environment["LANG"], "C")

    def test_run_does_not_repeat_timed_out_command(self) -> None:
        timeout = subprocess.TimeoutExpired(["curl", "https://example.com/?token=secret"], 1)
        with mock.patch.object(probe.subprocess, "run", side_effect=timeout):
            result = probe.run(["curl", "https://example.com/?token=secret"], 1)

        self.assertEqual(result.error, "command timed out")
        self.assertNotIn("secret", result.error or "")


class GatewayTests(unittest.TestCase):
    def test_manual_gateway_is_reported_as_manual(self) -> None:
        with mock.patch.object(probe, "detect_gateway") as detect:
            gateway, source = probe.select_gateway("192.0.2.1", "Darwin")

        self.assertEqual((gateway, source), ("192.0.2.1", "manual"))
        detect.assert_not_called()

    def test_detected_gateway_is_reported_as_auto(self) -> None:
        with mock.patch.object(probe, "detect_gateway", return_value="192.0.2.1"):
            gateway, source = probe.select_gateway(None, "Linux")

        self.assertEqual((gateway, source), ("192.0.2.1", "auto"))

    def test_gateway_rejects_command_options(self) -> None:
        with self.assertRaisesRegex(ValueError, "IPv4 or IPv6"):
            probe.validate_gateway("-f")


class PingParsingTests(unittest.TestCase):
    def test_parses_macos_ping(self) -> None:
        output = """
2 packets transmitted, 2 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 1.000/2.000/3.000/0.500 ms
"""
        self.assertEqual(
            probe.parse_ping(output),
            {
                "packet_loss_percent": 0.0,
                "min_ms": 1.0,
                "avg_ms": 2.0,
                "max_ms": 3.0,
                "jitter_ms": 0.5,
            },
        )

    def test_parses_linux_ping(self) -> None:
        output = """
2 packets transmitted, 2 received, 0% packet loss, time 1001ms
rtt min/avg/max/mdev = 4.000/5.000/6.000/0.250 ms
"""
        parsed = probe.parse_ping(output)
        self.assertEqual(parsed["packet_loss_percent"], 0.0)
        self.assertEqual(parsed["avg_ms"], 5.0)
        self.assertEqual(parsed["jitter_ms"], 0.25)

    def test_parses_busybox_ping_without_jitter(self) -> None:
        output = """
2 packets transmitted, 2 packets received, 0% packet loss
round-trip min/avg/max = 1.000/2.000/3.000 ms
"""
        parsed = probe.parse_ping(output)
        self.assertEqual(parsed["avg_ms"], 2.0)
        self.assertIsNone(parsed["jitter_ms"])


class EndpointTests(unittest.TestCase):
    def test_endpoint_requires_https(self) -> None:
        for endpoint in ("http://example.com", "file:///etc/passwd", "-K/dev/null"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                probe.validate_https_url(endpoint)

    def test_endpoint_rejects_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "credentials"):
            probe.validate_https_url("https://user:secret@example.com/")

    def test_sanitized_url_removes_path_query_and_ip(self) -> None:
        endpoint = "https://192.0.2.1:8443/private/token?key=secret"
        self.assertEqual(probe.sanitize_url(endpoint), "https://<ip-address>:8443")

    def test_curl_command_uses_end_of_options_and_disables_config(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], timeout: float) -> probe.CommandResult:
            commands.append(command)
            return probe.CommandResult(0, "204\t0.010\t0.020", "")

        with mock.patch.object(probe.shutil, "which", return_value="/usr/bin/curl"):
            with mock.patch.object(probe, "run", side_effect=fake_run):
                result = probe.probe_http(["https://example.com/path?key=secret"], 1, 1)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["results"][0]["url"], "https://example.com")
        for command in commands:
            self.assertEqual(command[1], "-q")
            self.assertNotIn("-L", command)
            self.assertEqual(command[-2], "--")
            self.assertEqual(command[-1], "https://example.com/path?key=secret")

    def test_https_status_is_failed_when_every_attempt_fails(self) -> None:
        failed = probe.CommandResult(
            7,
            "000\t0.000\t0.001",
            "curl failed for https://192.0.2.1/private?token=secret at 192.0.2.1",
        )
        with mock.patch.object(probe.shutil, "which", return_value="/usr/bin/curl"):
            with mock.patch.object(probe, "run", return_value=failed):
                result = probe.probe_http(["https://192.0.2.1/private?token=secret"], 1, 1)

        self.assertEqual(result["status"], "failed")
        self.assertTrue(all(not attempt["ok"] for attempt in result["results"]))
        serialized = str(result)
        self.assertNotIn("192.0.2.1", serialized)
        self.assertNotIn("secret", serialized)

    def test_https_status_is_partial_when_only_one_family_succeeds(self) -> None:
        responses = [
            probe.CommandResult(0, "204\t0.010\t0.020", ""),
            probe.CommandResult(7, "000\t0.000\t0.001", "connection failed"),
        ]
        with mock.patch.object(probe.shutil, "which", return_value="/usr/bin/curl"):
            with mock.patch.object(probe, "run", side_effect=responses):
                result = probe.probe_http(["https://example.com/"], 1, 1)

        self.assertEqual(result["status"], "partial")


if __name__ == "__main__":
    unittest.main()
