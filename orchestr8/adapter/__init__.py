from inspect import isclass, isfunction
from typing import Any, Callable, Type, overload

from .function import FunctionAdapter, P_Spec, T_Retval
from .struct import StructAdapter

__all__ = ("adapt",)


@overload
def adapt(__obj: Callable[P_Spec, T_Retval]) -> FunctionAdapter[P_Spec, T_Retval]:  # type: ignore[type-arg,valid-type]
    """
    Create an adapter from a function.

    Refer`orchestr8.adapter.function.FunctionAdapter` for more details.

    Args:
        __obj: The function to adapt.

    Returns:
        The adapter.
    """


@overload
def adapt(__obj: Type[T_Retval]) -> StructAdapter[T_Retval]:  # type: ignore[overload-cannot-match]
    """
    Create an adapter from a structured type such as Pydantic Model, TypedDict, dataclass, etc.

    Refer`orchestr8.adapter.struct.StructAdapter` for more details.

    Args:
        __obj: The complex class type to adapt.

    Returns:
        The adapter.
    """


def adapt(__obj: Any) -> Any:
    """
    Create an adapter from a function or structured type such as
    Pydantic Model, TypedDict, dataclass, etc.

    ```python
    from orchestr8.adapter import adapt
    from typing_extensions import TypedDict
    from pydantic import BaseModel

    @adapt
    def add(a: int, b: int) -> int:
        \"""
        Add two numbers together.

        :param a: The first number to add.
        :param b: The second number to add.
        \"""
        return a + b

    @adapt
    class User(TypedDict):
        id: str
        role: Literal["admin", "user"]
    ```
    """
    if isfunction(__obj):
        return FunctionAdapter(__obj)
    elif isclass(__obj):
        return StructAdapter(__obj)
    raise ValueError(f"Expected a function or class, got {type(__obj)} type")
