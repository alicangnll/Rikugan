"""Core error classes for Rikugan."""


class RikuganError(Exception):
    """Base exception for all Rikugan errors."""

    pass


class ProviderError(RikuganError):
    """Exception raised for LLM provider errors."""

    def __init__(self, message: str, provider: str = "unknown"):
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")


class AuthenticationError(ProviderError):
    """Exception raised for authentication failures."""

    pass


class RateLimitError(ProviderError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, provider: str = "unknown", retry_after: float = 5.0):
        self.retry_after = retry_after
        super().__init__(message, provider)


class ContextLengthError(ProviderError):
    """Exception raised when context length is exceeded."""

    pass


class ConfigurationError(RikuganError):
    """Exception raised for configuration errors."""

    pass


class ToolExecutionError(RikuganError):
    """Exception raised when tool execution fails."""

    pass
