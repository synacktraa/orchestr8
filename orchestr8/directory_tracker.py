from __future__ import annotations

import os
import shutil
from datetime import datetime
from json import dumps as json_dumps
from pathlib import Path

from .logger import Logger
from .shell import Shell

__all__ = ("DirectoryTracker",)


get_timestamp = lambda: datetime.now().strftime("%a, %b %d, %Y %I:%M %p")
"""Get the formatted current timestamp."""


def check_path_size_limit(path: Path, limit: int) -> bool:
    """
    Check if path size is above limit in MB.

    Args:
        path: Path to check
        limit: Limit in MB

    Returns:
        True if directory size above limit, else False
    """
    total_size, max_mb = 0, limit * 1024 * 1024
    for file in path.rglob("*"):
        if not file.is_file():
            continue
        total_size += file.stat().st_size
        if total_size > max_mb:
            return True
    return False


class DirectoryTracker(Logger):
    """
    A Git-based directory tracker that provides version control functionality.

    This class wraps Git commands to provide simple version control capabilities,
    including tracking changes, committing modifications, and undoing uncommitted changes.
    Supports large files through Git LFS when directory size exceeds a configurable limit.

    ```python
    # Initialize tracker for a specific directory
    tracker = DirectoryTracker(
        path="path/to/directory",
        use_lfs_after_size=200 # Use Git LFS if directory size exceeds 200MB
    )

    # Check if directory is being tracked
    print(tracker.is_tracking)

    # Check for changes
    print(tracker.has_changes)

    # Commit all changes
    tracker.commit("Updated files")

    # Undo all uncommited changes if needed
    tracker.undo()

    # Delete the .git directory
    tracker.delete()

    # Initialize tracking explicitly
    tracker.initialize()
    ```
    """

    def __init__(self, path: str | Path | None = None, *, use_lfs_after_size: int = 200) -> None:
        """
        Args:
            path: Directory path to use. If None, uses current working directory
            use_lfs_after_size: Maximum directory size in MB before enabling Git LFS

        Raises:
            Exception: If git is not found or unable to use git in the given directory
        """
        if path:
            self.__path = Path(path).expanduser().resolve().absolute()
            if not self.__path.is_dir():
                raise NotADirectoryError(f"Directory {str(self.__path)!r} doesn't exists.")
        else:
            self.__path = Path.cwd()

        if not shutil.which("git"):
            raise FileNotFoundError("git command not found. Please install it.")

        self.__shell = Shell(workdir=self.__path, raise_on_non_zero=True)
        self.__use_lfs_after_size = use_lfs_after_size
        if os.name == "nt" and "SHELL" not in os.environ:
            self._rm_dot_git_cmd = ["Remove-Item", "-Path", ".git", "-Recurse", "-Force"]
        else:
            self._rm_dot_git_cmd = ["rm", "-rf", ".git"]

        self.initialize()

    @property
    def path(self) -> Path:
        """The directory path."""
        return self.__path

    @property
    def shell(self) -> Shell:
        """The shell instance."""
        return self.__shell

    @property
    def is_tracking(self) -> bool:
        """
        Check if git tracking is enabled for the directory.

        Returns:
            True if the directory is being tracked (has .git directory), False otherwise
        """
        return (self.__path / ".git").is_dir()

    @property
    def has_changes(self) -> bool:
        """
        Check if there are any uncommitted changes in the tracked directory.

        Returns:
            True if there are uncommitted changes, False otherwise

        Raises:
            LookupError: If `.git` directory is not found
        """
        self.raise_if_not_tracking()
        self.logger.info("Checking for uncommitted changes")
        return bool(self.__shell.run("git", "status", "--porcelain"))

    @property
    def is_lfs_required(self) -> bool:
        """
        Check if the directory requires Git LFS.

        Returns:
            True if the directory size exceeds the configured limit, False otherwise
        """
        return check_path_size_limit(self.__path, self.__use_lfs_after_size)

    @property
    def is_using_lfs(self) -> bool:
        """
        Check if the repository is using Git LFS.

        Returns:
            True if Git LFS is configured and initialized, False otherwise

        Raises:
            LookupError: If `.git` directory is not found
        """
        self.raise_if_not_tracking()
        return (self.__path / ".git" / "lfs").is_dir()

    def raise_if_not_tracking(self) -> None:
        """
        Raise LookUpError if the directory is not being tracked.
        """
        if not self.is_tracking:
            raise LookupError("Tracking has not been enabled.")

    def initialize(self) -> None:
        """
        Initialize tracking directory changes.
        """
        if self.is_tracking and self.has_changes:
            self.logger.warning("Detected uncommitted changes. Make sure to commit them.")

        commit = False
        if not self.is_tracking:
            self.logger.info("Initializing git repository")
            self.__shell.run("git", "init")
            commit = True
        if self.is_lfs_required and not self.is_using_lfs:
            self.logger.info("Installing Git LFS")
            self.__shell.run("git", "lfs", "install")
            commit = True
        if commit:
            self.commit("tracker init", empty=True, bypass=True)

    def commit(self, __message: str, *, empty: bool = False, bypass: bool = False) -> None:
        """
        Commit all changes made to the tracked directory.

        Args:
            __message: The commit message
            empty: If True, create a commit even if there are no changes
            bypass: If True, bypass pre-commit and commit-msg hooks

        Raises:
            LookupError: If `.git` directory is not found
        """
        self.raise_if_not_tracking()

        self.logger.info("Staging all changes")
        self.__shell.run("git", "add", ".")

        commit_args = ["-m", json_dumps(f"[{get_timestamp()}] {__message}")]
        if empty:
            commit_args.append("--allow-empty")
            self.logger.info("Creating an empty commit")
        else:
            self.logger.info("Persisting uncommitted changes")
        if bypass:
            commit_args.append("--no-verify")
        self.__shell.run("git", "commit", *commit_args)

    def undo(self) -> None:
        """
        Undo all uncommitted changes in the tracked directory.

        This operation:
        1. Removes untracked files and directories
        2. Resets all tracked files to their last committed state

        Raises:
            LookupError: If `.git` directory is not found
        """
        self.raise_if_not_tracking()
        self.logger.info("Removing untracked files and directories")
        self.__shell.run("git", "clean", "-fd")
        self.logger.info("Resetting all tracked files to their last committed state")
        self.__shell.run("git", "reset", "--hard", "HEAD")

    def delete(self, commit: bool = True) -> None:
        """
        Delete the .git directory.

        Args:
            commit: Whether to commit all changes before deleting

        Raises:
            LookupError: If `.git` directory is not found
        """
        if commit and self.has_changes:
            self.commit("tracker delete")

        self.logger.info("Deleting .git directory")
        if self.is_tracking:
            self.__shell.run(*self._rm_dot_git_cmd)
