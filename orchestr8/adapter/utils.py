from __future__ import annotations

import ast
from inspect import getsource
from textwrap import dedent
from types import FunctionType
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from docstring_parser import Docstring


def extract_wrapped_function(__fn: FunctionType) -> FunctionType:
    """
    Extract the wrapped function.

    Args:
        __fn:  The function to extract the wrapped function from.

    Returns:
        The wrapped function.
    """
    if closure := __fn.__closure__:
        for cell in closure:
            if not isinstance(contents := cell.cell_contents, FunctionType):
                continue
            if contents.__closure__ is None:
                return contents
            else:
                return extract_wrapped_function(contents)
    return __fn


def get_code_definition(obj: Any, type: Literal["function", "class"] | None = None) -> str:  # noqa: A002
    """
    Get code definition of the object.

    Args:
        obj:  The object to get the code definition of.
        type:  The type of object to get the code definition of.

    Returns:
        The code definition of the object.
    """
    if type == "function":
        obj = extract_wrapped_function(obj)
    source = dedent(getsource(obj))
    if type is None:
        return source
    fn_ast = ast.parse(source).body[0]
    fn_ast.decorator_list = []  # type: ignore[attr-defined]
    return ast.unparse(fn_ast)


def build_description(docstring: Docstring) -> str | None:
    """
    Build description from docstring.

    Args:
        docstring:  A Docstring object.

    Returns:
        The description if found, else None
    """

    result = []
    if docstring.short_description:
        result.append(docstring.short_description)
        if docstring.blank_after_short_description:
            result.append("")
    if docstring.long_description:
        result.append(docstring.long_description)

    return "\n".join(result).strip("\n") if result else None


def update_object_schema(__type: type, schema: Dict[str, Any], docstring: Docstring) -> Dict[str, Any]:
    """
    Update object type schema with its type's docstring

    Args:
        __type:  The type to update schema for
        schema:  The schema to update
        docstring:  The docstring to use for updating

    Returns:
        The updated schema
    """
    typehints = get_type_hints(__type)
    if desc := build_description(docstring) or schema.get("description"):
        schema["description"] = desc
    for p_name, p_schema in schema["properties"].items():
        if p_name in typehints:
            schema["properties"][p_name] = update_schema(typehints[p_name], p_schema, docstring)
        param = next((p for p in docstring.params if p.arg_name == p_name), None)
        if param and (p_desc := param.description or p_schema.get("description")):
            schema["properties"][p_name]["description"] = p_desc
    return schema


def update_array_schema(__type: type, schema: Dict[str, Any], docstring: Docstring) -> Dict[str, Any]:
    """
    Update array type schema items/prefixItems with its type's docstring

    Args:
        __type:  The type to update schema for
        schema:  The schema to update
        docstring:  The docstring to use for updating

    Returns:
        The updated schema
    """
    if "items" in schema:
        schema["items"] = update_schema(__type, schema["items"], docstring)
    elif "prefixItems" in schema and all("title" in item for item in schema["prefixItems"]):
        # we assume it's named tuple
        prefix_items = []
        p_name_to_desc = {p.arg_name: p.description for p in docstring.params}
        for p_schema in schema["prefixItems"]:
            if (p_name := p_schema["title"].lower()) in p_name_to_desc:
                p_schema["description"] = p_name_to_desc[p_name]
            prefix_items.append(p_schema)
        schema["prefixItems"] = prefix_items
    return schema


def update_schema(__type: type, schema: Dict[str, Any], docstring: Docstring) -> Dict[str, Any]:
    """
    Update type schema

    Args:
        __type:  The type to update schema for
        schema:  The schema to update
        docstring:  The docstring to use for updating

    Returns:
        The updated schema
    """
    if "anyOf" in schema:
        of_key = "anyOf"
    elif "oneOf" in schema:
        of_key = "oneOf"
    else:
        of_key = None

    origin, arg_types = get_origin(__type) or __type, get_args(__type)
    if of_key is not None:
        schema[of_key] = [update_schema(tp, sc, docstring) for tp, sc in zip(arg_types, schema[of_key])]
    elif schema.get("type") == "object" and "properties" in schema:
        if not schema.get("additionalProperties", True):
            _ = schema.pop("additionalProperties")
        schema = update_object_schema(origin, schema, docstring)
    elif schema.get("type") == "array":
        schema = update_array_schema(arg_types[0] if arg_types else origin, schema, docstring)

    return schema


def drop_titles(__schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove title key-value pair from the entire schema

    Args:
        __schema:  The schema to drop titles from

    Returns:
        The schema with titles dropped
    """
    __schema.pop("title", None)

    if "anyOf" in __schema:
        for sub_schema in __schema["anyOf"]:
            drop_titles(sub_schema)
    elif "oneOf" in __schema:
        for sub_schema in __schema["oneOf"]:
            drop_titles(sub_schema)
    elif __schema.get("type") == "object" and "properties" in __schema:
        for prop in __schema["properties"].values():
            drop_titles(prop)
    elif __schema.get("type") == "array" and "items" in __schema:
        drop_titles(__schema["items"])

    return __schema


def to_function_calling_format(name: str, schema: Dict[str, Any], params_key: str) -> Dict[str, Any]:
    """
    Transform to LLM function calling format

    Args:
        name:  The function name
        schema:  The function schema
        params_key:  The key to use for parameters

    Returns:
        The function calling formatted schema.
    """
    if schema.get("type") != "object":
        raise ValueError("Schema must be of object type.")

    description_dict: Dict[str, str] = {}
    if desc := schema.pop("description", None):
        description_dict["description"] = desc

    return {"type": "function", "function": {"name": name, **description_dict, params_key: drop_titles(schema)}}


def to_openai_function_calling_format(name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a function schema to the OpenAI function calling format.

    Args:
        name:  The name of the function.
        schema:  The function schema.

    Returns:
        Schema in OpenAI function calling format.
    """
    return to_function_calling_format(name, schema, "parameters")


def to_anthropic_function_calling_format(name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a function schema to the Anthropic function calling format.

    Args:
        name:  The name of the function.
        schema:  The function schema.

    Returns:
        Schema in Anthropic function calling format.
    """
    return to_function_calling_format(name, schema, "input_schema")


def to_gemini_function_calling_format(name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a function schema to the Gemini function calling format.

    Args:
        name:  The name of the function.
        schema:  The function schema.

    Returns:
        Schema in Gemini function calling format.
    """
    from pydantic import BaseModel

    class SchemaModel(BaseModel):
        description: Optional[str] = None
        enum: Optional[List[str]] = None
        example: Optional[Any] = None
        format: Optional[str] = None
        nullable: Optional[bool] = None
        items: Optional[SchemaModel] = None
        required: Optional[List[str]] = None
        type: str
        properties: Optional[Dict[str, SchemaModel]] = None

    def add_enum_format(obj: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(obj, dict):
            new_dict: dict[str, Any] = {}
            for key, value in obj.items():
                new_dict[key] = add_enum_format(value)
                if key == "enum":
                    new_dict["format"] = "enum"
            return new_dict
        return obj

    schema_model = SchemaModel(**add_enum_format(schema))
    return to_function_calling_format(
        name=name,
        schema=schema_model.model_dump(exclude_none=True, exclude_unset=True),
        params_key="parameters",
    )
