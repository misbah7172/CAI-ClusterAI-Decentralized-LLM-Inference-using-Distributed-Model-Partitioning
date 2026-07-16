"""
Unit tests for CAI Sandbox Platform components.
"""

import tempfile
from pathlib import Path
import pytest

from sandbox.config import SandboxConfig, ClusterMode, NodeRole, NodeState
from sandbox.auth.token_manager import TokenManager, TokenClaims
from sandbox.auth.tls_manager import TLSManager
from sandbox.discovery.cluster_registry import ClusterRegistry, RegisteredNode
from sandbox.agent.hardware_reporter import HardwareReporter, HardwareReport


class TestSandboxConfig:
    """Tests for SandboxConfig."""

    def test_default_config(self):
        config = SandboxConfig()
        assert config.mode == ClusterMode.SINGLE
        assert config.role == NodeRole.PRIMARY
        assert config.grpc_port == 50100
        assert config.rest_port == 8100

    def test_ensure_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config = SandboxConfig(
                data_dir=tmpdir_path,
                cert_dir=tmpdir_path / "certs",
                token_dir=tmpdir_path / "tokens",
            )
            config.ensure_dirs()
            assert (tmpdir_path / "certs").exists()
            assert (tmpdir_path / "tokens").exists()
            assert (tmpdir_path / "models").exists()
            assert (tmpdir_path / "state").exists()


class TestTokenManager:
    """Tests for TokenManager."""

    def test_token_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TokenManager(token_dir=Path(tmpdir))

            # Generate token
            token = tm.generate_cluster_token(cluster_id="test-cluster", node_role="worker", expiry_hours=1)
            assert isinstance(token, str)
            assert len(token) > 10

            # Validate token — returns (bool, TokenClaims)
            valid, claims = tm.validate_token(token)
            assert valid is True
            assert isinstance(claims, TokenClaims)
            assert claims.cluster_id == "test-cluster"
            assert claims.node_role == "worker"

            # Check listing — returns List[TokenClaims]
            active_tokens = tm.list_active_tokens()
            assert len(active_tokens) == 1
            assert isinstance(active_tokens[0], TokenClaims)
            assert active_tokens[0].cluster_id == "test-cluster"

    def test_token_expiry(self):
        """Test that expired tokens are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TokenManager(token_dir=Path(tmpdir))
            # Generate a token with 0 expiry hours (immediate expiry)
            token = tm.generate_cluster_token(cluster_id="test-cluster", node_role="worker", expiry_hours=0)
            valid, claims = tm.validate_token(token)
            # Should be expired immediately
            assert valid is False
            assert claims is None

    def test_token_revocation(self):
        """Test that revoked tokens are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TokenManager(token_dir=Path(tmpdir))
            token = tm.generate_cluster_token(cluster_id="test-cluster", node_role="worker", expiry_hours=1)

            valid, claims = tm.validate_token(token)
            assert valid is True
            token_id = claims.token_id

            # Revoke the token
            tm.revoke_token(token_id)

            # Should now be invalid
            valid2, claims2 = tm.validate_token(token)
            assert valid2 is False


class TestTLSManager:
    """Tests for TLSManager."""

    def test_tls_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TLSManager(cert_dir=Path(tmpdir))

            # Generate CA
            ca_cert_path, ca_key_path = tm.generate_ca()
            assert ca_cert_path.exists()
            assert ca_key_path.exists()

            # Generate Node cert
            node_cert_path, node_key_path = tm.generate_node_cert(node_id="test-node-1")
            assert node_cert_path.exists()
            assert node_key_path.exists()

            # Verify cert
            assert tm.verify_cert(node_cert_path) is True


class TestClusterRegistry:
    """Tests for ClusterRegistry."""

    def test_registry_operations(self):
        registry = ClusterRegistry()

        # Initial empty state
        assert len(registry.get_all_nodes()) == 0

        # Add node via keyword arguments (matching the actual API)
        node = registry.add_node(
            node_id="node-1",
            role="worker",
            address="192.168.1.100:50101",
            hardware={"gpu_vram_mb": 4096.0, "gpu_type": "RTX 3060", "has_gpu": True, "ram_mb": 16384.0, "cpu_cores": 8},
            state=NodeState.CONNECTING,
        )
        assert isinstance(node, RegisteredNode)
        assert len(registry.get_all_nodes()) == 1

        # Query node
        fetched = registry.get_node("node-1")
        assert fetched is not None
        assert fetched.address == "192.168.1.100:50101"
        assert fetched.gpu_vram_mb == 4096.0

        # Update state — actual method is update_state(), not update_node_state()
        assert registry.update_state("node-1", NodeState.ACTIVE) is True
        assert registry.get_node("node-1").state == NodeState.ACTIVE
        assert len(registry.get_active_nodes()) == 1

        # Remove node
        removed = registry.remove_node("node-1")
        assert removed is not None
        assert len(registry.get_all_nodes()) == 0

    def test_heartbeat_updates(self):
        """Test that heartbeats update node state correctly."""
        registry = ClusterRegistry()
        registry.add_node(
            node_id="hb-node",
            role="worker",
            state=NodeState.AUTHENTICATED,
        )
        # First heartbeat should auto-transition AUTHENTICATED -> ACTIVE
        result = registry.update_heartbeat("hb-node", load_pct=30.0, power_draw_w=50.0)
        assert result is True
        assert registry.get_node("hb-node").state == NodeState.ACTIVE
        assert registry.get_node("hb-node").load_pct == 30.0

    def test_stale_cleanup(self):
        """Test that stale nodes are marked as disconnected."""
        import time
        registry = ClusterRegistry(expiry_s=0.05)  # 50ms expiry for fast test
        registry.add_node(node_id="stale-node", role="worker", state=NodeState.AUTHENTICATED)
        # Force into ACTIVE state via heartbeat
        registry.update_heartbeat("stale-node")
        # Force last heartbeat to old value
        registry.get_node("stale-node").last_heartbeat = time.time() - 1.0
        stale = registry.cleanup_stale()
        assert "stale-node" in stale
        assert registry.get_node("stale-node").state == NodeState.DISCONNECTED


class TestHardwareReporter:
    """Tests for HardwareReporter."""

    def test_report_generation(self):
        """Test that HardwareReporter generates a valid report.

        Uses get_report() which calls _scan() only if no cached value.
        Does NOT call start() to avoid spinning up a background thread.
        """
        reporter = HardwareReporter(node_id="test-hw-node")
        # get_report() will trigger one synchronous scan internally
        report = reporter.get_report()

        assert report.node_id == "test-hw-node"
        assert report.cpu_cores > 0
        assert report.ram_mb > 0
        assert isinstance(report.gpu_type, str)
        assert isinstance(report.power_draw_w, float)

        # Verify serialization
        d = report.to_dict()
        assert d["node_id"] == "test-hw-node"
        assert "cpu_cores" in d
        assert "ram_mb" in d

    def test_report_fields(self):
        """Test that all expected fields are present and typed correctly."""
        report = HardwareReport(
            node_id="mock-node",
            cpu_cores=8,
            ram_mb=16384.0,
            gpu_type="RTX 3090",
            gpu_vram_mb=24576.0,
            has_gpu=True,
            power_draw_w=200.0,
        )
        assert report.load_pct >= 0.0
        assert report.usable_memory_mb > 0  # GPU VRAM - 500 MB reserve
        d = report.to_dict()
        assert d["gpu_type"] == "RTX 3090"
        assert d["has_gpu"] is True

    def test_reporter_start_stop(self):
        """Test that the reporter can start and stop cleanly."""
        reporter = HardwareReporter(node_id="lifecycle-node", interval_s=60.0)
        reporter.start()
        assert reporter._running is True
        assert reporter._thread is not None
        reporter.stop()
        assert reporter._running is False
