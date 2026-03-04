"""MiniMax provider implementation."""

from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional

import importlib

from ..core.logging import log_debug, log_error
from ..core.types import Message, ModelInfo, ProviderCapabilities, Role, StreamChunk, TokenUsage
from .base import LLMProvider


class MiniMaxProvider(LLMProvider):
    """MiniMax LLM provider."""

    DEFAULT_API_BASE = "https://api.minimax.chat/v1"

    def __init__(self, api_key: str = "", api_base: str = "", model: str = ""):
        super().__init__(api_key, api_base or self.DEFAULT_API_BASE, model)

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            tools=True,
            vision=False,
            max_tokens=8192,
        )

    def _get_client(self):
        if self._client is None:
            openai = importlib.import_module("openai")
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
            )
        return self._client

    @staticmethod
    def _builtin_models() -> List[ModelInfo]:
        return [
            ModelInfo(id="MiniMax-M2.5", name="MiniMax M2.5", context_length=245760),
            ModelInfo(id="MiniMax-M2.5-Light", name="MiniMax M2.5 Lightning", context_length=245760),
            ModelInfo(id="MiniMax-Text-01", name="MiniMax Text 01", context_length=245760),
        ]

    def _fetch_models_live(self) -> List[ModelInfo]:
        client = self._get_client()
        response = client.models.list()
        models = []
        for m in response.data:
            if m.id.startswith("MiniMax"):
                models.append(ModelInfo(
                    id=m.id,
                    name=m.id,
                    context_length=getattr(m, "context_window", 245760),
                ))
        return models or self._builtin_models()

    def _format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert internal messages to MiniMax format."""
        formatted = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                formatted.append({"role": "system", "content": msg.content})
            elif msg.role == Role.USER:
                formatted.append({"role": "user", "content": msg.content})
            elif msg.role == Role.ASSISTANT:
                content = msg.content or ""
                if msg.tool_calls:
                    tool_calls = []
                    for tc in msg.tool_calls:
                        tool_calls.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        })
                    formatted.append({
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls,
                    })
                else:
                    formatted.append({"role": "assistant", "content": content})
            elif msg.role == Role.TOOL:
                formatted.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content,
                })
        return formatted

    def _normalize_response(self, response) -> Message:
        """Convert MiniMax response to internal Message."""
        choice = response.choices[0]
        text = choice.message.content or ""
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                ))

        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            total_tokens=response.usage.total_tokens if response.usage else 0,
        )

        return Message(
            role=Role.ASSISTANT,
            content=text,
            tool_calls=tool_calls,
            token_usage=usage,
        )

    def _handle_api_error(self, e: Exception) -> None:
        """Raise the appropriate Rikugan error from a MiniMax API error."""
        openai = importlib.import_module("openai")

        if isinstance(e, openai.AuthenticationError):
            from ..core.errors import AuthenticationError
            raise AuthenticationError(provider="minimax") from e
        if isinstance(e, openai.RateLimitError):
            from ..core.errors import RateLimitError
            raise RateLimitError(provider="minimax", retry_after=5.0) from e
        if isinstance(e, openai.BadRequestError):
            msg = str(e)
            from ..core.errors import ContextLengthError, ProviderError
            if "context" in msg.lower() or "token" in msg.lower():
                raise ContextLengthError(msg, provider="minimax") from e
            raise ProviderError(msg, provider="minimax") from e
        from ..core.errors import ProviderError
        raise ProviderError(str(e), provider="minimax") from e

    def _build_request_kwargs(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int,
        system: str,
    ) -> Dict[str, Any]:
        """Build kwargs dict for chat.completions.create."""
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(self._format_messages(messages))

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
        return kwargs

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        system: str = "",
    ) -> Message:
        client = self._get_client()
        kwargs = self._build_request_kwargs(messages, tools, temperature, max_tokens, system)

        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as e:
            self._handle_api_error(e)

        return self._normalize_response(response)

    def chat_stream(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        system: str = "",
    ) -> Generator[StreamChunk, None, None]:
        client = self._get_client()
        kwargs = self._build_request_kwargs(messages, tools, temperature, max_tokens, system)
        kwargs["stream"] = True

        try:
            stream = client.chat.completions.create(**kwargs)
            current_tool_calls: Dict[int, dict] = {}

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if delta.content:
                    yield StreamChunk(text=delta.content)

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tc_delta.id or "",
                                "name": tc_delta.function.name if tc_delta.function and tc_delta.function.name else "",
                                "args": "",
                            }
                            if tc_delta.id:
                                yield StreamChunk(
                                    tool_call_id=tc_delta.id,
                                    tool_name=tc_delta.function.name if tc_delta.function else "",
                                    is_tool_call_start=True,
                                )

                        if tc_delta.function and tc_delta.function.arguments:
                            current_tool_calls[idx]["args"] += tc_delta.function.arguments
                            yield StreamChunk(
                                tool_call_id=current_tool_calls[idx]["id"],
                                tool_name=current_tool_calls[idx]["name"],
                                tool_args_delta=tc_delta.function.arguments,
                            )

                if chunk.choices[0].finish_reason:
                    for tc_info in current_tool_calls.values():
                        yield StreamChunk(
                            tool_call_id=tc_info["id"],
                            tool_name=tc_info["name"],
                            is_tool_call_end=True,
                        )
                    yield StreamChunk(finish_reason=chunk.choices[0].finish_reason)

                if chunk.usage:
                    yield StreamChunk(usage=TokenUsage(
                        prompt_tokens=chunk.usage.prompt_tokens,
                        completion_tokens=chunk.usage.completion_tokens,
                        total_tokens=chunk.usage.total_tokens,
                    ))

        except Exception as e:
            log_error(f"MiniMaxProvider.chat_stream error: {e}")
            self._handle_api_error(e)

    def auth_status(self) -> tuple:
        """Return authentication status."""
        if self.api_key:
            return "API Key", "ok"
        return "", "none"


class ToolCall:
    """Minimal ToolCall replacement for this module."""
    def __init__(self, id: str, name: str, arguments: dict):
        self.id = id
        self.name = name
        self.arguments = arguments
