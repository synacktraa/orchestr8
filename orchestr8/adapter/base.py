from __future__ import annotations

from typing import Any, Dict

from .utils import (
    to_anthropic_function_calling_format,
    to_gemini_function_calling_format,
    to_openai_function_calling_format,
)

__all__ = ("BaseAdapter",)


class BaseAdapter:
    """Base class to be inherited by all adapters."""

    def __new__(cls, *args: Any, **kwargs: Any) -> BaseAdapter:
        if cls is BaseAdapter:
            raise TypeError("BaseAdapter cannot be instantiated directly")
        return super().__new__(cls)

    @property
    def name(self) -> str:
        """Name of the adapted object."""
        raise NotImplementedError("Parent class must implemented this property")

    @property
    def description(self) -> str | None:
        """Description of the adapted object."""
        raise NotImplementedError("Parent class must implemented this property")

    @property
    def schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the adapted object."""
        raise NotImplementedError("Parent class must implemented this property")

    @property
    def openai_schema(self) -> Dict[str, Any]:
        """Schema of the function in OpenAI function calling format."""
        return to_openai_function_calling_format(self.name, self.schema)

    @property
    def anthropic_schema(self) -> Dict[str, Any]:
        """Schema of the function in Anthropic function calling format."""
        return to_anthropic_function_calling_format(self.name, self.schema)

    @property
    def gemini_schema(self) -> Dict[str, Any]:
        """Schema of the function in Gemini function calling format."""
        return to_gemini_function_calling_format(self.name, self.schema)

    def validate_input(self, input: str | Dict[str, Any], **kwargs: Any) -> Any:  # noqa: A002
        """
        Validate the input against the schema of the function.

        Args:
            input: The JSON value or dictionary object to validate.
            kwargs: Additional keyword arguments.

        Returns:
            The validated input.
        """
        raise NotImplementedError("Parent class must implemented this method")
