"""
Auth middleware for CAI Sandbox REST and gRPC endpoints.

Provides token validation for HTTP headers and gRPC metadata.
"""

from __future__ import annotations

import logging
import time
from http.server import BaseHTTPRequestHandler
from typing import Callable, Optional, Tuple

from sandbox.auth.token_manager import TokenManager, TokenClaims

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Validates Bearer tokens on HTTP requests.

    Usage::

        auth = AuthMiddleware(token_manager)

        # In your HTTP handler:
        ok, claims = auth.authenticate_request(self)
        if not ok:
            return  # 401 already sent
    """

    def __init__(self, token_manager: TokenManager):
        self._token_manager = token_manager
        self._failed_attempts: dict[str, list[float]] = {}
        self._rate_limit_window = 60.0  # seconds
        self._rate_limit_max = 10  # max failures per window

    def authenticate_request(
        self,
        handler: BaseHTTPRequestHandler,
    ) -> Tuple[bool, Optional[TokenClaims]]:
        """Authenticate an HTTP request via Authorization header.

        Sends 401/429 response and returns (False, None) on failure.
        """
        # Extract client IP for rate limiting
        client_ip = handler.client_address[0] if handler.client_address else "unknown"

        # Rate limit check
        if self._is_rate_limited(client_ip):
            handler.send_response(429)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Retry-After", "60")
            handler.end_headers()
            handler.wfile.write(b'{"error":"Too many failed authentication attempts"}')
            return False, None

        # Extract token
        auth_header = handler.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            self._record_failure(client_ip)
            handler.send_response(401)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("WWW-Authenticate", "Bearer")
            handler.end_headers()
            handler.wfile.write(b'{"error":"Missing or invalid Authorization header"}')
            return False, None

        token = auth_header[7:].strip()
        valid, claims = self._token_manager.validate_token(token)

        if not valid:
            self._record_failure(client_ip)
            logger.warning("Authentication failed from %s", client_ip)
            handler.send_response(401)
            handler.send_header("Content-Type", "application/json")
            handler.end_headers()
            handler.wfile.write(b'{"error":"Invalid or expired token"}')
            return False, None

        return True, claims

    def validate_token_string(self, token: str) -> Tuple[bool, Optional[TokenClaims]]:
        """Validate a raw token string (for gRPC or WebSocket)."""
        return self._token_manager.validate_token(token)

    # ------------------------------------------------------------------
    # gRPC interceptor
    # ------------------------------------------------------------------

    def grpc_interceptor(self):
        """Return a gRPC server interceptor that validates tokens.

        Usage::

            server = grpc.server(
                ...,
                interceptors=[auth.grpc_interceptor()],
            )
        """
        return _GrpcAuthInterceptor(self._token_manager)

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _record_failure(self, client_ip: str) -> None:
        """Record a failed auth attempt."""
        now = time.time()
        if client_ip not in self._failed_attempts:
            self._failed_attempts[client_ip] = []
        self._failed_attempts[client_ip].append(now)
        # Prune old entries
        cutoff = now - self._rate_limit_window
        self._failed_attempts[client_ip] = [
            t for t in self._failed_attempts[client_ip] if t > cutoff
        ]

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if a client IP has exceeded the failure rate limit."""
        if client_ip not in self._failed_attempts:
            return False
        now = time.time()
        cutoff = now - self._rate_limit_window
        recent = [t for t in self._failed_attempts[client_ip] if t > cutoff]
        self._failed_attempts[client_ip] = recent
        return len(recent) >= self._rate_limit_max


class _GrpcAuthInterceptor:
    """gRPC server interceptor for token-based authentication.

    Expects the token in metadata key ``authorization``.
    """

    def __init__(self, token_manager: TokenManager):
        self._token_manager = token_manager

    def intercept_service(self, continuation, handler_call_details):
        """Intercept incoming gRPC calls and validate auth metadata."""
        import grpc

        metadata = dict(handler_call_details.invocation_metadata or [])
        token = metadata.get("authorization", "")

        if token.startswith("Bearer "):
            token = token[7:]

        # Allow health checks without auth
        method = handler_call_details.method or ""
        if method.endswith("/HealthCheck") or method.endswith("/GetStatus"):
            return continuation(handler_call_details)

        if not token:
            return self._abort(grpc.StatusCode.UNAUTHENTICATED, "Missing auth token")

        valid, claims = self._token_manager.validate_token(token)
        if not valid:
            return self._abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or expired token")

        return continuation(handler_call_details)

    @staticmethod
    def _abort(code, message):
        """Create an aborting handler."""
        import grpc

        def _handler(request, context):
            context.abort(code, message)

        return grpc.unary_unary_rpc_method_handler(_handler)
