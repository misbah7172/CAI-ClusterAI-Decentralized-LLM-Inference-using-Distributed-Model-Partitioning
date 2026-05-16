from __future__ import annotations

import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO_URL = "https://github.com/misbah7172/GreenCluster-AI-KAI.git"
DEFAULT_WORKSPACE = "/opt/kai"
DEFAULT_WSL_DISTRO = "Ubuntu-22.04"


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


def run(cmd: list[str], *, check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=True,
    )


def wsl_available() -> bool:
    return shutil.which("wsl") is not None or shutil.which("wsl.exe") is not None


def wsl_exec(script: str, distro: str = DEFAULT_WSL_DISTRO) -> None:
    wsl_bin = shutil.which("wsl") or shutil.which("wsl.exe")
    if not wsl_bin:
        raise RuntimeError(
            "WSL is not installed. Run `wsl --install -d Ubuntu-22.04`, reboot, then rerun the bootstrap script."
        )
    run([wsl_bin, "-d", distro, "--", "bash", "-lc", script])


def local_bash(script: str) -> None:
    run(["bash", "-lc", script])


def quote(value: str) -> str:
    return shlex.quote(str(value))


def linux_install_prereqs_script(workspace: str, repo_url: str) -> str:
    return dedent(
        f"""
        set -euo pipefail
        export DEBIAN_FRONTEND=noninteractive
        sudo apt-get update
        sudo apt-get install -y --no-install-recommends \
          ca-certificates curl git python3 python3-pip python3-venv docker.io
        sudo systemctl enable --now docker || sudo service docker start || true
        sudo usermod -aG docker "$USER" || true

        mkdir -p {quote(workspace)}
        if [ ! -d {quote(workspace)}/.git ]; then
          git clone {quote(repo_url)} {quote(workspace)}
        fi
        cd {quote(workspace)}

        python3 -m venv .venv310
        . .venv310/bin/activate
        pip install --upgrade pip setuptools wheel
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
        pip install -r docs/requirements.txt
        """
    ).strip()


def linux_primary_script(workspace: str, repo_url: str, server_ip: str, token_path: str) -> str:
    return dedent(
        f"""
        {linux_install_prereqs_script(workspace, repo_url)}

        curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --write-kubeconfig-mode 644 --tls-san {quote(server_ip)}" sh -

        sudo mkdir -p $(dirname {quote(token_path)})
        sudo cat /var/lib/rancher/k3s/server/node-token | tee {quote(token_path)}

        echo
        echo "KAI primary node is ready."
        echo "K3S_URL=https://{server_ip}:6443"
        echo "K3S_TOKEN=$(cat {quote(token_path)})"
        echo "Token saved to: {token_path}"
        """
    ).strip()


def linux_worker_script(workspace: str, repo_url: str, server_url: str, token: str) -> str:
    safe_server_url = quote(server_url)
    safe_token = quote(token)
    return dedent(
        f"""
        {linux_install_prereqs_script(workspace, repo_url)}

        export K3S_URL={safe_server_url}
        export K3S_TOKEN={safe_token}
        curl -sfL https://get.k3s.io | K3S_URL="$K3S_URL" K3S_TOKEN="$K3S_TOKEN" sh -

        echo
        echo "KAI worker node joined successfully."
        echo "Connected to: $K3S_URL"
        """
    ).strip()


def windows_install_and_run(script: str, distro: str = DEFAULT_WSL_DISTRO) -> None:
    if not wsl_available():
        raise RuntimeError(
            "WSL is not installed. Run `wsl --install -d Ubuntu-22.04`, reboot, then rerun this script."
        )
    wsl_exec(script, distro=distro)
