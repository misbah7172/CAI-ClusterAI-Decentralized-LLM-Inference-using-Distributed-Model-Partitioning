#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    DEFAULT_REPO_URL,
    DEFAULT_WORKSPACE,
    is_windows,
    linux_worker_script,
    local_bash,
    windows_install_and_run,
)


def _read_token(args: argparse.Namespace) -> str:
    if args.token:
        return args.token.strip()
    if args.token_file:
        return Path(args.token_file).expanduser().read_text(encoding="utf-8").strip()
    raise SystemExit("Provide either --token or --token-file.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a KAI worker node.")
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE, help="Repo workspace path (Linux/WSL path).")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL, help="Git repository URL to clone on the node.")
    parser.add_argument("--server-url", required=True, help="K3s server URL, e.g. https://192.168.1.100:6443")
    parser.add_argument("--token", help="K3s join token copied from the primary node.")
    parser.add_argument("--token-file", help="Path to a file containing the K3s join token.")
    parser.add_argument("--distro", default="Ubuntu-22.04", help="WSL distro name when running on Windows.")
    args = parser.parse_args()

    token = _read_token(args)
    script = linux_worker_script(args.workspace, args.repo_url, args.server_url, token)

    if is_windows():
        windows_install_and_run(script, distro=args.distro)
    else:
        local_bash(script)


if __name__ == "__main__":
    main()
