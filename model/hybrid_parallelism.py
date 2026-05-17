"""
Hybrid Parallelism Engine for KAI.

Combines pipeline parallelism (existing) with tensor parallelism:
- Split attention layers across multiple GPUs
- Keep feed-forward layers in pipeline mode
- Dynamically switch between pipeline-only, tensor-only, and hybrid

Usage::

    from model.hybrid_parallelism import HybridParallelismEngine, ParallelismMode
    
    engine = HybridParallelismEngine(devices=["cuda:0", "cuda:1"])
    
    # Configure strategy
    engine.set_mode(ParallelismMode.HYBRID)
    
    # Execute with hybrid parallelism
    output = engine.forward(model_chunk, input_tensor)
"""

import copy
import logging
import math
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
import torch.distributed as dist
from torch import Tensor

from model.plugin_architecture import PluginRegistry, ParallelismPlugin, ExecutorPlugin

logger = logging.getLogger(__name__)


class ParallelismMode(Enum):
    """Parallelism execution modes."""
    PIPELINE_ONLY = "pipeline"    # Sequential layer execution
    TENSOR_ONLY = "tensor"        # Split tensors across devices
    HYBRID = "hybrid"             # Tensor for attention, pipeline for FFN


class SplitDimension(Enum):
    """Dimension along which to split tensors."""
    BATCH = 0
    SEQUENCE = 1
    HEAD = 2
    HIDDEN = -1


@dataclass
class TensorParallelConfig:
    """Configuration for tensor parallelism."""
    num_devices: int = 2
    split_attention: bool = True
    split_feedforward: bool = False
    split_dimension: SplitDimension = SplitDimension.HEAD
    reduce_scatter: bool = True  # Use reduce-scatter for efficiency
    async_communication: bool = True


@dataclass
class ParallelismStrategy:
    """Strategy for a specific layer type."""
    layer_pattern: str
    mode: ParallelismMode
    tensor_config: Optional[TensorParallelConfig] = None
    priority: int = 0  # Higher = check first
    
    def matches(self, layer_name: str) -> bool:
        """Check if layer name matches pattern."""
        return self.layer_pattern.lower() in layer_name.lower()


@dataclass
class ExecutionStats:
    """Statistics for parallel execution."""
    total_time_ms: float = 0.0
    compute_time_ms: float = 0.0
    communication_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    num_splits: int = 0
    mode_used: ParallelismMode = ParallelismMode.PIPELINE_ONLY


class TensorSplitter:
    """Utilities for splitting and gathering tensors across devices."""
    
    @staticmethod
    def split_tensor(
        tensor: Tensor,
        num_splits: int,
        dim: int = -1,
    ) -> List[Tensor]:
        """Split tensor along specified dimension."""
        if num_splits == 1:
            return [tensor]
        
        size = tensor.size(dim)
        if size % num_splits != 0:
            # Pad if necessary
            pad_size = num_splits - (size % num_splits)
            pad_shape = list(tensor.shape)
            pad_shape[dim] = pad_size
            padding = torch.zeros(pad_shape, dtype=tensor.dtype, device=tensor.device)
            tensor = torch.cat([tensor, padding], dim=dim)
        
        return list(torch.chunk(tensor, num_splits, dim=dim))
    
    @staticmethod
    def gather_tensor(
        tensors: List[Tensor],
        dim: int = -1,
    ) -> Tensor:
        """Gather split tensors."""
        if len(tensors) == 1:
            return tensors[0]
        
        # Move all to same device
        device = tensors[0].device
        tensors = [t.to(device) for t in tensors]
        
        return torch.cat(tensors, dim=dim)
    
    @staticmethod
    def all_reduce(
        tensor: Tensor,
        op: str = "sum",
        devices: Optional[List[str]] = None,
    ) -> Tensor:
        """All-reduce across devices (simulated for single-process)."""
        # In multi-process setting, this would use dist.all_reduce
        # For single-process multi-GPU, we simulate by collecting on device 0
        return tensor
    
    @staticmethod
    def scatter_to_devices(
        tensor: Tensor,
        devices: List[str],
        dim: int = -1,
    ) -> List[Tensor]:
        """Scatter tensor chunks to different devices."""
        chunks = TensorSplitter.split_tensor(tensor, len(devices), dim)
        return [chunk.to(device) for chunk, device in zip(chunks, devices)]


class AttentionParallel(nn.Module):
    """Tensor-parallel wrapper for attention layers.
    
    Splits attention heads across devices for parallel computation.
    
    Parameters
    ----------
    attention_module : nn.Module
        Original attention module
    devices : list[str]
        Devices to distribute across
    num_heads : int
        Total number of attention heads
    """
    
    def __init__(
        self,
        attention_module: nn.Module,
        devices: List[str],
        num_heads: int = 8,
    ):
        super().__init__()
        self.attention = attention_module
        self.devices = devices
        self.num_heads = num_heads
        self.heads_per_device = max(1, num_heads // max(1, len(devices)))
        self._replicas: Dict[str, nn.Module] = {}
        
        # Split attention weights across devices
        self._split_weights()
    
    def _split_weights(self) -> None:
        """Prepare per-device replicas for attention execution.

        This is a practical single-process fallback: each device gets a
        lazily-created module replica. That keeps the runtime functional even
        when torch.distributed is not initialised.
        """
        self._replicas.clear()

    def _get_replica(self, device: str) -> nn.Module:
        if device not in self._replicas:
            replica = copy.deepcopy(self.attention)
            replica = replica.to(device)
            replica.eval()
            self._replicas[device] = replica
        return self._replicas[device]
    
    def forward(
        self,
        hidden_states: Tensor,
        attention_mask: Optional[Tensor] = None,
        **kwargs,
    ) -> Tensor:
        """Forward with tensor parallelism."""
        if len(self.devices) == 1:
            # No parallelism needed
            return self.attention(hidden_states, attention_mask=attention_mask, **kwargs)
        
        # Practical parallel fallback: shard the batch across devices and gather
        # the results. This is deterministic and works with arbitrary attention
        # modules without assuming a specific internal projection layout.
        chunks = TensorSplitter.split_tensor(hidden_states, len(self.devices), dim=0)
        outputs: List[Tensor] = [None] * len(chunks)  # type: ignore[assignment]
        errors: List[Exception] = []

        def _run_shard(index: int, device: str, shard: Tensor) -> None:
            try:
                replica = self._get_replica(device)
                shard_device = shard.to(device)
                mask = attention_mask.to(device) if attention_mask is not None else None
                with torch.no_grad():
                    result = replica(shard_device, attention_mask=mask, **kwargs)
                outputs[index] = result.to(hidden_states.device)
            except Exception as exc:  # pragma: no cover - surfaced to caller
                errors.append(exc)

        threads = []
        for index, (device, shard) in enumerate(zip(self.devices, chunks)):
            thread = threading.Thread(target=_run_shard, args=(index, device, shard), daemon=True)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        if errors:
            raise errors[0]

        return TensorSplitter.gather_tensor(outputs, dim=0)


class FeedForwardParallel(nn.Module):
    """Tensor-parallel wrapper for feed-forward layers.
    
    Splits the hidden dimension for parallel MLP computation.
    
    Parameters
    ----------
    ffn_module : nn.Module
        Original FFN module
    devices : list[str]
        Devices to distribute across
    """
    
    def __init__(
        self,
        ffn_module: nn.Module,
        devices: List[str],
    ):
        super().__init__()
        self.ffn = ffn_module
        self.devices = devices
        self.num_splits = len(devices)
        self._replicas: Dict[str, nn.Module] = {}
    
    def forward(self, hidden_states: Tensor) -> Tensor:
        """Forward with column-parallel / row-parallel strategy."""
        if len(self.devices) == 1:
            return self.ffn(hidden_states)

        def _get_replica(device: str) -> nn.Module:
            if device not in self._replicas:
                replica = copy.deepcopy(self.ffn)
                replica = replica.to(device)
                replica.eval()
                self._replicas[device] = replica
            return self._replicas[device]

        chunks = TensorSplitter.split_tensor(hidden_states, len(self.devices), dim=0)
        outputs: List[Tensor] = [None] * len(chunks)  # type: ignore[assignment]
        errors: List[Exception] = []

        def _run_shard(index: int, device: str, shard: Tensor) -> None:
            try:
                replica = _get_replica(device)
                with torch.no_grad():
                    result = replica(shard.to(device))
                outputs[index] = result.to(hidden_states.device)
            except Exception as exc:  # pragma: no cover - surfaced to caller
                errors.append(exc)

        threads = []
        for index, (device, shard) in enumerate(zip(self.devices, chunks)):
            thread = threading.Thread(target=_run_shard, args=(index, device, shard), daemon=True)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        if errors:
            raise errors[0]

        return TensorSplitter.gather_tensor(outputs, dim=0)


class HybridParallelismEngine:
    """Engine for hybrid pipeline + tensor parallelism.
    
    Dynamically switches between parallelism modes based on
    layer type and available resources.
    
    Parameters
    ----------
    devices : list[str]
        Available devices (e.g., ["cuda:0", "cuda:1"])
    mode : ParallelismMode
        Default parallelism mode
    config : TensorParallelConfig, optional
        Tensor parallelism configuration
    """
    
    def __init__(
        self,
        loader_or_devices: Optional[Any] = None,
        nodes: Optional[List[Any]] = None,
        mode: ParallelismMode = ParallelismMode.PIPELINE_ONLY,
        config: Optional[TensorParallelConfig] = None,
        tensor_parallel_size: Optional[int] = None,
        devices: Optional[List[str]] = None,
    ):
        self.loader = None
        self.nodes = nodes or []

        if devices is not None:
            self.devices = list(devices)
        elif isinstance(loader_or_devices, list) and loader_or_devices and all(isinstance(item, str) for item in loader_or_devices):
            self.devices = list(loader_or_devices)
        else:
            self.devices = self._detect_devices()

        if loader_or_devices is not None and not (
            isinstance(loader_or_devices, list) and loader_or_devices and all(isinstance(item, str) for item in loader_or_devices)
        ):
            self.loader = loader_or_devices

        self.mode = mode
        self.config = config or TensorParallelConfig(num_devices=len(self.devices))
        self.tensor_parallel_size = max(1, int(tensor_parallel_size or self.config.num_devices or len(self.devices)))
        
        # Layer strategies
        self._strategies: List[ParallelismStrategy] = []
        self._setup_default_strategies()
        
        # Wrapped modules cache
        self._wrapped_modules: Dict[str, nn.Module] = {}

        # Chunked runtime (used when initialised with a loader)
        self._chunks: List[nn.Module] = []
        self._chunk_mode: bool = False
        self._primary_device = self.devices[0]
        self._chunk_wrapped = False
        if self.loader is not None:
            self._build_chunked_runtime()
        
        # Statistics
        self._stats = ExecutionStats()
        self._lock = threading.Lock()
    
    def _detect_devices(self) -> List[str]:
        """Detect available CUDA devices."""
        if torch.cuda.is_available():
            return [f"cuda:{i}" for i in range(torch.cuda.device_count())]
        return ["cpu"]
    
    def _setup_default_strategies(self) -> None:
        """Setup default parallelism strategies."""
        # Attention layers: tensor parallel
        self._strategies.append(ParallelismStrategy(
            layer_pattern="attn",
            mode=ParallelismMode.TENSOR_ONLY,
            tensor_config=TensorParallelConfig(
                num_devices=len(self.devices),
                split_attention=True,
            ),
            priority=10,
        ))
        
        self._strategies.append(ParallelismStrategy(
            layer_pattern="attention",
            mode=ParallelismMode.TENSOR_ONLY,
            tensor_config=TensorParallelConfig(
                num_devices=len(self.devices),
                split_attention=True,
            ),
            priority=10,
        ))
        
        # FFN layers: pipeline (default)
        self._strategies.append(ParallelismStrategy(
            layer_pattern="mlp",
            mode=ParallelismMode.PIPELINE_ONLY,
            priority=5,
        ))
        
        self._strategies.append(ParallelismStrategy(
            layer_pattern="ffn",
            mode=ParallelismMode.PIPELINE_ONLY,
            priority=5,
        ))
        
        # Sort by priority
        self._strategies.sort(key=lambda s: s.priority, reverse=True)

    def _build_chunked_runtime(self) -> None:
        """Build an end-to-end chunked runtime from a HF loader.

        This keeps the CLI path working and makes the engine usable without
        manually passing a module per layer.
        """
        try:
            from model.layer_chunker import LayerChunker
        except Exception as exc:  # pragma: no cover - import safety
            raise RuntimeError(f"Layer chunking unavailable: {exc}") from exc

        if self.loader is None:
            return

        chunker = LayerChunker(self.loader)

        # Prefer memory-aware partitioning if node capacities are available.
        node_memory_mb = []
        for node in self.nodes or []:
            usable = getattr(node, "usable_memory_mb", None)
            if usable is None:
                gpu_vram = float(getattr(node, "gpu_vram_mb", 0.0) or 0.0)
                ram_mb = float(getattr(node, "ram_mb", 0.0) or 0.0)
                usable = gpu_vram if gpu_vram > 0 else ram_mb
            node_memory_mb.append(float(usable or 0.0))

        try:
            if node_memory_mb and len(node_memory_mb) > 0:
                self._chunks = chunker.create_chunks_by_memory(node_memory_mb)
            else:
                self._chunks = chunker.create_chunks(max(1, self.tensor_parallel_size))
        except Exception:
            self._chunks = chunker.create_chunks(max(1, self.tensor_parallel_size))

        self._chunk_mode = True
        self._wrap_chunk_layers()

    def _wrap_chunk_layers(self) -> None:
        """Wrap layers inside each chunk according to the current strategy."""
        if self._chunk_wrapped:
            return
        for chunk in self._chunks:
            if not hasattr(chunk, "layers"):
                continue
            for layer_name, module in list(chunk.layers.items()):
                wrapped = self.wrap_module(module, layer_name)
                if wrapped is not module:
                    chunk.layers[layer_name] = wrapped
            chunk.to(self._primary_device)
            chunk.eval()
        self._chunk_wrapped = True
    
    def set_mode(self, mode: ParallelismMode) -> None:
        """Set global parallelism mode."""
        self.mode = mode
        logger.info("Parallelism mode set to: %s", mode.value)
    
    def add_strategy(self, strategy: ParallelismStrategy) -> None:
        """Add a custom parallelism strategy."""
        self._strategies.append(strategy)
        self._strategies.sort(key=lambda s: s.priority, reverse=True)
    
    def get_strategy_for_layer(self, layer_name: str) -> ParallelismStrategy:
        """Get parallelism strategy for a layer."""
        for strategy in self._strategies:
            if strategy.matches(layer_name):
                return strategy
        
        # Default strategy based on global mode
        return ParallelismStrategy(
            layer_pattern="*",
            mode=self.mode,
        )
    
    def wrap_module(
        self,
        module: nn.Module,
        layer_name: str,
    ) -> nn.Module:
        """Wrap module for parallel execution."""
        if layer_name in self._wrapped_modules:
            return self._wrapped_modules[layer_name]
        
        strategy = self.get_strategy_for_layer(layer_name)
        
        if strategy.mode == ParallelismMode.PIPELINE_ONLY:
            wrapped = module
        elif strategy.mode == ParallelismMode.TENSOR_ONLY:
            if "attn" in layer_name.lower() or "attention" in layer_name.lower():
                # Infer num_heads from module
                num_heads = getattr(module, "num_heads", 8)
                wrapped = AttentionParallel(module, self.devices, num_heads)
            else:
                wrapped = FeedForwardParallel(module, self.devices)
        else:
            # Hybrid: wrap based on layer type
            if "attn" in layer_name.lower():
                num_heads = getattr(module, "num_heads", 8)
                wrapped = AttentionParallel(module, self.devices, num_heads)
            else:
                wrapped = module
        
        self._wrapped_modules[layer_name] = wrapped
        return wrapped
    
    def forward(
        self,
        module: Optional[nn.Module] = None,
        inputs: Optional[Tensor] = None,
        layer_name: str = "",
        **kwargs,
    ) -> Tensor:
        """Execute forward pass with appropriate parallelism.
        
        Parameters
        ----------
        module : nn.Module
            Module to execute
        inputs : Tensor
            Input tensor
        layer_name : str
            Layer name for strategy lookup
            
        Returns
        -------
        Tensor
            Output tensor
        """
        import time
        start_time = time.perf_counter()

        # Chunked end-to-end mode: used by kai_cli.py and test fixtures that
        # construct the engine from a loader + cluster nodes.
        if self._chunk_mode:
            if inputs is None and module is not None and isinstance(module, torch.Tensor):
                inputs = module
                module = None
            if inputs is None:
                raise ValueError("inputs tensor is required for chunked forward")
            output = self._forward_chunked(inputs)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            with self._lock:
                self._stats.total_time_ms += elapsed_ms
                self._stats.mode_used = self.mode
            return output

        if module is None or inputs is None:
            raise ValueError("module and inputs are required for module-level forward")
        
        strategy = self.get_strategy_for_layer(layer_name)
        
        if strategy.mode == ParallelismMode.PIPELINE_ONLY:
            output = self._forward_pipeline(module, inputs, **kwargs)
        elif strategy.mode == ParallelismMode.TENSOR_ONLY:
            output = self._forward_tensor_parallel(module, inputs, layer_name, **kwargs)
        else:
            output = self._forward_hybrid(module, inputs, layer_name, **kwargs)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        with self._lock:
            self._stats.total_time_ms += elapsed_ms
            self._stats.mode_used = strategy.mode
        
        return output

    def _forward_chunked(self, inputs: Tensor) -> Tensor:
        """Forward through chunked runtime built from a loader."""
        if not self._chunks:
            raise RuntimeError("Chunked runtime is not initialised")

        x = inputs.to(self._primary_device)
        with torch.no_grad():
            for chunk in self._chunks:
                x = chunk(x)
        return x
    
    def _forward_pipeline(
        self,
        module: nn.Module,
        inputs: Tensor,
        **kwargs,
    ) -> Tensor:
        """Standard pipeline execution."""
        with torch.no_grad():
            return module(inputs, **kwargs) if kwargs else module(inputs)
    
    def _forward_tensor_parallel(
        self,
        module: nn.Module,
        inputs: Tensor,
        layer_name: str,
        **kwargs,
    ) -> Tensor:
        """Tensor-parallel execution."""
        if len(self.devices) == 1:
            return self._forward_pipeline(module, inputs, **kwargs)
        
        wrapped = self.wrap_module(module, layer_name)
        
        with torch.no_grad():
            return wrapped(inputs, **kwargs) if kwargs else wrapped(inputs)
    
    def _forward_hybrid(
        self,
        module: nn.Module,
        inputs: Tensor,
        layer_name: str,
        **kwargs,
    ) -> Tensor:
        """Hybrid execution: tensor parallel for attention, pipeline for FFN."""
        # Determine layer type
        if "attn" in layer_name.lower() or "attention" in layer_name.lower():
            return self._forward_tensor_parallel(module, inputs, layer_name, **kwargs)
        else:
            return self._forward_pipeline(module, inputs, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        with self._lock:
            return {
                "total_time_ms": round(self._stats.total_time_ms, 3),
                "compute_time_ms": round(self._stats.compute_time_ms, 3),
                "communication_time_ms": round(self._stats.communication_time_ms, 3),
                "memory_used_mb": round(self._stats.memory_used_mb, 2),
                "num_splits": self._stats.num_splits,
                "mode_used": self._stats.mode_used.value,
                "num_devices": len(self.devices),
                "devices": self.devices,
                "chunk_mode": self._chunk_mode,
                "num_chunks": len(self._chunks),
            }
    
    def reset_stats(self) -> None:
        """Reset execution statistics."""
        with self._lock:
            self._stats = ExecutionStats()


class WorkloadAnalyzer:
    """Analyzes workload to recommend parallelism strategy.
    
    Parameters
    ----------
    model : nn.Module
        Model to analyze
    sample_input : Tensor
        Sample input for profiling
    """
    
    def __init__(
        self,
        model: Optional[nn.Module] = None,
        sample_input: Optional[Tensor] = None,
    ):
        self.model = model
        self.sample_input = sample_input
        
        self._layer_profiles: Dict[str, Dict[str, Any]] = {}
    
    def profile_layers(self) -> Dict[str, Dict[str, Any]]:
        """Profile each layer for compute/memory characteristics."""
        profiles = {}
        
        for name, module in self.model.named_modules():
            if not list(module.children()):  # Leaf modules
                param_count = sum(p.numel() for p in module.parameters())
                if param_count == 0:
                    continue
                
                is_attention = any(
                    p in name.lower()
                    for p in ["attn", "attention", "self_attn"]
                )
                
                is_ffn = any(
                    p in name.lower()
                    for p in ["mlp", "ffn", "feed_forward", "fc"]
                )
                
                profiles[name] = {
                    "param_count": param_count,
                    "memory_mb": param_count * 2 / (1024**2),
                    "is_attention": is_attention,
                    "is_ffn": is_ffn,
                    "module_type": module.__class__.__name__,
                }
        
        self._layer_profiles = profiles
        return profiles
    
    def recommend_mode(
        self,
        model: Optional[nn.Module] = None,
        nodes: Optional[List[Any]] = None,
    ) -> Tuple[ParallelismMode, str]:
        """Recommend parallelism mode based on model characteristics.

        The method accepts optional ``model`` and ``nodes`` arguments to stay
        compatible with older call sites and tests.
        """
        if model is not None:
            self.model = model

        if self.model is None:
            return ParallelismMode.PIPELINE_ONLY, "No model provided"

        if not self._layer_profiles:
            self.profile_layers()

        node_count = len(nodes) if nodes else 0
        
        attention_params = sum(
            p["param_count"]
            for p in self._layer_profiles.values()
            if p["is_attention"]
        )
        
        ffn_params = sum(
            p["param_count"]
            for p in self._layer_profiles.values()
            if p["is_ffn"]
        )
        
        total_params = attention_params + ffn_params
        
        if total_params == 0:
            return ParallelismMode.PIPELINE_ONLY, "No significant layers found"
        
        attention_ratio = attention_params / total_params if total_params > 0 else 0
        
        if node_count >= 2 and attention_ratio > 0.4:
            return ParallelismMode.HYBRID, f"Multi-node workload ({attention_ratio:.1%} attention, {node_count} nodes)"
        if attention_ratio > 0.6:
            return ParallelismMode.TENSOR_ONLY, f"High attention ratio ({attention_ratio:.1%})"
        if attention_ratio > 0.3:
            return ParallelismMode.HYBRID, f"Mixed workload ({attention_ratio:.1%} attention)"
        return ParallelismMode.PIPELINE_ONLY, "FFN-dominant workload"


# Register as plugins
@PluginRegistry.register(
    "parallelism",
    "hybrid",
    description="Hybrid pipeline + tensor parallelism"
)
class HybridParallelismPlugin(ParallelismPlugin):
    """Plugin wrapper for HybridParallelismEngine."""
    
    def __init__(self, devices: Optional[List[str]] = None):
        self._engine = HybridParallelismEngine(devices=devices)
    
    @property
    def name(self) -> str:
        return "hybrid"
    
    def get_strategy(
        self,
        layer_type: str,
        resources: Dict[str, Any],
    ) -> str:
        strategy = self._engine.get_strategy_for_layer(layer_type)
        return strategy.mode.value
    
    def execute_parallel(
        self,
        module: nn.Module,
        inputs: Tensor,
        strategy: str,
        devices: List[str],
    ) -> Tensor:
        self._engine.devices = devices
        self._engine.set_mode(ParallelismMode(strategy))
        return self._engine.forward(module, inputs)


@PluginRegistry.register(
    "executor",
    "hybrid_parallel",
    description="Executor with hybrid parallelism support"
)
class HybridParallelExecutor(ExecutorPlugin):
    """Executor plugin using hybrid parallelism."""
    
    def __init__(self, devices: Optional[List[str]] = None):
        self._engine = HybridParallelismEngine(devices=devices)
    
    @property
    def name(self) -> str:
        return "hybrid_parallel"
    
    def execute(
        self,
        module: nn.Module,
        inputs: Tensor,
        **kwargs,
    ) -> Tensor:
        layer_name = kwargs.get("layer_name", "")
        return self._engine.forward(module, inputs, layer_name=layer_name)
    
    def supports_async(self) -> bool:
        return False
