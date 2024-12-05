Let's face it: Large Language Models (LLMs) are brilliant at generating code, but they're not infallible. They can hallucinate functions, introduce security risks, and occasionally produce code that looks convincing but is fundamentally broken.

This cookbook is your safety net. We'll explore how to execute LLM-generated code in a controlled, isolated environment—transforming your skepticism into a structured approach for safe code exploration.

Think of it like handling a fascinating but unpredictable exotic pet: you want to marvel at its capabilities while ensuring it can't accidentally wreck your entire digital ecosystem.

## Installation and Setup

> Make sure you have `docker` installed on your system. Refer to the [docker installation guide](https://docs.docker.com/engine/install/) for more details.

This cookbook requires the `litellm` library for code generation via the Groq provider.

If you don't have an API key for Groq, you can get one at [Groq Console](https://console.groq.com/keys).

```python
%pip install orchestr8[execution-runtime] litellm

import os, getpass

def set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

set_env("GROQ_API_KEY")
```

```python
import re
from io import BytesIO

from litellm import completion

# Yoinked from https://github.com/ShishirPatil/gorilla/blob/main/goex/exec_engine/pipeline.py#L14
INSTRUCTION = """\
You are an assistant that outputs executable Python code that perform what the user requests.
It is important that you only return one and only one code block with all the necessary imports inside ```python and nothing else.
The code block should print the output(s) when appropriate.

If the action can't be successfully completed, throw an exception.
"""

def generate_code(request: str) -> BytesIO | None:
    response = completion(
        model="groq/llama-3.1-70b-versatile",
        messages=[
            {"role": "system", "content": INSTRUCTION},
            {"role": "user", "content": request}
        ],
    )
    content: str = response.choices[0].message.content
    match = re.search(r"```python\n(.*?)```", content, re.DOTALL) # search for the code block
    if match:
        # extract the code block
        code = match.group(1)
        print(code)
        return BytesIO(code.encode())
```

## Creating an isolated runtime

Execution runtime uses `uv` to run python scripts and projects inside virtual environments.

```python
import orchestr8 as o8

runtime = o8.create_execution_runtime(isolate=True)
```

> The first time you run this, it will take a minute or two to setup the container.

!!! success "Logs"

    ```
    [IsolatedExecutionRuntime] Setting up the instance
    [SandboxClient] Building image 'orchestr8-runtime:py-3.10-alpine3.20' from dockerfile
    [SandboxClient] Step 1/3 : FROM python:3.10-alpine3.20
    [SandboxClient]
    [SandboxClient] ---> 039508c234f8
    [SandboxClient] Step 2/3 : COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
    [SandboxClient]
    [SandboxClient] ---> 1cc5c59fffc4
    [SandboxClient] Step 3/3 : CMD ["tail", "-f", "/dev/null"]
    [SandboxClient]
    [SandboxClient] ---> Running in 48e67352a232
    [SandboxClient] ---> Removed intermediate container 48e67352a232
    [SandboxClient] ---> d92b0d627dbe
    [SandboxClient] Successfully built d92b0d627dbe
    [SandboxClient] Successfully tagged orchestr8-runtime:py-3.10-alpine3.20
    [SandboxClient] Starting up container from image 'orchestr8-runtime:py-3.10-alpine3.20'
    ```

## Generating and running the code

We're going to ask a query where the LLM includes a third party library in the generated code to show why running the code using orchestr8's execution runtime is beneficial.

```python
code = generate_code("""\
Write a python function that uses requests library to fetch github user information.
Include an example of fetching the user "synacktraa".
""")
```

!!! success "Result"

    ```python
    import requests
    import json

    def fetch_github_user_info(username):
        try:
            url = f"https://api.github.com/users/{username}"
            response = requests.get(url)

            if response.status_code == 200:
                user_info = response.json()
                print(json.dumps(user_info, indent=4))
            else:
                raise Exception(f"Failed to fetch user information. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"An error occurred: {e}")

    fetch_github_user_info("synacktraa")
    ```

To run this code inside the runtime, we can use the `run_script` method.

The `run_script` creates an on-demand environment for the script and runs it inside it. It also installs the third party dependencies (if any) specified in the script.

```python
output = runtime.run_script(code, requirements=True)
print(output)
```

If you take a look at the third log message, you'll notice that the script is ran with `requests==2.32.3` dependency. If you wish to know more about this `auto-generation` of requirements, refer [`generate_requirements` function](../api_reference/execution-runtime.md/#orchestr8.execution_runtime.package_utils.generate_requirements).

!!! success "Logs and Result"

    ```
    [SandboxClient] Copying 'C:\\Users\\synac\\AppData\\Local\\Temp\\tmpwz_hvchz.py' to '/tmp' inside container(sid='de0a74e929ce')
    [IsolatedExecutionRuntime] Running script 'tmpwz_hvchz.py'
    [IsolatedShell] ⚙️  || uv run --no-project --quiet --with requests==2.32.3 /tmp/tmpwz_hvchz.py
    {
        "login": "synacktraa",
        "id": 91981716,
        "node_id": "U_kgDOBXuHlA",
        "avatar_url": "https://avatars.githubusercontent.com/u/91981716?v=4",
        "gravatar_id": "",
        "url": "https://api.github.com/users/synacktraa",
        "html_url": "https://github.com/synacktraa",
        "followers_url": "https://api.github.com/users/synacktraa/followers",
        "following_url": "https://api.github.com/users/synacktraa/following{/other_user}",
        "gists_url": "https://api.github.com/users/synacktraa/gists{/gist_id}",
        "starred_url": "https://api.github.com/users/synacktraa/starred{/owner}{/repo}",
        "subscriptions_url": "https://api.github.com/users/synacktraa/subscriptions",
        "organizations_url": "https://api.github.com/users/synacktraa/orgs",
        "repos_url": "https://api.github.com/users/synacktraa/repos",
        "events_url": "https://api.github.com/users/synacktraa/events{/privacy}",
        "received_events_url": "https://api.github.com/users/synacktraa/received_events",
        "type": "User",
        "user_view_type": "public",
        "site_admin": false,
        "name": "Harsh Verma",
        "company": null,
        "blog": "",
        "location": "India",
        "email": null,
        "hireable": null,
        "bio": "Hidden in the chaos is the element.",
        "twitter_username": null,
        "public_repos": 45,
        "public_gists": 6,
        "followers": 48,
        "following": 29,
        "created_at": "2021-10-05T17:57:09Z",
        "updated_at": "2024-12-01T05:29:46Z"
    }
    ```

As you can see, you only require a runtime instance and [`.run_script` method](../api_reference/execution-runtime.md#orchestr8.execution_runtime.IsolatedExecutionRuntime.run_script) to run the code.

If you wish to persist the code as a uv project, you can use the [`.create_project` method](../api_reference/execution-runtime.md#create_project-function) which can save you a lot of time as the third party dependencies are installed only once. Then you can utilise the [`.run_project` method](../api_reference/execution-runtime.md#orchestr8.execution_runtime.IsolatedExecutionRuntime.run_project) to run the project whenever you need.
