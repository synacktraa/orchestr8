Execution runtime is one of the most interesting components in Orchestr8. It allows you to run Python scripts and created projects in the host or isolated virtual environments. It utilizes uv to provide a simple and efficient way to manage and run Python projects and scripts.

There are two types of execution runtimes:

- `ExecutionRuntime`: This runtime is used to run Python scripts and created projects in the host machine.
- `IsolatedExecutionRuntime`: This runtime is used to run Python scripts and created projects in docker containers.

## Creating Projects

To create a project, you can use the `create_project` function. This function takes a python script, extracts its dependencies and creates a uv project. Created projects can be used through both host and isolated runtimes.

```python
import orchestr8 as o8

o8.create_project(
    "/path/to/script_name.py",
    id="project_id", # Not required, defaults to script name.
    requirements=True,
)
```

There are three values that can be passed to the `requirements` parameter:

- `True`: Auto-generate requirements from the script. To know more refer [generate_requirements](../api_reference/execution-runtime.md/#orchestr8.execution_runtime.package_utils.generate_requirements) function.
- `["package==1.0.0"]`: List of requirement strings.
- `None`: Don't add any dependencies. (Default)

All projects are created in the `~/.orchestr8/runtime/projects` directory.

!!! success "Listing ~/.orchestr8/runtime/projects/project_id"

    ```
    .venv
    main.py
    pyproject.toml
    requirements.txt
    uv.lock
    ```

> `requirements.txt` is used by isolated runtimes to install dependencies in virtual environments inside containers

## Using Runtime Instances

To create a runtime instance, you can use the `create_execution_runtime` function. This function takes an `isolate` parameter, which determines whether to use an isolated runtime or the host runtime.

> If you're already inside a container, it will default to using the host runtime

```python
import orchestr8 as o8

runtime = o8.create_execution_runtime(isolate=True)
```

You can also pass `python_tag` and `docker_config` parameters to customize the isolated runtime.

> Isolation requires docker, refer [here](https://docs.docker.com/engine/install/) for installation instructions

!!! Example "Running a created project"

    To run a created project, you can use the `run_project` method. It requires the `id` of the project.

    You can also pass arguments and environment variables to the project if needed.

    ```python
    output = runtime.run_project('project_id', '--param1', 'value1', env={"ENV_VAR": "value"})
    ```

!!! Example "Running a script"

    You can run a script directly without needing to create a project using on-demand environments provided by `uv`. To do this, you can use the `run_script` method. It takes parameters required by both `create_project` function and `run_project` method.

    > To know more about on-demand environments, refer [uv docs](https://docs.astral.sh/uv/guides/scripts/#running-a-script-with-dependencies)

    ```python
    output = runtime.run_script(
        'script1.py', '-p1', 'value1', requirements=True, env={"ENV_VAR": "value"}
    )
    ```

### ExecutionRuntime (host-based)

Interface for running Python scripts and created projects in the host machine.

```python
from orchestr8.execution_runtime import ExecutionRuntime

# Create a host execution runtime instance
runtime = ExecutionRuntime()

# Run a script with auto-generated requirements
output = runtime.run_script('script1.py', '-p1', 'value1', requirements=True)

# Run a script with pre-defined requirements
output = runtime.run_script('script2.py', requirements=["requests==2.25.1"])

# Run a created project
output = runtime.run_project('project_id', '--param1', 'value1')
```

### IsolatedExecutionRuntime

Interface for running Python scripts and created projects in isolated environments.

> Isolation requires docker, refer [here](https://docs.docker.com/engine/install/) for installation instructions

```python
from orchestr8.execution_runtime import IsolatedExecutionRuntime

# Create an isolated execution runtime instance
runtime = IsolatedExecutionRuntime(isolate=True, python_tag="3.10-alpine3.20")

# Run a script with auto-generated requirements
output = runtime.run_script('script1.py', '-p1', 'value1', requirements=True)

# Run a script with pre-defined requirements
output = runtime.run_script('script2.py', requirements=["requests==2.25.1"])

# Run a created project
output = runtime.run_project('project_id', '--param1', 'value1')
```
