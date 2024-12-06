Integrating Large Language Models (LLMs) with file system access introduces significant risks. AI models, while powerful, can unpredictably interact with files due to:

- Misinterpreting context
- Lacking understanding of file system consequences
- Potential hallucinations leading to destructive actions

This cookbook presents a systematic approach to mitigating these risks by implementing version tracking and change management mechanisms, ensuring safe and controlled file system interactions with LLMs.

## Installation and Setup

This cookbook requires the `litellm` library for function-call generation via the Groq provider.

If you don't have an API key for Groq, you can get one at [Groq Console](https://console.groq.com/keys).

> `DirectoryTracker` component requires `git` for version control, you can download it from [here](https://git-scm.com/downloads)

```python
%pip install orchestr8[adapter] litellm

import os, getpass

def set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

set_env("GROQ_API_KEY")
```

```python
import json
from typing import Any, Dict, List

from litellm import completion

INSTRUCTION = "Complete user requests using the given functions."

def generate_function_call(request: str, functions: List[Dict[str, Any]]):
    response = completion(
        model="groq/llama3-groq-70b-8192-tool-use-preview",
        messages=[
            {"role": "system", "content": INSTRUCTION},
            {"role": "user", "content": request}
        ],
        tools=functions
    )
    tool_call = response.choices[0].message.tool_calls[0].function
    if tool_call is None:
        print(response.choices[0].message.content)
        raise Exception("No function call found in the response.")
    return tool_call.name, json.loads(tool_call.arguments)
```

## Creating a tracker instance

`DirectoryTracker` wraps Git commands to provide simple version control capabilities, including tracking changes, committing modifications, and undoing uncommitted changes. Supports large files through Git LFS when directory size exceeds a configurable limit.

```python
import orchestr8 as o8

from pathlib import Path
from tempfile import tempdir

directory = Path(tempdir) / "orchestr8-tracking" # We'll be working inside this directory
directory.mkdir(exist_ok=True)

tracker = o8.DirectoryTracker(path=directory)

print(f"Listing {str(directory)}")
print(tracker.shell.run("ls")) # Returns None, because the directory is empty
```

!!! success "Logs and Result"

    ```
    [DirectoryTracker] Initializing git repository
    [Shell] ⚙️  || git init
    [DirectoryTracker] Staging all changes
    [Shell] ⚙️  || git add .
    [DirectoryTracker] Creating an empty commit
    [Shell] ⚙️  || git commit -m "[Thu, Dec 05, 2024 11:08 AM] tracker init" --allow-empty --no-verify
    Listing /tmp/orchestr8-tracking
    [Shell] ⚙️  || ls
    None
    ```

## Creating adapters from functions

Creating adapters is as simple as defining a function and decorating it with `@adapt` decorator.

```python
from pathlib import Path

import orchestr8 as o8

@o8.adapt
def read_file(path: Path) -> str:
    """
    Read the contents of a file.

    :param path: Path to the file
    :return: File contents
    """
    if not path.is_file():
        raise FileNotFoundError(f"File {path} not found.")
    return path.read_text()

@o8.adapt
def write_file(path: Path, content: str, overwrite: bool = False) -> None:
    """
    Write content to a file.

    :param path: Path to the file
    :param content: Content to write
    :param overwrite: Whether to overwrite the file if it exists
    """
    if path.is_file() and not overwrite:
        raise FileExistsError(
            f"File {path} already exists, set overwrite=True to overwrite it."
        )
    if not path.is_file():
        path.touch()
    path.write_text(content)


@o8.adapt
def delete_file(path: Path) -> None:
    """
    Delete a file.

    :param path: Path to the file
    """
    if not path.is_file():
        raise FileNotFoundError(f"File {path} not found.")
    path.unlink()
```

## Generating function-calls and tracking changes

Get ready for a version control adventure! We'll demonstrate how to safely interact with files using an AI assistant.

```python
function_call = generate_function_call(
    f"Write 'Hello LLM' to {str(directory / 'new.txt')!r} file",
    functions=[write_file.openai_schema]
)
print(function_call)
```

!!! success "Result"

    ```python
    ('write_file', {'path': '/tmp/orchestr8-tracking/new.txt', 'content': 'Hello LLM'})
    ```

Let's validate and write our file into the directory.

```python
write_file.validate_input(function_call[1])
```

Curious if our actions left any traces? Let's inspect the directory's status!

```python
print(tracker.has_changes)
```

!!! success "Logs and Result"

    ```
    [DirectoryTracker] Checking for uncommitted changes
    [Shell] ⚙️  || git status --porcelain
    True
    ```

Time to peek inside our directory and see what's been created!

```python
print(tracker.shell.run("ls"))
```

!!! success "Logs and Result"

    ```
    [Shell] ⚙️  || ls
    new.txt
    ```

Made a mistake? No worries! We'll show you how to roll back changes instantly.

```python
tracker.undo()
```

!!! success "Logs"

    ```
    [DirectoryTracker] Removing untracked files and directories
    [Shell] ⚙️  || git clean -fd
    [DirectoryTracker] Resetting all tracked files to their last committed state
    [Shell] ⚙️  || git reset --hard HEAD
    ```

Let's double-check that our undo worked perfectly.

```python
print(tracker.shell.run("ls"))
```

!!! success "Logs and Result"

    ```
    [Shell] ⚙️  || ls
    None
    ```

Let's give it another shot and see the magic happen!

```python
function_call = generate_function_call(
    f"Write bubble sort algorithm to {str(directory / 'sort.py')!r} file",
    functions=[write_file.openai_schema]
)
print(function_call)
write_file.validate_input(function_call[1])
```

!!! success "Result"

    ```python
    ('write_file', {'path': '/tmp/orchestr8-tracking/sort.py', 'content': 'def bubble_sort(arr):\n    n = len(arr)\n\n    for i in range(n):\n        for j in range(0, n - i - 1):\n            if arr[j] > arr[j + 1]:\n                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n\n    return arr\n\narr = [64, 34, 25, 12, 22, 11, 90]\nprint(bubble_sort(arr))'})
    ```

Peek inside the newly created file and marvel at the AI-generated code!

```python
print(tracker.shell.run("cat", "sort.py"))
```

!!! success "Logs and Result"

    ```
    [Shell] ⚙️  || cat sort.py
    def bubble_sort(arr):
        n = len(arr)

        for i in range(n):
            for j in range(0, n - i - 1):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]

        return arr

    arr = [64, 34, 25, 12, 22, 11, 90]
    print(bubble_sort(arr))
    ```

Time to make our changes permanent with a commit!

```python
tracker.commit("Added sort.py")
```

!!! success "Logs"

    ```
    [DirectoryTracker] Staging all changes
    [Shell] ⚙️  || git add .
    [DirectoryTracker] Persisting uncommitted changes
    [Shell] ⚙️  || git commit -m "[Thu, Dec 05, 2024 11:21 AM] Added sort.py"
    ```

Did our commit go through? Let's check the status!

```python
print(tracker.has_changes)
```

!!! success "Logs and Result"

    ```
    [DirectoryTracker] Checking for uncommitted changes
    [Shell] ⚙️  || git status --porcelain
    False
    ```

Watch what happens when we ask the LLM to delete our carefully crafted file!

```python
function_call = generate_function_call(
    f"Delete the {str(directory / 'sort.py')!r} file",
    functions=[delete_file.openai_schema]
)
print(function_call)
delete_file.validate_input(function_call[1])
```

!!! success "Result"

    ```python
    ('delete_file', {'path': '/tmp/orchestr8-tracking/sort.py'})
    ```

The tracker is vigilant! Let's see if it catches our file deletion.

```python
print(tracker.has_changes)
```

!!! success "Logs and Result"

    ```
    [DirectoryTracker] Checking for uncommitted changes
    [Shell] ⚙️  || git status --porcelain
    True
    ```

Our directory's current state? Let's take a look!

```python
print(tracker.shell.run("ls"))
```

!!! success "Logs and Result"

    ```
    [Shell] ⚙️  || ls
    None
    ```

No problem! We can easily restore our deleted file.

```python
tracker.undo()
```

!!! success "Logs"

    ```
    [DirectoryTracker] Removing untracked files and directories
    [Shell] ⚙️  || git clean -fd
    [DirectoryTracker] Resetting all tracked files to their last committed state
    [Shell] ⚙️  || git reset --hard HEAD
    ```

Confirming our file is back where it belongs!

```python
print(tracker.shell.run("ls"))
```

!!! success "Logs and Result"

    ```
    [Shell] ⚙️  || ls
    sort.py
    ```

Let's peek at our restored file one more time.

```python
print(tracker.shell.run("cat", "sort.py"))
```

!!! success "Logs and Result"

    ```
    [Shell] ⚙️  || cat sort.py
    def bubble_sort(arr):
        n = len(arr)

        for i in range(n):
            for j in range(0, n - i - 1):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]

        return arr

    arr = [64, 34, 25, 12, 22, 11, 90]
    print(bubble_sort(arr))
    ```

Time to clean up our tracking!

```python
tracker.delete()
print(tracker.is_tracking)
```

!!! success "Logs and Result"

    ```
    [DirectoryTracker] Checking for uncommitted changes
    [Shell] ⚙️  || git status --porcelain
    [DirectoryTracker] Deleting .git directory
    [Shell] ⚙️  || rm -rf .git
    False
    ```

One final look at our directory.

```python
print(tracker.shell.run("ls"))
```

!!! success "Logs and Result"

    ```
    [Shell] ⚙️  || ls
    sort.py
    ```
