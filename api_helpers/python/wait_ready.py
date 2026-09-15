#!/usr/bin/env python3
"""Only report success after the public Mattermost API responds over HTTPS."""

import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen


def validate_endpoint(endpoint):
    parts = urlsplit(endpoint)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or not parts.hostname.endswith(".cloudfront.net")
        or parts.username is not None
        or parts.password is not None
        or parts.port is not None
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
    ):
        raise ValueError("Expected this blueprint's HTTPS CloudFront endpoint")


def ready(endpoint):
    try:
        with urlopen(endpoint.rstrip("/") + "/api/v4/system/ping", timeout=15) as response:
            return response.status == 200 and json.loads(response.read(65536)).get("status") == "OK"
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, AttributeError):
        return False


def wait_until_ready(endpoint, timeout=900, interval=10):
    validate_endpoint(endpoint)
    deadline = time.monotonic() + timeout
    while True:
        if ready(endpoint):
            print(f"Mattermost is ready: {endpoint}", flush=True)
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "Mattermost did not become ready within 15 minutes after Terraform. "
                "Inspect the EC2 instance via Session Manager: "
                "journalctl -u stackrepeat-mattermost.service. "
                "Resources still exist; retry or destroy the workload."
            )
        time.sleep(min(interval, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    try:
        wait_until_ready(sys.argv[1])
    except (IndexError, ValueError, TimeoutError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
