#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    DEFAULT_REPO_URL,
    DEFAULT_WORKSPACE,
    is_windows,
    linux_primary_script,
    local_bash,
    windows_install_and_run,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a KAI primary/control-plane node.")
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE, help="Repo workspace path (Linux/WSL path).")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL, help="Git repository URL to clone on the node.")
    parser.add_argument("--server-ip", required=True, help="LAN IP address of the primary node.")
    parser.add_argument(
        "--token-file",
        default="~/.kai/k3s-node-token.txt",
        help="Where to save the K3s join token on the primary node.",
    )
    parser.add_argument("--distro", default="Ubuntu-22.04", help="WSL distro name when running on Windows.")
    args = parser.parse_args()

    token_path = str(Path(args.token_file).expanduser())
    script = linux_primary_script(args.workspace, args.repo_url, args.server_ip, token_path)

    if is_windows():
        windows_install_and_run(script, distro=args.distro)
    else:
        local_bash(script)


if __name__ == "__main__":
    main()
