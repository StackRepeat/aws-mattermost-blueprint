#!/usr/bin/env python3
"""Opt-in Docker integration check. Creates and removes only its own resources."""

import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "terraform/templates/bootstrap.sh.tftpl").read_text()
LOCALS = (ROOT / "terraform/main.tf").read_text()


def image_pin(name):
    match = re.search(rf'^\s*{name}\s*=\s*"([^"\n]+)"', LOCALS, re.MULTILINE)
    if not match or "@sha256:" not in match[1]:
        raise RuntimeError(f"Missing immutable {name} pin in terraform/main.tf")
    return match[1]


def main():
    if not shutil.which("docker"):
        raise SystemExit("Docker with the Compose plugin must be installed and running.")
    subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL)
    project = "stackrepeat-smoke-" + secrets.token_hex(6)
    username = "demo-admin"
    email = "demo-admin@example.invalid"
    password = "Demo1-" + secrets.token_hex(20)
    db_password = secrets.token_hex(24)
    postgres_image = image_pin("postgres_image")
    mattermost_image = image_pin("mattermost_image")

    with tempfile.TemporaryDirectory(prefix=project + "-") as temporary:
        directory = Path(temporary)
        compose = TEMPLATE.split("<<'COMPOSE'\n", 1)[1].split("\nCOMPOSE", 1)[0]
        compose = compose.replace("${postgres_image}", postgres_image)
        compose = compose.replace("${mattermost_image}", mattermost_image)
        compose = compose.replace("$${", "${")
        # The catalogue targets x86_64; this also tests that image on ARM laptops.
        compose = compose.replace("    image:", "    platform: linux/amd64\n    image:")
        compose = compose.replace("127.0.0.1:8065:8065", "127.0.0.1::8065")
        (directory / "compose.yaml").write_text(compose)
        (directory / ".env").write_text(
            f"COMPOSE_PROJECT_NAME={project}\n"
            f"POSTGRES_PASSWORD={db_password}\n"
            "MM_SQLSETTINGS_DATASOURCE="
            f"postgres://mattermost:{db_password}@postgres:5432/mattermost"
            "?sslmode=disable&connect_timeout=10\n"
            "MM_SERVICESETTINGS_SITEURL=http://localhost\n"
        )
        os.chmod(directory / ".env", 0o600)
        for folder in ["config", "data", "logs", "plugins", "client-plugins", "bleve-indexes"]:
            (directory / "volumes/mattermost" / folder).mkdir(parents=True)
        (directory / "volumes/postgres").mkdir(parents=True)
        (directory / "limits.yaml").write_text(
            "services:\n"
            "  postgres:\n    mem_limit: 512m\n    cpus: 0.25\n"
            "  mattermost:\n    mem_limit: 1536m\n    cpus: 0.5\n"
        )
        command = ["docker", "compose", "-p", project, "-f", str(directory / "compose.yaml"),
                   "-f", str(directory / "limits.yaml")]

        def run(*args, capture=False):
            return subprocess.run(command + list(args), cwd=directory, check=True,
                                  text=True, stdout=subprocess.PIPE if capture else None).stdout

        def mmctl(*args, capture=False):
            return run("exec", "-T", "mattermost", "/mattermost/bin/mmctl", "--local",
                       *args, capture=capture)

        def seed():
            users = json.loads(mmctl("user", "list", "--all", "--json", capture=True)) or []
            if not any(user["username"] == username for user in users):
                mmctl("user", "create", "--username", username, "--email", email,
                      "--password", password, "--system-admin", "--email-verified",
                      "--disable-welcome-email", capture=True)
            teams = json.loads(mmctl("team", "list", "--json", capture=True)) or []
            if not any(team["name"] == "stackrepeat-demo" for team in teams):
                mmctl("team", "create", "--name", "stackrepeat-demo", "--display-name",
                      "StackRepeat Demo", "--email", email, "--private", capture=True)
            mmctl("team", "users", "add", "stackrepeat-demo", username, capture=True)

        try:
            print("Starting isolated Mattermost and PostgreSQL containers (2 GiB combined cap).", flush=True)
            subprocess.run(
                ["docker", "run", "--rm", "--name", project + "-permissions",
                 "--platform", "linux/amd64", "--user", "0", "--entrypoint", "/bin/sh",
                 "-v", str(directory / "volumes") + ":/volumes", postgres_image,
                 "-ec", "chown -R 2000:2000 /volumes/mattermost"], check=True,
            )
            run("up", "-d")
            address = run("port", "mattermost", "8065", capture=True).strip()
            base = "http://" + address + "/api/v4"

            def request(path, payload=None, token=None):
                headers = {"Content-Type": "application/json"}
                if token:
                    headers["Authorization"] = "Bearer " + token
                data = None if payload is None else json.dumps(payload).encode()
                with urllib.request.urlopen(urllib.request.Request(base + path, data=data,
                                                                  headers=headers), timeout=10) as response:
                    return response.headers, json.load(response)

            def wait_ready():
                for _ in range(180):
                    try:
                        _, payload = request("/system/ping")
                        if payload["status"] == "OK":
                            return
                    except (OSError, KeyError, json.JSONDecodeError):
                        pass
                    time.sleep(2)
                raise RuntimeError("Mattermost was not ready within six minutes.")

            def assert_signup_blocked():
                try:
                    request("/users", {"username": "public-takeover", "email": "takeover@example.invalid",
                                       "password": "BlockedPublicSignupPassword123456"})
                except urllib.error.HTTPError as error:
                    if error.code == 501:
                        return
                    raise
                raise AssertionError("Public registration was unexpectedly accepted.")

            def assert_login():
                headers, user = request("/users/login", {"login_id": username, "password": password})
                assert "system_admin" in user["roles"], "Account lacks administrator permissions."
                _, teams = request("/users/me/teams", token=headers["Token"])
                assert any(team["name"] == "stackrepeat-demo" for team in teams), "Demo team is missing."

            wait_ready()
            assert_signup_blocked()  # Includes the first-user takeover window.
            seed()
            seed()
            assert_signup_blocked()
            assert_login()
            run("restart", "mattermost")
            # Docker can allocate another host port when restarting a container
            # whose localhost binding requested an automatically chosen port.
            address = run("port", "mattermost", "8065", capture=True).strip()
            base = "http://" + address + "/api/v4"
            wait_ready()
            seed()
            assert_login()
            print("PASS: closed initial signup, repeated bootstrap, administrator login, team membership, "
                  "and restart persistence.", flush=True)
        finally:
            # No global prune: the unique Compose project scopes all cleanup.
            subprocess.run(command + ["down", "--volumes", "--remove-orphans"], cwd=directory,
                           check=False, timeout=120)
            # Linux containers can create files owned by other UIDs on a Linux host.
            subprocess.run(
                ["docker", "run", "--rm", "--name", project + "-cleanup", "--platform", "linux/amd64",
                 "--user", "0", "--entrypoint", "/bin/sh", "-v", str(directory / "volumes") + ":/volumes",
                 postgres_image, "-ec", "chmod -R a+rwX /volumes"], check=False, timeout=60,
            )


if __name__ == "__main__":
    main()
