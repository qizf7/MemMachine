"""
Qianwen-based language model implementation.
"""

import json
import time
from typing import Any

from openai import AsyncOpenAI

from memmachine.common.metrics_factory.metrics_factory import MetricsFactory

from .language_model import LanguageModel


class QianwenLanguageModel(LanguageModel):
    """
    Language model that uses Qianwen's models
    to generate responses based on prompts and tools.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize a QianwenLanguageModel
        with the provided configuration.

        Args:
            config (dict[str, Any]):
                Configuration dictionary containing:
                - api_key (str):
                  API key for accessing the Qianwen service.
                - model (str, optional):
                  Name of the Qianwen model to use
                  (default: "qwen-turbo").
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

        self._model = config.get("model", "qwen-turbo")
        self._base_url = config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")

        api_key = config.get("api_key")
        if api_key is None:
            raise ValueError("Language API key must be provided")

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

            self._input_tokens_usage_counter = metrics_factory.get_counter(
                "language_model_qianwen_usage_input_tokens",
                "Number of input tokens used for Qianwen language model",
                label_names=label_names,
            )
            self._input_cached_tokens_usage_counter = (
                metrics_factory.get_counter(
                    "language_model_qianwen_usage_input_cached_tokens",
                    (
                        "Number of tokens retrieved from cache "
                        "used for Qianwen language model"
                    ),
                    label_names=label_names,
                )
            )
            self._output_tokens_usage_counter = metrics_factory.get_counter(
                "language_model_qianwen_usage_output_tokens",
                "Number of output tokens used for Qianwen language model",
                label_names=label_names,
            )
            self._output_reasoning_tokens_usage_counter = (
                metrics_factory.get_counter(
                    "language_model_qianwen_usage_output_reasoning_tokens",
                    (
                        "Number of reasoning tokens "
                        "used for Qianwen language model"
                    ),
                    label_names=label_names,
                )
            )
            self._total_tokens_usage_counter = metrics_factory.get_counter(
                "language_model_qianwen_usage_total_tokens",
                "Number of tokens used for Qianwen language model",
                label_names=label_names,
            )
            self._latency_summary = metrics_factory.get_summary(
                "language_model_qianwen_latency_seconds",
                "Latency in seconds for Qianwen language model requests",
                label_names=label_names,
            )

    async def generate_response(
        self,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, str] = "auto",
    ) -> tuple[str, Any]:
        input_prompts = [
            {"role": "system", "content": system_prompt or ""},
            {"role": "user", "content": user_prompt or ""},
        ]

        start_time = time.monotonic()
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=input_prompts,
            tools=tools,
            tool_choice=tool_choice,
        )
        end_time = time.monotonic()

        if self._collect_metrics and response.usage is not None:
            self._input_tokens_usage_counter.increment(
                value=response.usage.prompt_tokens,
                labels=self._user_metrics_labels,
            )
            self._input_cached_tokens_usage_counter.increment(
                value=getattr(response.usage, 'prompt_tokens_details', {}).get('cached_tokens', 0),
                labels=self._user_metrics_labels,
            )
            self._output_tokens_usage_counter.increment(
                value=response.usage.completion_tokens,
                labels=self._user_metrics_labels,
            )
            self._output_reasoning_tokens_usage_counter.increment(
                value=getattr(response.usage, 'completion_tokens_details', {}).get('reasoning_tokens', 0),
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

        function_calls_arguments = []
        if response.choices and response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                if tool_call.type == "function":
                    try:
                        function_calls_arguments.append(
                            json.loads(tool_call.function.arguments)
                        )
                    except json.JSONDecodeError:
                        # Skip invalid JSON arguments
                        continue

        return (
            response.choices[0].message.content or "",
            function_calls_arguments,
        )
