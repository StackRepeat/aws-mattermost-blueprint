"""Readiness must fail closed on startup errors and ignore destroy operations."""

import importlib.util
import io
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wait_ready", ROOT / "api_helpers/python/wait_ready.py")
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


class Response(io.BytesIO):
    status = 200


class ReadinessTests(unittest.TestCase):
    def test_waits_through_startup_failures(self):
        responses = [URLError("starting"), Response(b'{"status":"FAIL"}'), Response(b'{"status":"OK"}')]
        with patch.object(readiness, "urlopen", side_effect=responses) as request:
            with patch.object(readiness.time, "sleep"):
                readiness.wait_until_ready("https://demo.cloudfront.net")
        self.assertEqual(request.call_count, 3)

    def test_html_error_page_is_not_ready(self):
        with patch.object(readiness, "urlopen", return_value=Response(b"<html>Unavailable</html>")):
            self.assertFalse(readiness.ready("https://demo.cloudfront.net"))

    def test_unhealthy_service_fails_deployment(self):
        with patch.object(readiness, "ready", return_value=False):
            with self.assertRaises(TimeoutError):
                readiness.wait_until_ready("https://demo.cloudfront.net", timeout=0)

    def test_endpoint_rejects_credentials_and_unexpected_hosts(self):
        for endpoint in ("http://demo.cloudfront.net", "https://user:pass@demo.cloudfront.net",
                         "https://console.aws.amazon.com/", "https://demo.cloudfront.net.evil.test",
                         "https://demo.cloudfront.net/path", "https://demo.cloudfront.net?secret=test"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                readiness.validate_endpoint(endpoint)

    def test_destroy_does_not_need_terraform_or_network(self):
        result = subprocess.run(
            ["/bin/bash", str(ROOT / "api_helpers/post-api-helpers.sh")],
            env={"WORKLOAD_ACTION": "destroy", "PATH": "/nonexistent"},
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
