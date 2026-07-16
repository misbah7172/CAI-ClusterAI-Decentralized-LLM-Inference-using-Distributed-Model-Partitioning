"""
Token-based authentication for the CAI Sandbox cluster.

The primary node generates JWT access tokens that worker nodes present
when registering. Tokens contain cluster identity, role, and expiry.

Usage::

    manager = TokenManager()
    token = manager.generate_cluster_token(cluster_id="my-cluster")
    print(f"Share this token with workers: {token}")

    # On worker node
    is_valid, claims = manager.validate_token(token)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sandbox.config import TOKEN_DIR, TOKEN_EXPIRY_HOURS, TOKEN_SECRET_ENV

logger = logging.getLogger(__name__)


@dataclass
class TokenClaims:
    """Decoded token payload."""
    token_id: str
    cluster_id: str
    node_role: str  # "primary" or "worker"
    issued_at: float
    expires_at: float
    permissions: List[str] = field(default_factory=lambda: ["join", "heartbeat", "inference"])
    issuer_node_id: str = ""

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "cluster_id": self.cluster_id,
            "node_role": self.node_role,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "permissions": self.permissions,
            "issuer_node_id": self.issuer_node_id,
        }


class TokenManager:
    """Manages JWT-like access tokens for the sandbox cluster.

    Tokens are HMAC-SHA256 signed JSON payloads (not full JWT to avoid
    external dependency requirements). The signing secret is generated
    once per cluster and stored locally.

    Parameters
    ----------
    token_dir : Path
        Directory for storing token metadata and the signing secret.
    secret : str, optional
        Override the signing secret (otherwise auto-generated/loaded).
    """

    def __init__(
        self,
        token_dir: Optional[Path] = None,
        secret: Optional[str] = None,
    ):
        self._token_dir = token_dir or TOKEN_DIR
        self._token_dir.mkdir(parents=True, exist_ok=True)
        self._secret = secret or self._load_or_create_secret()
        self._revoked: set[str] = set()
        self._load_revocation_list()

    # ------------------------------------------------------------------
    # Token generation
    # ------------------------------------------------------------------

    def generate_cluster_token(
        self,
        cluster_id: str = "",
        node_role: str = "worker",
        expiry_hours: Optional[int] = None,
        permissions: Optional[List[str]] = None,
        issuer_node_id: str = "",
    ) -> str:
        """Generate a new access token for cluster membership.

        Parameters
        ----------
        cluster_id : str
            Cluster identifier. Auto-generated if empty.
        node_role : str
            Role for the token holder (``"primary"`` or ``"worker"``).
        expiry_hours : int, optional
            Token validity in hours. Defaults to config value.
        permissions : list[str], optional
            Permissions granted by this token.

        Returns
        -------
        str
            The encoded token string (base64-safe).
        """
        hours = expiry_hours if expiry_hours is not None else TOKEN_EXPIRY_HOURS
        now = time.time()

        claims = TokenClaims(
            token_id=uuid.uuid4().hex[:16],
            cluster_id=cluster_id or uuid.uuid4().hex[:12],
            node_role=node_role,
            issued_at=now,
            expires_at=now + hours * 3600,
            permissions=permissions or ["join", "heartbeat", "inference"],
            issuer_node_id=issuer_node_id,
        )

        token = self._encode(claims)

        # Persist token metadata
        self._save_token_record(claims)
        logger.info(
            "Generated token %s for cluster %s (role=%s, expires in %dh)",
            claims.token_id, claims.cluster_id, node_role, hours,
        )

        return token

    # ------------------------------------------------------------------
    # Token validation
    # ------------------------------------------------------------------

    def validate_token(self, token: str) -> Tuple[bool, Optional[TokenClaims]]:
        """Validate a token and return its claims.

        Returns
        -------
        (bool, TokenClaims | None)
            (True, claims) if valid; (False, None) if invalid.
        """
        claims = self._decode(token)
        if claims is None:
            logger.warning("Token validation failed: invalid signature or format")
            return False, None

        if claims.is_expired:
            logger.warning("Token %s has expired", claims.token_id)
            return False, None

        if claims.token_id in self._revoked:
            logger.warning("Token %s has been revoked", claims.token_id)
            return False, None

        return True, claims

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def revoke_token(self, token_id: str) -> bool:
        """Revoke a specific token by its ID."""
        self._revoked.add(token_id)
        self._save_revocation_list()
        logger.info("Revoked token: %s", token_id)
        return True

    def list_active_tokens(self) -> List[TokenClaims]:
        """List all non-expired, non-revoked tokens."""
        tokens: List[TokenClaims] = []
        records_dir = self._token_dir / "records"
        if not records_dir.exists():
            return tokens

        now = time.time()
        for f in records_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                claims = TokenClaims(**data)
                if not claims.is_expired and claims.token_id not in self._revoked:
                    tokens.append(claims)
            except Exception:
                continue

        return tokens

    # ------------------------------------------------------------------
    # Encoding / Decoding (HMAC-SHA256 signed JSON)
    # ------------------------------------------------------------------

    def _encode(self, claims: TokenClaims) -> str:
        """Encode claims into a signed token string."""
        import base64

        payload = json.dumps(claims.to_dict(), separators=(",", ":"), sort_keys=True)
        payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()

        signature = hmac.new(
            self._secret.encode(), payload_b64.encode(), hashlib.sha256
        ).hexdigest()

        return f"{payload_b64}.{signature}"

    def _decode(self, token: str) -> Optional[TokenClaims]:
        """Decode and verify a token string."""
        import base64

        parts = token.strip().split(".")
        if len(parts) != 2:
            return None

        payload_b64, signature = parts

        # Verify signature
        expected_sig = hmac.new(
            self._secret.encode(), payload_b64.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        try:
            payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
            return TokenClaims(**payload)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Secret management
    # ------------------------------------------------------------------

    def _load_or_create_secret(self) -> str:
        """Load signing secret from file/env, or create a new one."""
        # Check environment override
        env_secret = os.environ.get(TOKEN_SECRET_ENV)
        if env_secret:
            return env_secret

        # Check file
        secret_file = self._token_dir / ".secret"
        if secret_file.exists():
            return secret_file.read_text(encoding="utf-8").strip()

        # Generate new secret
        secret = secrets.token_hex(32)
        self._token_dir.mkdir(parents=True, exist_ok=True)
        secret_file.write_text(secret, encoding="utf-8")
        # Restrict permissions on Unix
        try:
            os.chmod(str(secret_file), 0o600)
        except (OSError, AttributeError):
            pass

        logger.info("Generated new signing secret")
        return secret

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _save_token_record(self, claims: TokenClaims) -> None:
        """Save token metadata to disk."""
        records_dir = self._token_dir / "records"
        records_dir.mkdir(parents=True, exist_ok=True)
        record_file = records_dir / f"{claims.token_id}.json"
        record_file.write_text(
            json.dumps(claims.to_dict(), indent=2),
            encoding="utf-8",
        )

    def _save_revocation_list(self) -> None:
        """Persist the revocation list."""
        revoke_file = self._token_dir / "revoked.json"
        revoke_file.write_text(
            json.dumps(list(self._revoked)),
            encoding="utf-8",
        )

    def _load_revocation_list(self) -> None:
        """Load the revocation list from disk."""
        revoke_file = self._token_dir / "revoked.json"
        if revoke_file.exists():
            try:
                data = json.loads(revoke_file.read_text(encoding="utf-8"))
                self._revoked = set(data)
            except Exception:
                self._revoked = set()
