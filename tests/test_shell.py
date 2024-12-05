from pathlib import Path
from unittest.mock import MagicMock

import pytest

from orchestr8.shell import IsolatedShell, Shell


class TestShell:
    def test_init_default_workdir(self):
        """Test initialization with default working directory."""
        shell = Shell()
        assert shell.workdir == Path.cwd()

    def test_init_custom_workdir(self, tmp_path):
        """Test initialization with a custom working directory."""
        shell = Shell(workdir=tmp_path)
        assert shell.workdir == tmp_path

    def test_init_invalid_workdir(self):
        """Test initialization with an invalid working directory."""
        non_existent_path = Path("/path/that/does/not/exist")
        with pytest.raises(NotADirectoryError):
            Shell(workdir=non_existent_path)

    def test_run_command_basic(self, tmp_path):
        """Test basic command execution."""
        shell = Shell(workdir=tmp_path)
        result = shell.run("echo", "'Hello, World!'")
        assert "Hello, World!" in result


class TestIsolatedShell:
    @pytest.fixture
    def mock_docker_container(self):
        """Create a mock Docker container for testing."""
        container_mock = MagicMock()
        container_mock.status = "running"
        container_mock.exec_run.return_value = (None, b"Mocked output")
        return container_mock

    def test_init_with_running_container(self, mock_docker_container):
        """Test initialization with a running container."""
        shell = IsolatedShell(container=mock_docker_container)
        assert shell.container == mock_docker_container

    def test_init_with_stopped_container(self, mock_docker_container):
        """Test initialization with a stopped container raises an exception."""
        mock_docker_container.status = "stopped"
        with pytest.raises(Exception, match="Container is not running."):
            IsolatedShell(container=mock_docker_container)

    def test_run_command_basic(self, mock_docker_container):
        """Test basic command execution in container."""
        shell = IsolatedShell(container=mock_docker_container)
        result = shell.run("test", "command")
        assert result == "Mocked output"

    def test_run_command_streaming(self, mock_docker_container):
        """Test streaming command output."""
        # Simulate streaming output

        shell = IsolatedShell(container=mock_docker_container)
        mock_docker_container.exec_run.return_value = (None, iter([b"Line 1", b"Line 2"]))
        output_stream = shell.stream(
            "stream",
            "command",
        )
        output_lines = list(output_stream)

        assert len(output_lines) == 2
        assert output_lines[0] == "Line 1"
        assert output_lines[1] == "Line 2"

    def test_stop_container(self, mock_docker_container):
        """Test stopping the container."""
        shell = IsolatedShell(container=mock_docker_container)
        shell._stop_container()
        mock_docker_container.stop.assert_called_once()
