import os
import shutil
import tempfile
from pathlib import Path

import pytest

from orchestr8.directory_tracker import DirectoryTracker
from orchestr8.shell import Shell


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)


@pytest.fixture
def tracker_instance(temp_directory):
    """Create a DirectoryTracker instance in a temp directory with git initialized."""
    # Ensure git is installed and available
    try:
        Shell().run("git", "version")
    except Exception:
        pytest.skip("Git is not installed")

    # Create some test files
    test_file = temp_directory / "test.txt"
    test_file.write_text("Test content")

    # Create and return the tracker
    tracker = DirectoryTracker(path=temp_directory)
    return tracker


def test_directory_tracker_initialization(temp_directory):
    """Test DirectoryTracker initialization."""
    tracker = DirectoryTracker(path=temp_directory)

    # Verify tracking is initialized
    assert tracker.is_tracking
    assert (temp_directory / ".git").is_dir()


def test_directory_tracker_initialization_errors():
    """Test error cases during DirectoryTracker initialization."""
    # Non-existent directory
    with pytest.raises(Exception, match="Directory"):
        DirectoryTracker(path="/path/to/non/existent/directory")

    # No git installed - this might be hard to test reliably,
    # so we'll skip comprehensive testing of this case
    if shutil.which("git") is None:
        with pytest.raises(Exception, match="git command not found"):
            DirectoryTracker()


def test_commit(tracker_instance):
    """Test commit functionality."""
    # Create a new file
    new_file = tracker_instance.path / "new_file.txt"
    new_file.write_text("New content")

    # Commit changes
    tracker_instance.commit("Test commit")

    # Verify no changes after commit
    assert not tracker_instance.has_changes


def test_commit_empty(tracker_instance):
    """Test empty commit."""
    # Create an empty commit
    tracker_instance.commit("Empty commit", empty=True)

    # Verify the commit was created
    output = tracker_instance.shell.run("git", "log", "--oneline")
    assert "Empty commit" in output


def test_undo(tracker_instance):
    """Test undoing changes."""
    # Create a new file
    new_file = tracker_instance.path / "undo_test.txt"
    new_file.write_text("Content to be undone")

    # Verify file exists before undo
    assert new_file.exists()

    # Undo changes
    tracker_instance.undo()

    # Verify file is gone
    assert not new_file.exists()


def test_has_changes(tracker_instance):
    """Test detecting changes."""
    # Initially no changes
    assert not tracker_instance.has_changes

    # Create a new file
    new_file = tracker_instance.path / "changes_test.txt"
    new_file.write_text("New content")

    # Should now show changes
    assert tracker_instance.has_changes


def test_delete_tracking(tracker_instance):
    """Test deleting .git directory."""
    # Delete tracking
    tracker_instance.delete()

    # Verify tracking is removed
    assert not (tracker_instance.path / ".git").exists()
    assert not tracker_instance.is_tracking


def test_is_lfs_required(temp_directory):
    """Test Git LFS requirement detection."""
    # Create large files to trigger LFS
    large_file_path = temp_directory / "large_file.bin"

    # Create a file larger than the LFS threshold (use_lfs_after_size=5)
    with open(large_file_path, "wb") as f:
        f.write(b"0" * (6 * 1024 * 1024))  # 6MB file

    tracker = DirectoryTracker(path=temp_directory, use_lfs_after_size=5)

    # Verify LFS is required
    assert tracker.is_lfs_required


def test_raise_if_not_tracking():
    """Test raising exception when not tracking."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        tracker = DirectoryTracker(path=tmpdirname)
        tracker.delete()  # Remove .git directory

        # Should raise an exception when trying to perform tracking operations
        with pytest.raises(Exception, match="Tracking has not been enabled"):
            tracker.raise_if_not_tracking()


def test_commit_bypass_hooks(tracker_instance):
    """Test bypassing git hooks during commit."""
    # Create a new file
    new_file = tracker_instance.path / "bypass_hooks_test.txt"
    new_file.write_text("Bypass hooks content")

    # Commit with hook bypass
    tracker_instance.commit("Commit with hook bypass", bypass=True)

    # Verify the commit exists
    output = tracker_instance.shell.run("git", "log", "--oneline")
    assert "Commit with hook bypass" in output


def test_environment_info():
    """Print environment information for debugging."""
    print(f"Python Version: {os.sys.version}")
    print(f"Operating System: {os.name}")
    print(f"Platform: {os.sys.platform}")

    # Check git version
    try:
        git_version = Shell().run("git", "version")
        print(f"Git Version: {git_version}")
    except Exception as e:
        print(f"Git version check failed: {e}")
