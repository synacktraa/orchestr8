from __future__ import annotations

import os
import shutil
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from re import match as re_match
from typing import Any, Dict, List, Literal, Protocol, Tuple

from .._paths import ISOLATED_RUNTIME_VENVS_VOLUME_DIR, RUNTIME_PROJECTS_DIR
from ..logger import Logger
from ..sandbox_client import SandboxClient
from ..shell import IsolatedShell, Shell
from .package_utils import Dependency, extract_module_names, generate_requirements

__all__ = "create_project", "create_execution_runtime"

os.environ["VIRTUAL_ENV"] = ""

EXECUTOR_IMAGE_TEMPLATE = """\
FROM python:{python_tag}

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

CMD ["tail", "-f", "/dev/null"]\
"""


class SupportsStr(Protocol):
    def __str__(self) -> str: ...


def project_exists(__id: str) -> bool:
    """
    Check if a project with the given id exists.

    Args:
        __id: The id of the project to check

    Returns:
        True if the project exists, False otherwise
    """
    return (RUNTIME_PROJECTS_DIR / __id).exists()


def _validate_script_and_requirements(
    script: str | Path | BytesIO,
    requirements: List[str] | Literal[True] | None = None,
    dependency_overrides: Dict[str, Dependency] | None = None,
) -> Tuple[Path, List[str] | None]:
    """Helper function for `create_project` and `run_script` methods."""
    if isinstance(script, BytesIO):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
            _script = Path(tmp_file.name)
            _script.write_bytes(script.read())
            script = _script
    else:
        script = Path(script)
        if not script.is_file():
            raise FileNotFoundError(f"Script {str(script)!r} not found")

    if requirements is True:
        requirements = generate_requirements(extract_module_names(script), dependency_overrides)

    return script, requirements


def create_project(
    __script: str | Path,
    *,
    id: str | None = None,  # noqa: A002
    requirements: List[str] | Literal[True] | None = None,
    dependency_overrides: Dict[str, Dependency] | None = None,
    force: bool = False,
) -> None:
    """
    Create a uv project from a python script.

    ```python
    create_project(
        "/path/to/script.py",
        id="project_id", # Not required, defaults to script name.
        requirements=["package=0.0.0"], # Set `True` to auto generate
    )
    ```

    Refer `orchestr8.execution_runtime.package_utils.generate_requirements` to know more
    about auto-generation of requirements from python source file and `dependency_overrides`.

    Args:
        __script: The python script to create project from
        id: The id to use for the project. Defaults to the script name
        requirements: List of requirement strings (e.g., ["package==1.0.0"]) or True to auto-generate
        dependency_overrides: Depedency overrides. Applicable only if requirements=True
        force: Whether to force create the project even if it's already available

    Raises:
        FileNotFoundError: If the script file is not found

    """
    project_id = id or Path(__script).stem
    project_dir = RUNTIME_PROJECTS_DIR / project_id
    if project_exists(project_id):
        if not force:
            raise FileExistsError(f"Project with id {project_id!r} already exists." " Use `force=True` to overwrite.")
        shutil.rmtree(project_dir, ignore_errors=True)

    script, requirements = _validate_script_and_requirements(
        __script, requirements=requirements, dependency_overrides=dependency_overrides
    )

    shell = Shell(workdir=RUNTIME_PROJECTS_DIR)

    # Creating a new project
    shell.run("uv", "init", "--vcs", "none", "--no-readme", "--no-workspace", "--no-pin-python", project_id)

    # Deleting default hello.py created by uv
    (project_dir / "hello.py").unlink(missing_ok=True)
    # Copy the script to `main.py` in the project directory
    (project_dir / "main.py").write_bytes(script.read_bytes())

    if requirements:
        # Add dependencies to the project
        shell.run("uv", "add", "--directory", project_id, *requirements)

        # Create a requirements.txt file for isolated runtime virtual environments
        shell.run(
            "uv",
            "export",
            "--directory",
            project_id,
            "--no-editable",
            "--no-emit-project",
            "--no-header",
            "--locked",
            "--format",
            "requirements-txt",
            "-o",
            "requirements.txt",
        )


class ExecutionRuntime(Logger):
    """
    Interface for running Python scripts and created projects in the host machine.

    ```python
    # Create a host execution runtime instance
    runtime = ExecutionRuntime()

    # Run a script with auto-generated requirements
    output = runtime.run_script('script1.py', '-p1', 'value1', requirements=True)

    # Run a script with pre-defined requirements
    output = runtime.run_script('script2.py', requirements=["requests==2.25.1"])

    # Run a created project
    output = runtime.run_project('project_id', '--param1', 'value1')
    ```
    """

    def __init__(self) -> None:
        """Initialize the runtime."""
        self.__shell = Shell(workdir=RUNTIME_PROJECTS_DIR)
        if os.name == "nt":
            self._py_exe_loc = "Scripts"  # windows
        else:
            self._py_exe_loc = "bin"  # unix

    @property
    def shell(self) -> Shell:
        """The shell instance."""
        return self.__shell

    def run_project(self, __id: str, *args: SupportsStr, env: Dict[str, str] | None = None) -> str | None:
        """
        Run the project with the given id.

        Args:
            __id: The id of the project to run
            args: The arguments to pass to the script associated with the project
            env: Environment variables required by the project

        Returns:
            The output of the script

        Raises:
            FileNotFoundError: If the project with the given id does not exist
        """
        if not project_exists(__id):
            raise FileNotFoundError(f"Project with id {__id!r} not found.")

        project_dir = RUNTIME_PROJECTS_DIR / __id
        python_exe = str(project_dir / ".venv" / self._py_exe_loc / "python")
        main_py = str(project_dir / "main.py")
        return self.__shell.run(python_exe, main_py, *list(map(str, args)), env=env)

    def run_script(
        self,
        __script: str | Path | BytesIO,
        *args: SupportsStr,
        env: Dict[str, str] | None = None,
        requirements: List[str] | Literal[True] | None = None,
        dependency_overrides: Dict[str, Dependency] | None = None,
    ) -> str | None:
        """
        Run a python script inside on-demand environment.

        Reference: https://docs.astral.sh/uv/guides/scripts/#running-a-script-with-dependencies

        To know more about auto-generation of requirements from python source
        file, refer `orchestr8.execution_runtime.package_utils.generate_requirements`.

        Args:
            __script: The python script to run
            args: The arguments to pass to the script
            env: Environment variables required by the script
            requirements: List of requirement strings (e.g., ["package==1.0.0"]) or True to auto-generate
            dependency_overrides: Depedency overrides. Applicable only if requirements=True

        Returns:
            The output of the script
        """
        script, requirements = _validate_script_and_requirements(
            script=__script, requirements=requirements, dependency_overrides=dependency_overrides
        )

        self.logger.info(f"Running script {script.name!r}")
        cmd = ["uv", "run", "--no-project", "--quiet"]
        if requirements:
            cmd.extend(["--with", *requirements])
        cmd.append(str(script.absolute()))
        if args:
            cmd.extend(list(map(str, args)))
        return self.__shell.run(*cmd, env=env)


class IsolatedExecutionRuntime(Logger):
    """
    Interface for running Python scripts and created projects in isolated environments.

    ```python
    # Create an isolated execution runtime instance
    runtime = IsolatedExecutionRuntime(isolate=True, python_tag="3.10-alpine3.20")

    # Run a script with auto-generated requirements
    output = runtime.run_script('script1.py', '-p1', 'value1', requirements=True)

    # Run a script with pre-defined requirements
    output = runtime.run_script('script2.py', requirements=["requests==2.25.1"])

    # Run a created project
    output = runtime.run_project('project_id', '--param1', 'value1')
    ```
    """

    def __init__(self, *, python_tag: str | None = None, **docker_config: Any) -> None:
        """
        Initialize the runtime.

        :param python_tag: Python image tag. Defaults to 3.10-alpine3.20.
        :type python_tag: str | None
        :param docker_config: Docker client configuration.
        :type docker_config: dict[str, Any]
        """
        minor, major = sys.version_info[:2]
        python_tag = python_tag or f"{minor}.{major}-alpine3.20"

        if not (m := re_match(r"^(\d+\.\d+)", python_tag)):
            raise ValueError(f"Invalid python tag: {python_tag!r}")

        python_version: str = m.group(1)
        self.__venvs_dir = ISOLATED_RUNTIME_VENVS_VOLUME_DIR / python_version
        if not self.__venvs_dir.is_dir():
            self.__venvs_dir.mkdir(exist_ok=True)

        py_image = f"python:{python_tag}"
        self.__sb_client = SandboxClient(**docker_config)
        if not self.__sb_client.image_exists(py_image) and not (
            self.__sb_client.image_exists(py_image, where="registry")
        ):
            raise Exception(f"Python image {py_image!r} not found on docker hub.")

        executor_image = f"orchestr8-runtime:py-{python_tag}"
        if not self.__sb_client.image_exists(executor_image):
            self.__sb_client.build_image(
                image=executor_image, dockerfile=BytesIO(EXECUTOR_IMAGE_TEMPLATE.format(python_tag=python_tag).encode())
            )

        # Project directory inside the container, host project directory is mounted
        projs_dir_mount = "/var/o8-projects"
        container = self.__sb_client.run_container(
            executor_image,
            volumes={
                RUNTIME_PROJECTS_DIR: {"bind": projs_dir_mount, "mode": "ro"},
                self.__venvs_dir: {"bind": "/var/o8-venvs", "mode": "rw"},
            },
            detach=True,
            stderr=True,
            remove=True,
        )
        self.__shell = IsolatedShell(container=container, workdir=projs_dir_mount)

    @property
    def shell(self) -> IsolatedShell:
        """The shell instance."""
        return self.__shell

    def run_project(self, __id: str, *args: SupportsStr, env: Dict[str, str] | None = None) -> str | None:
        """
        Run the project with the given id.

        Args:
            __id: The id of the project to run
            args: The arguments to pass to the script associated with the project
            env: Environment variables required by the project

        Returns:
            The output of the script

        Raises:
            FileNotFoundError: If the project with the given id does not exist
        """
        if not project_exists(__id):
            raise FileNotFoundError(f"Project with id {__id!r} not found.")

        venv_dir_mount = Path("/var") / "o8-venvs" / __id
        proj_dir_mount = Path("/var") / "o8-projects" / __id
        if not (self.__venvs_dir / __id).exists():
            self.logger.info(f"Creating virtual environment for project {__id!r}")
            self.__shell.run("uv", "venv", "--no-project", venv_dir_mount.as_posix())

            if (RUNTIME_PROJECTS_DIR / __id / "requirements.txt").exists():
                self.logger.info(f"Installing requirements for project {__id!r}")
                self.__shell.run(
                    "uv",
                    "pip",
                    "install",
                    "-r",
                    (proj_dir_mount / "requirements.txt").as_posix(),
                    env={"VIRTUAL_ENV": venv_dir_mount.as_posix()},
                )

        python_exe = (venv_dir_mount / "bin" / "python").as_posix()
        main_py = (proj_dir_mount / "main.py").as_posix()
        return self.__shell.run(python_exe, main_py, *list(map(str, args)), env=env)

    def run_script(
        self,
        __script: str | Path | BytesIO,
        *args: SupportsStr,
        env: Dict[str, str] | None = None,
        requirements: List[str] | Literal[True] | None = None,
        dependency_overrides: Dict[str, Dependency] | None = None,
    ) -> str | None:
        """
        Run a python script inside on-demand environment.

        Reference: https://docs.astral.sh/uv/guides/scripts/#running-a-script-with-dependencies

        To know more about auto-generation of requirements from python source
        file, refer `orchestr8.execution_runtime.package_utils.generate_requirements`.

        Args:
            __script: The python script to run.
            args: The arguments to pass to the script
            env: Environment variables required by the script
            requirements: List of requirement strings (e.g., ["package==1.0.0"]) or True to auto-generate
            dependency_overrides: Depedency overrides. Applicable only if requirements=True

        Returns:
            The output of the script
        """
        script, requirements = _validate_script_and_requirements(
            script=__script, requirements=requirements, dependency_overrides=dependency_overrides
        )
        self.__sb_client.copy_path_to_container(self.__shell.container.id, src=script, target="/tmp")  # noqa: S108

        self.logger.info(f"Running script {script.name!r}")
        cmd = ["uv", "run", "--no-project", "--quiet"]
        if requirements:
            cmd.extend(["--with", *requirements])
        cmd.append(f"/tmp/{script.name}")  # noqa: S108
        if args:
            cmd.extend(list(map(str, args)))
        return self.__shell.run(*cmd, env=env)


def create_execution_runtime(
    isolate: bool = False, python_tag: str | None = None, **docker_config: Any
) -> ExecutionRuntime | IsolatedExecutionRuntime:
    """
    Create execution runtime instance for running Python scripts and created projects.

    ```python
    runtime = create_execution_runtime(isolate=True, python_tag="3.10-alpine3.20")

    # Run a script with auto-generated requirements
    output = runtime.run_script('script1.py', '-p1', 'value1', requirements=True)

    # Run a script with pre-defined requirements
    output = runtime.run_script('script2.py', requirements=["requests==2.25.1"])

    # Run a created project
    output = runtime.run_project('project_id', '--param1', 'value1')
    ```

    Args:
        isolate: Whether to isolate the runtime. Defaults to False
        python_tag: Python image tag. Defaults to 3.10-alpine3.20. Applicable, if `isolate is True`
        docker_config: Docker client configuration. Applicable, if `isolate is True`

    Returns:
        Runtime instance
    """
    if isolate:
        if (proc := Path("/proc/1/cgroup")).exists() and "docker" in proc.read_text():
            ExecutionRuntime.logger.info("Already inside a container. Switched to host.")
            return ExecutionRuntime()

        IsolatedExecutionRuntime.logger.info("Setting up the instance")
        return IsolatedExecutionRuntime(python_tag=python_tag, **docker_config)

    ExecutionRuntime.logger.info("Setting up the instance")
    return ExecutionRuntime()
