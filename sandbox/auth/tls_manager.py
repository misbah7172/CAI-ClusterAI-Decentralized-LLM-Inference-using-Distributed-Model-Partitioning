"""
TLS certificate management for CAI Sandbox inter-node communication.

Generates a self-signed CA for the cluster and issues per-node
certificates so all gRPC / REST traffic is encrypted.

Usage::

    tls = TLSManager()
    tls.generate_ca(cluster_id="my-cluster")
    node_cert, node_key = tls.generate_node_cert("worker-abc12345")
"""

from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from sandbox.config import CERT_DIR

logger = logging.getLogger(__name__)


class TLSManager:
    """Manages TLS certificates for secure inter-node communication.

    Parameters
    ----------
    cert_dir : Path
        Directory for storing certificates and keys.
    """

    def __init__(self, cert_dir: Optional[Path] = None):
        self._cert_dir = cert_dir or CERT_DIR
        self._cert_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # CA management
    # ------------------------------------------------------------------

    @property
    def ca_cert_path(self) -> Path:
        return self._cert_dir / "ca.crt"

    @property
    def ca_key_path(self) -> Path:
        return self._cert_dir / "ca.key"

    @property
    def has_ca(self) -> bool:
        return self.ca_cert_path.exists() and self.ca_key_path.exists()

    def generate_ca(
        self,
        cluster_id: str = "Cai-sandbox",
        validity_days: int = 3650,
    ) -> Tuple[Path, Path]:
        """Generate a self-signed CA certificate for the cluster.

        Returns (cert_path, key_path).
        """
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
        except ImportError:
            logger.warning(
                "cryptography package not installed. TLS disabled. "
                "Install with: pip install cryptography"
            )
            return self._generate_placeholder_ca()

        # Generate CA private key
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

        # Generate CA certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CAI Sandbox"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"CAI Sandbox CA ({cluster_id})"),
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        ca_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, key_cert_sign=True, crl_sign=True,
                    content_commitment=False, key_encipherment=False,
                    data_encipherment=False, key_agreement=False,
                    encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .sign(ca_key, hashes.SHA256())
        )

        # Write CA cert
        self.ca_cert_path.write_bytes(
            ca_cert.public_bytes(serialization.Encoding.PEM)
        )

        # Write CA key (restricted permissions)
        self.ca_key_path.write_bytes(
            ca_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        try:
            os.chmod(str(self.ca_key_path), 0o600)
        except (OSError, AttributeError):
            pass

        logger.info("Generated CA certificate for cluster '%s'", cluster_id)
        return self.ca_cert_path, self.ca_key_path

    def generate_node_cert(
        self,
        node_id: str,
        san_ips: Optional[list[str]] = None,
        san_dns: Optional[list[str]] = None,
        validity_days: int = 365,
    ) -> Tuple[Path, Path]:
        """Issue a node certificate signed by the cluster CA.

        Parameters
        ----------
        node_id : str
            Unique node identifier (used as CN).
        san_ips : list[str], optional
            IP addresses to include as Subject Alternative Names.
        san_dns : list[str], optional
            DNS names to include as Subject Alternative Names.

        Returns
        -------
        (cert_path, key_path)
        """
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            import ipaddress
        except ImportError:
            logger.warning("cryptography package not available; generating placeholder cert")
            return self._generate_placeholder_node_cert(node_id)

        if not self.has_ca:
            logger.info("No CA found; generating one first")
            self.generate_ca()

        # Load CA
        ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())
        ca_key = serialization.load_pem_private_key(self.ca_key_path.read_bytes(), password=None)

        # Generate node key
        node_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        # Build SANs
        sans: list[x509.GeneralName] = [x509.DNSName(node_id)]
        for dns in (san_dns or []):
            sans.append(x509.DNSName(dns))
        sans.append(x509.DNSName("localhost"))
        for ip_str in (san_ips or []):
            try:
                sans.append(x509.IPAddress(ipaddress.ip_address(ip_str)))
            except ValueError:
                pass
        # Always include loopback
        sans.append(x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")))

        subject = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CAI Sandbox"),
            x509.NameAttribute(NameOID.COMMON_NAME, node_id),
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        node_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(node_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName(sans), critical=False)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, key_encipherment=True,
                    content_commitment=False, data_encipherment=False,
                    key_agreement=False, key_cert_sign=False, crl_sign=False,
                    encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256())
        )

        # Write node cert and key
        node_dir = self._cert_dir / "nodes"
        node_dir.mkdir(exist_ok=True)
        cert_path = node_dir / f"{node_id}.crt"
        key_path = node_dir / f"{node_id}.key"

        cert_path.write_bytes(node_cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            node_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        try:
            os.chmod(str(key_path), 0o600)
        except (OSError, AttributeError):
            pass

        logger.info("Generated node certificate for '%s'", node_id)
        return cert_path, key_path

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_cert(self, cert_path: Path) -> bool:
        """Verify a certificate was signed by the cluster CA."""
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives.asymmetric import padding

            if not self.has_ca:
                return False

            ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())
            node_cert = x509.load_pem_x509_certificate(cert_path.read_bytes())

            # Verify signature
            ca_cert.public_key().verify(
                node_cert.signature,
                node_cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                node_cert.signature_hash_algorithm,
            )
            return True
        except Exception as exc:
            logger.debug("Certificate verification failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # gRPC credential helpers
    # ------------------------------------------------------------------

    def get_server_credentials(self, node_id: str):
        """Return gRPC server credentials for a node."""
        import grpc

        node_dir = self._cert_dir / "nodes"
        cert_path = node_dir / f"{node_id}.crt"
        key_path = node_dir / f"{node_id}.key"

        if not cert_path.exists() or not key_path.exists():
            self.generate_node_cert(node_id)

        server_cert = cert_path.read_bytes()
        server_key = key_path.read_bytes()
        ca_cert = self.ca_cert_path.read_bytes() if self.has_ca else None

        return grpc.ssl_server_credentials(
            [(server_key, server_cert)],
            root_certificates=ca_cert,
            require_client_auth=False,
        )

    def get_channel_credentials(self):
        """Return gRPC channel credentials for connecting to a node."""
        import grpc

        if not self.has_ca:
            return grpc.ssl_channel_credentials()

        ca_cert = self.ca_cert_path.read_bytes()
        return grpc.ssl_channel_credentials(root_certificates=ca_cert)

    # ------------------------------------------------------------------
    # Placeholders (when cryptography is unavailable)
    # ------------------------------------------------------------------

    def _generate_placeholder_ca(self) -> Tuple[Path, Path]:
        """Write placeholder files when cryptography is unavailable."""
        self.ca_cert_path.write_text("# TLS disabled — install cryptography package\n")
        self.ca_key_path.write_text("# TLS disabled — install cryptography package\n")
        return self.ca_cert_path, self.ca_key_path

    def _generate_placeholder_node_cert(self, node_id: str) -> Tuple[Path, Path]:
        node_dir = self._cert_dir / "nodes"
        node_dir.mkdir(exist_ok=True)
        cert_path = node_dir / f"{node_id}.crt"
        key_path = node_dir / f"{node_id}.key"
        cert_path.write_text("# TLS disabled\n")
        key_path.write_text("# TLS disabled\n")
        return cert_path, key_path
