from __future__ import annotations

import os
import subprocess
from collections.abc import Generator
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any, Dict, Tuple

if TYPE_CHECKING:
    from docker.models.containers import Container  # type: ignore[import-untyped]

from .logger import Logger

__all__ = "Shell", "IsolatedShell"


class ShellException(Exception): ...


def raise_on_failure(cmd: Tuple[str, ...], error: str) -> None:
    """Raise a ShellException if the command fails."""
    raise ShellException(f"Command {' '.join(cmd)!r} failed.\n{error}")


def format_log(cmd: Tuple[str, ...]) -> str:
    """Format the command log."""
    return "⚙️  || <fg #d7eac2>{cmd}</fg #d7eac2>".format(cmd=" ".join(cmd))


class Shell(Logger):
    """
    Interface for running commands in host machine.

    If host is windows, all commands are executed using `PowerShell`.

    ⚠️ WARNING: This class allows execution of system commands and should be used with EXTREME CAUTION.

    - Never run commands with user-supplied or untrusted input
    - Always validate and sanitize any command arguments
    - Be aware of potential security risks, especially with privilege escalation

    ```python
    # Initialize the shell
    shell = Shell(workdir="/path/to/directory")

    # Run command
    print(shell.run("echo", "'Hello from shell!'"))

    # Stream run command
    for line in shell.stream("echo", "Hello from shell!"):
        print(line)
    ```
    """

    def __init__(
        self,
        *,
        workdir: str | Path | None = None,
        raise_on_non_zero: bool = False,
    ) -> None:
        """
        Initialize the CommandExecutor.

        Args:
            workdir: The working directory to execute commands in
            raise_on_non_zero: Whether to raise an exception if the command returns non-zero exit code
        """
        if workdir:
            w_dir = Path(workdir)
            if not w_dir.is_dir():
                raise NotADirectoryError(f"{str(w_dir)!r} is not a directory.")
            self.__workdir = PurePath(w_dir)
        else:
            self.__workdir = PurePath(Path.cwd())

        self.__raise_on_non_zero = raise_on_non_zero

    @staticmethod
    def __validate_cmd(cmd: Tuple[str, ...]) -> Tuple[str, ...]:
        if os.name == "nt" and "SHELL" not in os.environ:
            return ("powershell", "-NoProfile", "-NonInteractive", "-Command", *cmd)
        return cmd

    @property
    def workdir(self) -> PurePath:
        """The working directory."""
        return self.__workdir

    def __prepare_common_kwargs(self, env: Dict[str, str] | None = None) -> Dict[str, Any]:
        kwargs = {"cwd": self.__workdir, "text": True}
        if env:
            kwargs["env"] = {**os.environ, **env}
        return kwargs

    def run(self, *cmd: str, env: Dict[str, str] | None = None) -> str | None:
        """
        Run a command and return the output.

        Args:
            cmd: The arguments to pass as command
            env: Environment variables to set

        Returns:
            Output of the executed command

        Raises:
            ShellException: If the command returns non-zero exit code and raise_on_non_zero is False
        """
        self.logger.info(format_log(cmd))
        process: subprocess.CompletedProcess[str] = subprocess.run(  # noqa: S603
            self.__validate_cmd(cmd), capture_output=True, **self.__prepare_common_kwargs(env)
        )
        if error := process.stderr.strip():
            if process.returncode != 0 and self.__raise_on_non_zero:
                raise_on_failure(cmd, error)
            return error

        return process.stdout.strip() or None

    def stream(self, *cmd: str, env: Dict[str, str] | None = None) -> Generator[str, Any, None]:
        """
        Run a command and stream the output.

        Args:
            cmd: The arguments to pass as command
            env: Environment variables to set

        Returns:
            Output stream of the executed command

        Raises:
            ShellException: If the command returns non-zero exit code and raise_on_non_zero is False
        """
        self.logger.info(format_log(cmd))
        process = subprocess.Popen(  # noqa: S603
            self.__validate_cmd(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **self.__prepare_common_kwargs(env),
        )
        if error := process.stderr:
            if process.returncode != 0 and self.__raise_on_non_zero:
                raise_on_failure(cmd, "".join(error).strip())
            yield from error

        if output := process.stdout:
            yield from output


class IsolatedShell(Logger):
    """
    Interface for running commands inside a detached container.

    ```python
    from orchestr8.sandbox_client import SandboxClient

    # Create a detached container
    client = SandboxClient()
    container = client.run_container(
        "ubuntu:22.04", detach=True, remove=True
    )

    # Initialize the shell
    shell = IsolatedShell(
        container=container, workdir="/path/to/directory"
    )

    # Run command
    print(shell.run("echo", "Hello from shell!"))

    # Stream run command
    for line in shell.stream("ls", "-l"):
        print(line)
    ```
    """

    def __init__(  # type: ignore[no-any-unimported]
        self,
        *,
        container: Container,
        workdir: str | Path | None = None,
        raise_on_non_zero: bool = False,
    ) -> None:
        """
        Args:
            container: The detached container to execute commands in
            workdir: The working directory to execute commands in
            raise_on_non_zero: Whether to raise an exception if the command returns non-zero exit co
        """
        container.reload()
        if container.status != "running":
            raise ShellException("Container is not running.")
        self.__container = container
        self.__w_dir_str = None
        self.__raise_on_non_zero = raise_on_non_zero
        if workdir:
            self.__workdir = PurePath(workdir)
        else:
            self.__workdir = PurePath(self.run("pwd").strip())  # type: ignore[union-attr]
        self.__w_dir_str = self.__workdir.as_posix()

    @property
    def container(self) -> Container:  # type: ignore[no-any-unimported]
        """The container."""
        return self.__container

    @property
    def workdir(self) -> PurePath:
        """The working directory."""
        return self.__workdir

    def __exec(self, *cmd: str, **kwargs: Any) -> Any:
        self.logger.info(format_log(cmd))
        code, ret = self.__container.exec_run(cmd, workdir=self.__w_dir_str, **kwargs)
        if code != 0 and self.__raise_on_non_zero:
            self._stop_container()  # Is it right to stop the container before raising exception?
            raise_on_failure(cmd, ret)
        return ret

    def run(self, *cmd: str, env: Dict[str, str] | None = None) -> str | None:
        """
        Run a command inside the container and return the output.

        Args:
            cmd: The arguments to pass as command
            env: Environment variables to set

        Returns:
            Output of the executed command

        Raises:
            ShellException: If the command returns non-zero exit code and raise_on_non_zero is False
        """
        return self.__exec(*cmd, environment=env).decode() or None

    def stream(self, *cmd: str, env: Dict[str, str] | None = None) -> Generator[str, Any, None]:
        """
        Run a command in the container and stream the output.

        Args:
            cmd: The arguments to pass as command
            env: Environment variables to set

        Returns:
            Output stream of the executed command

        Raises:
            ShellException: If the command returns non-zero exit code and raise_on_non_zero is False
        """
        for line in self.__exec(*cmd, stream=True, environment=env):
            yield line.decode()

    def _stop_container(self) -> None:
        """Stop the container."""
        if self.__container.status == "running":
            self.logger.info("Shutting down the container")
            self.__container.stop()

    def __del__(self) -> None:
        self._stop_container()
