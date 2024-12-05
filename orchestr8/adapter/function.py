from inspect import isfunction
from sys import version_info
from typing import Callable, Generic, TypeVar

if version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec  # type: ignore[assignment]

from .struct import StructAdapter

__all__ = ("FunctionAdapter",)


P_Spec = ParamSpec("P_Spec")
T_Retval = TypeVar("T_Retval")


class FunctionAdapter(StructAdapter[T_Retval], Generic[P_Spec, T_Retval]):
    """
    A specialized adapter for Python functions, extending StructAdapter to handle function-specific type hints.

    Provides:
    - Function code definition extraction
    - Dynamic schema generation for function signatures.
    - Extraction of docstring metadata for populating schema.
    - Automatic validation of python or JsON input against the schema.

    Enables schema-driven representations of functions for function calling, serialization, and documentation purposes.

    ```python
    from orchestr8.adapter.function import FunctionAdapter

    def create_user(id: str, role: Literal["admin", "user"]) -> bool:
        \"""
        Creates a new user with the given ID and role.

        :param id: The ID of the user to create.
        :param role: The role of the user to create.
        \"""

    # Create adapter
    fn = FunctionAdapter(create_user)

    # Normal invocation
    fn(id="user123", role="user")

    # Access function properties
    print(f"Function name: {fn.name}")
    print(f"Function description: {fn.description}")
    print(f"Function docstring: {fn.docstring}")
    print(f"Function definition: {fn.definition}")
    print(f"Function schema: {fn.schema}")
    print(f"Function OpenAI schema: {fn.openai_schema}")
    print(f"Function Anthropic schema: {fn.anthropic_schema}")
    print(f"Function Gemini schema: {fn.gemini_schema}")

    # Validate python input
    fn.validate_input({"id": "user123", "role": "user"})

    # Validate JSON input
    fn.validate_input('{"id": "user123", "role": "user"}')
    ```
    """

    ref_type = "function"
    validate_ref = lambda c, r: isfunction(r)

    def __init__(self, __fn: Callable[P_Spec, T_Retval]) -> None:
        """
        Args:
            __fn: The function to create adapter from

        Raises:
            ValueError: If __fn is not a valid function
        """
        super().__init__(__fn)  # type: ignore[arg-type]

    def __call__(self, *args: P_Spec.args, **kwargs: P_Spec.kwargs) -> T_Retval:
        return super().__call__(*args, **kwargs)
