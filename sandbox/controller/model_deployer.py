"""
Model Deployer — orchestrates model loading, partitioning, and inference.

Uses the AutoPartitioner to plan chunk distribution, assigns chunks to
cluster nodes, starts an InferenceGateway, and handles text generation jobs.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import torch

from model.hf_loader import HFModelLoader
from model.layer_chunker import LayerChunker
from model.auto_partitioner import AutoPartitioner
from model.resource_detector import NodeInfo
from model.gateway import InferenceGateway
from sandbox.config import SandboxConfig

logger = logging.getLogger(__name__)


class ModelDeployer:
    """Orchestrates model deployment and inference across CAI Sandbox nodes.

    Parameters
    ----------
    controller : RemoteController
        The cluster controller instance.
    config : SandboxConfig, optional
        Sandbox configuration.
    """

    def __init__(self, controller, config: Optional[SandboxConfig] = None):
        self._controller = controller
        self._config = config or SandboxConfig()
        self._gateways: Dict[str, InferenceGateway] = {}  # deployment_id -> InferenceGateway

    def deploy(
        self,
        model_name: str,
        num_chunks: Optional[int] = None,
        strategy: str = "balanced",
        target_nodes: Optional[List[str]] = None,
        dtype: str = "float16",
    ) -> Dict[str, Any]:
        """Deploy a model across the cluster.

        Parameters
        ----------
        model_name : str
            HuggingFace model name or local path.
        num_chunks : int, optional
            Number of chunks. Defaults to number of available nodes.
        strategy : str
            Deployment strategy ("balanced", "energy", "latency").
        target_nodes : list[str], optional
            Specific node IDs to deploy to.
        dtype : str
            Data type for model weights.

        Returns
        -------
        dict
            Deployment result with placements, success status, etc.
        """
        deployment_id = uuid.uuid4().hex[:12]
        logger.info("Initializing deployment %s for model '%s'", deployment_id, model_name)

        # 1. Load model metadata
        try:
            loader = HFModelLoader(model_name, dtype=dtype)
        except Exception as exc:
            logger.error("Failed to load model %s: %s", model_name, exc)
            return {
                "success": False,
                "message": f"Failed to load model config: {exc}",
                "deployment_id": deployment_id,
            }

        # 2. Query available nodes from controller
        available = self._controller._get_available_nodes(target_nodes)
        if not available:
            return {
                "success": False,
                "message": "No active nodes available in cluster",
                "deployment_id": deployment_id,
            }

        # Map RegisteredNode to NodeInfo for AutoPartitioner
        detector_nodes = []
        for node in available:
            detector_nodes.append(
                NodeInfo(
                    name=node.node_id,
                    gpu_vram_mb=node.gpu_vram_mb,
                    gpu_type=node.gpu_type,
                    ram_mb=node.ram_mb,
                    cpu_cores=node.cpu_cores,
                    has_gpu=node.has_gpu,
                )
            )

        if num_chunks is None:
            num_chunks = len(available)

        # 3. Create Partition Plan using AutoPartitioner or Scheduler
        logger.info("Creating partition plan for %d chunks using %s strategy...", num_chunks, strategy)
        partitioner = AutoPartitioner()
        plan = partitioner.create_plan(loader, detector_nodes)

        # Let's see if we can use the scheduler to optimize placement
        placements = self._controller._plan_placement(
            num_chunks=num_chunks,
            available_nodes=available,
            strategy=strategy,
        )

        # 4. Assign chunks to nodes
        results = []
        chunk_hosts = []

        for placement in placements:
            chunk_id = placement["chunk_id"]
            node_id = placement["node_id"]
            node = self._controller._registry.get_node(node_id)
            node_host = "localhost"
            if node and node.address and ":" in node.address:
                node_host = node.address.rsplit(":", 1)[0]

            logger.info("Assigning chunk %d to node %s...", chunk_id, node_id)
            result = self._controller._assign_chunk_to_node(
                node_id=node_id,
                chunk_id=chunk_id,
                model_name=model_name,
                num_chunks=num_chunks,
                dtype=dtype,
            )

            success = result.get("success", False)
            placement["success"] = success
            
            # Map chunk endpoint
            endpoint = result.get("chunk_endpoint", "")
            if success and endpoint:
                if ":" in endpoint:
                    port = endpoint.rsplit(":", 1)[1]
                    # Rewrite 0.0.0.0 to node's real IP address
                    resolved_endpoint = f"{node_host}:{port}"
                else:
                    resolved_endpoint = endpoint
                placement["endpoint"] = resolved_endpoint
                chunk_hosts.append(resolved_endpoint)
            else:
                placement["endpoint"] = ""

            results.append(placement)

        success = len(chunk_hosts) == num_chunks and all(p.get("success") for p in results)

        if not success:
            logger.error("Deployment %s failed during chunk assignment", deployment_id)
            return {
                "success": False,
                "message": "One or more nodes failed to load assignments",
                "deployment_id": deployment_id,
                "placements": results,
            }

        # 5. Initialize Inference Gateway for routing
        try:
            logger.info("Connecting InferenceGateway to hosts: %s", chunk_hosts)
            gateway = InferenceGateway(chunk_hosts=chunk_hosts)
            self._gateways[deployment_id] = gateway
        except Exception as exc:
            logger.error("Failed to start InferenceGateway: %s", exc)
            return {
                "success": False,
                "message": f"Failed to start InferenceGateway: {exc}",
                "deployment_id": deployment_id,
                "placements": results,
            }

        gateway_endpoint = f"http://localhost:{self._config.api_port}/api/v1/inference"

        return {
            "success": True,
            "message": f"Successfully deployed model '{model_name}' across {num_chunks} nodes",
            "deployment_id": deployment_id,
            "placements": results,
            "gateway_endpoint": gateway_endpoint,
        }

    def undeploy(self, deployment_id: str) -> bool:
        """Tear down inference gateway for a deployment."""
        if deployment_id in self._gateways:
            del self._gateways[deployment_id]
            logger.info("Shutdown InferenceGateway for deployment %s", deployment_id)
            return True
        return False

    def generate(
        self,
        deployment_id: str,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Run text generation using the deployed chunks and InferenceGateway.

        Parameters
        ----------
        deployment_id : str
            The active deployment ID.
        prompt : str
            The text prompt.
        max_tokens : int
            Maximum tokens to generate.
        temperature : float
            Sampling temperature.

        Returns
        -------
        dict
            Inference result containing generated text, stats, and metadata.
        """
        gateway = self._gateways.get(deployment_id)
        if not gateway:
            return {"success": False, "message": f"No active gateway for deployment {deployment_id}"}

        deployment = self._controller.get_deployment(deployment_id)
        if not deployment:
            return {"success": False, "message": "Deployment not found"}

        model_name = deployment["model_name"]
        logger.info("Starting text generation for model '%s' (deployment %s)", model_name, deployment_id)

        t0 = time.time()
        
        # Tokenize and perform autoregressive generation using the gateway
        try:
            loader = HFModelLoader(model_name, dtype=deployment.get("dtype", "float16"))
            tokenizer = loader.get_tokenizer()
            input_ids = tokenizer.encode(prompt, return_tensors="pt")
            generated_ids = input_ids.clone()
            eos_token_id = tokenizer.eos_token_id

            logger.debug("Prompt tokenized. Input shape: %s", list(input_ids.shape))

            tokens_generated = 0

            for step in range(max_tokens):
                # Pass current token sequence through the whole gateway chain
                res = gateway.run_inference(generated_ids, model_name=model_name)
                logits = res["output_tensor"]  # Should be shape (batch, seq_len, vocab_size)
                
                # Get logits for the last token position
                if logits.dim() == 3:
                    next_logits = logits[:, -1, :]  # (batch=1, vocab_size)
                elif logits.dim() == 2:
                    next_logits = logits  # Fallback
                else:
                    raise ValueError(f"Unexpected logits shape: {logits.shape}")

                # Simple sampling / argmax
                if temperature <= 0.0:
                    next_token_id = torch.argmax(next_logits, dim=-1)
                else:
                    probs = torch.softmax(next_logits / temperature, dim=-1)
                    next_token_id = torch.multinomial(probs, num_samples=1).squeeze(-1)

                if next_token_id.item() == eos_token_id:
                    break

                # Append to sequence
                generated_ids = torch.cat([generated_ids, next_token_id.unsqueeze(0)], dim=1)
                tokens_generated += 1

            total_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
            # Extracted completion (only what was generated)
            completion = tokenizer.decode(generated_ids[0][input_ids.shape[1]:], skip_special_tokens=True)
            
            elapsed = time.time() - t0
            logger.info("Generation complete. Generated %d tokens in %.2fs", tokens_generated, elapsed)

            return {
                "success": True,
                "text": total_text,
                "completion": completion,
                "tokens_generated": tokens_generated,
                "time_taken_s": elapsed,
                "tokens_per_second": tokens_generated / elapsed if elapsed > 0 else 0,
            }

        except Exception as exc:
            logger.exception("Error during distributed text generation: %s", exc)
            return {"success": False, "message": f"Inference execution error: {exc}"}
