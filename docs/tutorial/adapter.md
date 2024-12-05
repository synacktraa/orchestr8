Orchestr8 comes with two types of adapters: `StructAdapter` and `FunctionAdapter`. These adapters allow you to generate schema in standard & function-calling formats, extract code definition and validate input from Python or JsON object.

## `@adapt` decorator

The `@adapt` decorator wraps both `StructAdapter` and `FunctionAdapter` and allows you to easily create adapters from functions or structured types such as Pydantic Model, TypedDict, dataclass, etc.

```python
import orchestr8 as o8
from typing import Literal
from typing_extensions import TypedDict

@o8.adapt
def search_web(
    text: str,
    backend: Literal['api', 'html', 'lite'] = 'api',
):
    """
    Search the web.

    :param text: Text to search for
    :param backend: Backend to use for retrieving results
    """
    return f"No results found for {text!r} in {backend!r} backend."

@o8.adapt
class ProductInfo(BaseModel):
    """
    Information about the product.

    :param name: Name of the product
    :param price: Price of the product
    :param in_stock: If the product is in stock
    """
    name: str
    price: float
    in_stock: bool
```

!!! Example "Working with adapter instance"

    ```python
    print(search_web.name) # search_web
    print(search_web.description) # Search the web.
    ```

    `search_web.definition`

    !!! success "Code definition"

        ```python
        def search_web(
            text: str,
            backend: Literal['api', 'html', 'lite'] = 'api',
        ):
            """
            Search the web.

            :param text: Text to search for
            :param backend: Backend to use for retrieving results
            """
            return f"No results found for {text!r} in {backend!r} backend."
        ```

    `search_web.schema`

    !!! success "Standard Schema"

        ```python
        {
            'additionalProperties': False,
            'properties': {
                'text': {
                    'title': 'Text',
                    'type': 'string',
                    'description': 'Text to search for'
                },
                'backend': {
                    'default': 'api',
                    'enum': ['api', 'html', 'lite'],
                    'title': 'Backend',
                    'type': 'string',
                    'description': 'Backend to use for retrieving results'
                }
            },
            'required': ['text'],
            'type': 'object',
            'description': 'Search the web.'
        }
        ```

    `search_web.openai_schema`

    !!! success "OpenAI Schema"

        ```python
        {
            "type": "function",
            "function": {
                'name': 'search_web',
                'description': 'Search the web.',
                'parameters': {
                    'additionalProperties': False,
                    'properties': {
                        'text': {
                            'type': 'string',
                            'description': 'Text to search for'
                        },
                        'backend': {
                            'default': 'api',
                            'enum': ['api', 'html', 'lite'],
                            'type': 'string',
                            'description': 'Backend to use for retrieving results'
                        }
                    },
                    'required': ['text'],
                    'type': 'object'
                }
            }
        }
        ```

    `search_web.anthropic_schema`

    !!! success "Anthropic Schema"

        ```python
        {
            "type": "function",
            "function": {
                'name': 'search_web',
                'input_schema': {
                    'additionalProperties': False,
                    'properties': {
                        'text': {
                            'type': 'string',
                            'description': 'Text to search for'
                        },
                        'backend': {
                            'default': 'api',
                            'enum': ['api', 'html', 'lite'],
                            'type': 'string',
                            'description': 'Backend to use for retrieving results'
                        }
                    },
                    'required': ['text'],
                    'type': 'object'
                }
            }
        }
        ```

    `search_web.gemini_schema`

    !!! success "Gemini Schema"

        ```python
        {
            "type": "function",
            "function": {
                'name': 'search_web',
                'parameters': {
                    'required': ['text'],
                    'type': 'object',
                    'properties': {
                        'text': {
                            'description': 'Text to search for',
                            'type': 'string'
                        },
                        'backend': {
                            'description': 'Backend to use for retrieving results',
                            'enum': ['api', 'html', 'lite'],
                            'format': 'enum',
                            'type': 'string'
                        }
                    }
                }
            }
        }
        ```

    Validating inputs against the schema:

    ```python
    print(search_web.validate_input({"text": "LLMs", "backend": "api"}))
    # OR
    print(search_web.validate_input('{"text": "LLMs", "backend": "api"}')) # JsON Input
    ```

    !!! success "Result"

        ```
        No results found for 'LLMs' in 'api' backend.
        ```

## StructAdapter

A wrapper around pydantic's `TypeAdapter` for schema and definition generation with capability to
validate input from python or JsON object.

Structured types such as Pydantic Models, TypedDict, dataclasses, etc. are supported.

Useful for schema-driven representations of complex types for use in function calling,
serialization, and documentation contexts.

Creating a `StructAdapter` instance is straightforward:

```python
from typing_extensions import TypedDict
from orchestr8.adapter import StructAdapter

class ProductInfo(TypedDict):
    """
    Information about the product.

    :param name: Name of the product
    :param price: Price of the product
    :param in_stock: If the product is in stock
    """
    name: str
    price: float
    in_stock: bool

adapter = StructAdapter(ProductInfo)
```

For more on how to use the instance, refer: [@adapt decorator](#adapt-decorator) "Working with adapter instance" section.

## FunctionAdapter

A specialized adapter for Python functions, extending StructAdapter to handle function-specific type hints.

Creating a `FunctionAdapter` instance is straightforward:

```python
from orchestr8.adapter import FunctionAdapter

def search_web(
    text: str,
    backend: Literal['api', 'html', 'lite'] = 'api',
):
    """
    Search the web.

    :param text: Text to search for
    :param backend: Backend to use for retrieving results
    """
    return f"No results found for {text!r} in {backend!r} backend."

adapter = FunctionAdapter(search_web)
```

For more on how to use the instance, refer: [@adapt decorator](#adapt-decorator) "Working with adapter instance" section.
