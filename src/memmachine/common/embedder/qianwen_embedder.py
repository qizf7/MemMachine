"""
Qianwen-based embedder implementation.
"""

import time
from typing import Any

from openai import AsyncOpenAI

from memmachine.common.metrics_factory.metrics_factory import MetricsFactory

from .embedder import Embedder


class QianwenEmbedder(Embedder):
    """
    Embedder that uses Qianwen's embedding models
    to generate embeddings for inputs and queries.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize a QianwenEmbedder with the provided configuration.

        Args:
            config (dict[str, Any]):
                Configuration dictionary containing:
                - api_key (str):
                  API key for accessing the Qianwen service.
                - model (str, optional):
                  Name of the Qianwen embedding model to use
                  (default: "text-embedding-v1").
                - base_url (str, optional):
                  Base URL for the Qianwen API
                  (default: "https://dashscope.aliyuncs.com/compatible-mode/v1").
                - metrics_factory (MetricsFactory, optional):
                  An instance of MetricsFactory
                  for collecting usage metrics.
                - user_metrics_labels (dict[str, str], optional):
                  Labels to attach to the collected metrics.

        Raises:
            ValueError:
                If configuration argument values are missing or invalid.
            TypeError:
                If configuration argument values are of incorrect type.
        """
        super().__init__()

        self._model = config.get("model", "text-embedding-v1")
        self._base_url = config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")

        api_key = config.get("api_key")
        if api_key is None:
            raise ValueError("Embedder API key must be provided")

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url
        )

        metrics_factory = config.get("metrics_factory")
        if metrics_factory is not None and not isinstance(
            metrics_factory, MetricsFactory
        ):
            raise TypeError(
                "Metrics factory must be an instance of MetricsFactory"
            )

        self._collect_metrics = False
        if metrics_factory is not None:
            self._collect_metrics = True
            self._user_metrics_labels = config.get("user_metrics_labels", {})
            label_names = self._user_metrics_labels.keys()

            self._prompt_tokens_usage_counter = metrics_factory.get_counter(
                "embedder_qianwen_usage_prompt_tokens",
                "Number of tokens used by prompts to Qianwen embedder",
                label_names=label_names,
            )
            self._total_tokens_usage_counter = metrics_factory.get_counter(
                "embedder_qianwen_usage_total_tokens",
                "Number of tokens used by requests to Qianwen embedder",
                label_names=label_names,
            )
            self._latency_summary = metrics_factory.get_summary(
                "embedder_qianwen_latency_seconds",
                "Latency in seconds for Qianwen embedder requests",
                label_names=label_names,
            )

    async def ingest_embed(self, inputs: list[Any]) -> list[list[float]]:
        return await self._embed(inputs)

    async def search_embed(self, queries: list[Any]) -> list[list[float]]:
        return await self._embed(queries)

    async def _embed(self, inputs: list[Any]) -> list[list[float]]:
        if not inputs:
            return []

        inputs = [
            input.replace("\n", " ") if input else "\n" for input in inputs
        ]

        start_time = time.monotonic()
        response = await self._client.embeddings.create(
            input=inputs, model=self._model
        )
        end_time = time.monotonic()

        if self._collect_metrics:
            self._prompt_tokens_usage_counter.increment(
                value=response.usage.prompt_tokens,
                labels=self._user_metrics_labels,
            )
            self._total_tokens_usage_counter.increment(
                value=response.usage.total_tokens,
                labels=self._user_metrics_labels,
            )
            self._latency_summary.observe(
                value=end_time - start_time,
                labels=self._user_metrics_labels,
            )

        return [datum.embedding for datum in response.data]
