from __future__ import annotations

from typing import List, Literal, NamedTuple, Union

import pytest
from docstring_parser import Docstring
from typing_extensions import TypedDict

from orchestr8.adapter import adapt
from orchestr8.adapter.utils import (
    to_anthropic_function_calling_format,
    to_gemini_function_calling_format,
    to_openai_function_calling_format,
)


def test_struct_adapter_with_typeddict():
    @adapt
    class User(TypedDict):
        """
        User data

        :param id: The ID of the user
        :param role: The role of the user
        """

        id: str
        role: Literal["admin", "user"]

    output = User(id="user123", role="user")
    assert output["id"] == "user123"
    assert output["role"] == "user"
    assert User.name == "User"
    assert User.description == "User data"
    assert isinstance(User.docstring, Docstring)
    assert User.definition.startswith("class User(TypedDict):")
    standard_schema = {
        "type": "object",
        "title": "User",
        "description": "User data",
        "properties": {
            "id": {"title": "Id", "type": "string", "description": "The ID of the user"},
            "role": {
                "title": "Role",
                "type": "string",
                "enum": ["admin", "user"],
                "description": "The role of the user",
            },
        },
        "required": ["id", "role"],
    }
    assert User.schema == standard_schema
    assert User.openai_schema == to_openai_function_calling_format(User.name, standard_schema)
    assert User.anthropic_schema == to_anthropic_function_calling_format(User.name, standard_schema)
    assert User.gemini_schema == to_gemini_function_calling_format(User.name, standard_schema)


class User(NamedTuple):
    name: str
    age: int


def test_function_adapter_with_nested_types():
    @adapt
    def create_users(users: List[User]) -> bool:
        """
        Create a list of users.

        :param users: The list of users to create.
        """
        return True

    assert create_users.schema["properties"]["users"] == {
        "items": {
            "maxItems": 2,
            "minItems": 2,
            "prefixItems": [{"title": "Name", "type": "string"}, {"title": "Age", "type": "integer"}],
            "type": "array",
        },
        "title": "Users",
        "type": "array",
        "description": "The list of users to create.",
    }


def test_function_adapter_with_optional_parameters():
    @adapt
    def update_user(
        id: str,  # noqa: A002
        name: Union[str, None] = None,
        age: Union[int, None] = None,
    ) -> User:
        """
        Update a user with the given ID.

        :param id: The ID of the user to update.
        :param name: The new name of the user (optional).
        :param age: The new age of the user (optional).
        """
        # Implementation omitted
        return User(name or "John Doe", age or 30)

    assert update_user.schema["properties"] == {
        "id": {"type": "string", "title": "Id", "description": "The ID of the user to update."},
        "name": {
            "title": "Name",
            "description": "The new name of the user (optional).",
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "default": None,
        },
        "age": {
            "title": "Age",
            "description": "The new age of the user (optional).",
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "default": None,
        },
    }
    assert update_user.schema["required"] == ["id"]


def test_adapt_decorator_with_invalid_input():
    with pytest.raises(ValueError):
        adapt(42)  # Non-function/struct input


def test_adapter_validate_input():
    def add(a: int, b: int) -> int:
        """
        Add two numbers together.

        :param a: The first number to add.
        :param b: The second number to add.
        """
        return a + b

    add_adapter = adapt(add)
    assert add_adapter.validate_input({"a": 1, "b": 2}) == 3
    assert add_adapter.validate_input('{"a": 1, "b": 2}') == 3

    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        add_adapter.validate_input({"a": 1, "b": "2"}, strict=True)

    with pytest.raises(ValidationError):
        add_adapter.validate_input('{"a": 1, "b": "2"}', strict=True)
