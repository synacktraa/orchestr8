from __future__ import annotations

from inspect import isclass
from typing import TYPE_CHECKING, Any, Dict, Generic, Literal, Type, TypeVar

if TYPE_CHECKING:
    from docstring_parser import Docstring

from .base import BaseAdapter
from .utils import build_description, get_code_definition, update_object_schema

__all__ = ("StructAdapter",)


T = TypeVar("T")


class StructAdapter(Generic[T], BaseAdapter):
    """
    A wrapper around pydantic's `TypeAdapter` for schema and definition generation with capability to
    validate input from python or JsON object.

    Structured types such as Pydantic Models, TypedDict, dataclasses, etc. are supported.

    Provides:
    - Code definition extraction.
    - Dynamic schema generation in standard and function-calling formats such as OpenAI, Anthropic, and Gemini.
    - Extraction of docstring metadata for populating schema.
    - Automatic validation of python or JsON input against the schema.

    Useful for schema-driven representations of complex types for use in function calling,
    serialization, and documentation contexts.

    ```python
    from typing_extensions import TypedDict
    from orchestract.adapter.struct import StructAdapter

    class User(TypedDict): # Can be pydantic model or dataclass
        id: str
        role: Literal["admin", "user"]

    # Create adapter
    struct = StructAdapter(User)

    # Normal invocation
    struct(id="user123", role="user") # returns: {"id": "user123", "role": "user"}

    # Access adapter properties
    print(f"Struct name: {struct.name}")
    print(f"Struct description: {struct.description}")
    print(f"Struct docstring: {struct.docstring}")
    print(f"Struct definition: {struct.definition}")
    print(f"Struct schema: {struct.schema}")
    print(f"Struct OpenAI schema: {struct.openai_schema}")
    print(f"Struct Anthropic schema: {struct.anthropic_schema}")
    print(f"Struct Gemini schema: {struct.gemini_schema}")

    # Validate python input
    struct.validate_input({"id": "user123", "role": "user"})

    # Validate JSON input
    struct.validate_input('{"id": "user123", "role": "user"}')
    ```
    """

    ref_type: Literal["function", "class"] | None = "class"
    validate_ref = lambda c, r: isclass(r)

    def __init__(self, __obj: Type[T]) -> None:
        """
        Args:
            __obj: The structured type to create adapter from

        Raises:
            ValueError: If object is of not class type
        """
        if not self.validate_ref(__obj):
            raise ValueError(f"Expected a {self.ref_type!r}")
        self.__ref = __obj
        self.__name = self.__ref.__name__

        from docstring_parser import parse
        from pydantic.type_adapter import TypeAdapter

        self.__docstring = parse(self.__ref.__doc__ or "")
        self.__adapter = TypeAdapter(self.__ref)
        self.__description = build_description(self.__docstring)
        self.__definition: str | None = None
        self.__schema: Dict[str, Any] | None = None

    def __call__(self, *args: Any, **kwargs: Any) -> T:
        return self.__ref(*args, **kwargs)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def description(self) -> str | None:
        return self.__description or None

    @property
    def docstring(self) -> Docstring:
        return self.__docstring

    @property
    def definition(self) -> str:
        """Code definition"""
        if self.__definition is None:
            self.__definition = get_code_definition(self.__ref, type=self.ref_type)
        return self.__definition

    @property
    def schema(self) -> Dict[str, Any]:
        """Schema in standard format."""
        if self.__schema is None:
            base_schema = self.__adapter.json_schema()
            if "$defs" in base_schema:
                from jsonref import replace_refs  # type: ignore[import-untyped]

                base_schema = replace_refs(base_schema, lazy_load=False)
                _ = base_schema.pop("$defs", None)
            self.__schema = update_object_schema(self.__ref, base_schema, self.__docstring)
        return self.__schema

    def validate_input(self, input: Dict[str, Any] | str, *, strict: bool | None = None, **kwargs: Any) -> T:  # noqa: A002
        """
        Validate the input against the schema.

        Args:
            input: The dictionary object or JSON string to validate.
            strict: Whether to perform strict validation.
            kwargs: Additional keyword arguments to pass to the TypeAdapter's validate method.

        Returns:
            The validated input.
        """
        if isinstance(input, str):
            return self.__adapter.validate_json(input, strict=strict, **kwargs)
        return self.__adapter.validate_python(input, strict=strict, **kwargs)
