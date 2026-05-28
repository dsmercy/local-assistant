class OllamaError(Exception):
    """Base class for Ollama client errors."""


class OllamaUnavailableError(OllamaError):
    """Raised when Ollama server is unreachable or returns a non-2xx status."""


class OllamaModelNotFoundError(OllamaError):
    """Raised when the requested model is not available."""
