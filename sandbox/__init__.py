"""
CAI Sandbox — Decentralized Node Platform.

Allows any laptop to run the full CAI stack in an isolated sandbox,
join distributed clusters remotely, and operate in single-node or
multi-node modes with minimal setup.

Modules
-------
runtime     – Sandbox runtime manager and Docker orchestration
agent       – Node agent for cluster communication
discovery   – LAN auto-discovery and manual connection
auth        – Token-based authentication and TLS
simulation  – Multi-node simulation on a single machine
controller  – Remote cluster management API
cli         – ``cai_sandbox`` command-line interface
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
