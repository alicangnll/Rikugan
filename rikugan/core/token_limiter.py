"""Token usage limiter for Rikugan.

Prevents excessive token usage by enforcing configurable limits.
Raises an error when limits are exceeded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.errors import ProviderError
from ..core.logging import log_debug, log_error, log_warn


class TokenType(str, Enum):
    """Token usage types."""

    INPUT = "input"
    OUTPUT = "output"
    CACHE_READ = "cache_read"
    CACHE_CREATION = "cache_creation"
    TOTAL = "total"


@dataclass
class TokenLimit:
    """Token limit configuration."""

    max_input_tokens: int = 100000
    max_output_tokens: int = 50000
    max_cache_read_tokens: int = 100000
    max_cache_creation_tokens: int = 50000
    max_total_tokens: int = 200000
    enabled: bool = True
    action: str = "error"  # "error", "warn", "none"


class TokenLimiter:
    """Token usage limiter.

    Enforces token limits to prevent excessive usage.
    Can be configured via settings or environment variables.
    """

    def __init__(self, config: Optional[TokenLimit] = None):
        """Initialize token limiter.

        Args:
            config: Token limit configuration. If None, loads from settings.
        """
        if config is None:
            config = self._load_config()
        self.config = config
        self._session_tokens = {TokenType.INPUT: 0, TokenType.OUTPUT: 0,
                             TokenType.CACHE_READ: 0, TokenType.CACHE_CREATION: 0}

    def _load_config(self) -> TokenLimit:
        """Load token limit configuration from settings or environment."""
        from ..core.config import RikuganConfig

        cfg = RikuganConfig()

        # Check environment variables first
        max_input = int(os.environ.get("RIKUGAN_MAX_INPUT_TOKENS", "100000"))
        max_output = int(os.environ.get("RIKUGAN_MAX_OUTPUT_TOKENS", "50000"))
        max_total = int(os.environ.get("RIKUGAN_MAX_TOTAL_TOKENS", "200000"))
        enabled = os.environ.get("RIKUGAN_TOKEN_LIMITER_ENABLED", "true").lower() == "true"
        action = os.environ.get("RIKUGAN_TOKEN_LIMITER_ACTION", "error")

        # Check settings file
        if hasattr(cfg, "token_limiter"):
            limiter_cfg = cfg.token_limiter
            return TokenLimit(
                max_input_tokens=limiter_cfg.get("max_input_tokens", max_input),
                max_output_tokens=limiter_cfg.get("max_output_tokens", max_output),
                max_cache_read_tokens=limiter_cfg.get("max_cache_read_tokens", 100000),
                max_cache_creation_tokens=limiter_cfg.get("max_cache_creation_tokens", 50000),
                max_total_tokens=limiter_cfg.get("max_total_tokens", max_total),
                enabled=limiter_cfg.get("enabled", enabled),
                action=limiter_cfg.get("action", action),
            )

        return TokenLimit(
            max_input_tokens=max_input,
            max_output_tokens=max_output,
            max_cache_read_tokens=100000,
            max_cache_creation_tokens=50000,
            max_total_tokens=max_total,
            enabled=enabled,
            action=action,
        )

    def check_tokens(self, input_tokens: int = 0, output_tokens: int = 0,
                    cache_read_tokens: int = 0, cache_creation_tokens: int = 0) -> None:
        """Check if token usage is within limits.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            cache_read_tokens: Number of cache read tokens.
            cache_creation_tokens: Number of cache creation tokens.

        Raises:
            ProviderError: If token limits are exceeded and action is "error".
        """
        if not self.config.enabled:
            return

        total_tokens = input_tokens + output_tokens + cache_read_tokens + cache_creation_tokens

        # Check each limit
        limits = [
            (TokenType.INPUT, input_tokens, self.config.max_input_tokens),
            (TokenType.OUTPUT, output_tokens, self.config.max_output_tokens),
            (TokenType.CACHE_READ, cache_read_tokens, self.config.max_cache_read_tokens),
            (TokenType.CACHE_CREATION, cache_creation_tokens, self.config.max_cache_creation_tokens),
            (TokenType.TOTAL, total_tokens, self.config.max_total_tokens),
        ]

        for token_type, used, limit in limits:
            if used > limit:
                self._handle_limit_exceeded(token_type, used, limit)

        # Update session tokens
        self._session_tokens[TokenType.INPUT] += input_tokens
        self._session_tokens[TokenType.OUTPUT] += output_tokens
        self._session_tokens[TokenType.CACHE_READ] += cache_read_tokens
        self._session_tokens[TokenType.CACHE_CREATION] += cache_creation_tokens

    def _handle_limit_exceeded(self, token_type: TokenType, used: int, limit: int) -> None:
        """Handle token limit exceeded.

        Args:
            token_type: Type of token that exceeded limit.
            used: Number of tokens used.
            limit: Token limit.

        Raises:
            ProviderError: If action is "error".
        """
        msg = (
            f"Token limit exceeded: {token_type.value} tokens "
            f"({used:,} > {limit:,})"
        )

        if self.config.action == "error":
            log_error(msg)
            raise ProviderError(
                f"Token usage exceeded limit: {used:,} {token_type.value} tokens "
                f"(limit: {limit:,}). Please reduce input length or adjust "
                "RIKUGAN_MAX_*_TOKENS environment variables.",
                provider="token_limiter",
            )
        elif self.config.action == "warn":
            log_warn(msg)
        else:
            log_debug(msg)

    def get_session_tokens(self) -> dict[TokenType, int]:
        """Get current session token usage.

        Returns:
            Dictionary mapping token types to usage counts.
        """
        return self._session_tokens.copy()

    def reset_session_tokens(self) -> None:
        """Reset session token usage."""
        self._session_tokens = {token_type: 0 for token_type in TokenType}
        log_debug("Session token usage reset")

    def get_remaining_tokens(self) -> dict[TokenType, int]:
        """Get remaining tokens for each type.

        Returns:
            Dictionary mapping token types to remaining tokens.
        """
        return {
            TokenType.INPUT: self.config.max_input_tokens - self._session_tokens[TokenType.INPUT],
            TokenType.OUTPUT: self.config.max_output_tokens - self._session_tokens[TokenType.OUTPUT],
            TokenType.CACHE_READ: self.config.max_cache_read_tokens - self._session_tokens[TokenType.CACHE_READ],
            TokenType.CACHE_CREATION: self.config.max_cache_creation_tokens - self._session_tokens[TokenType.CACHE_CREATION],
            TokenType.TOTAL: self.config.max_total_tokens - sum(self._session_tokens.values()),
        }


# Global token limiter instance
_token_limiter: Optional[TokenLimiter] = None


def get_token_limiter() -> TokenLimiter:
    """Get the global token limiter instance.

    Returns:
        Token limiter instance.
    """
    global _token_limiter
    if _token_limiter is None:
        _token_limiter = TokenLimiter()
    return _token_limiter


def reset_token_limiter() -> None:
    """Reset the global token limiter."""
    global _token_limiter
    _token_limiter = None
