import io
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from docker.errors import NotFound
from loguru import logger

from orchestr8.sandbox_client import SandboxClient


@pytest.fixture
def mock_docker_client():
    """Fixture to create a mocked Docker client for testing."""
    with patch("docker.from_env") as mock_from_env, patch("docker.DockerClient") as mock_docker_client:
        mock_client_instance = MagicMock()
        mock_from_env.return_value = mock_client_instance
        mock_docker_client.return_value = mock_client_instance
        yield mock_client_instance


@pytest.fixture
def caplog(caplog):
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


def test_sandbox_client_initialization_default(mock_docker_client):
    """Test default initialization of SandboxClient."""
    client = SandboxClient()
    assert client._instance == mock_docker_client


def test_sandbox_client_initialization_with_config(mock_docker_client):
    """Test initialization of SandboxClient with custom configuration."""
    config = {"timeout": 60, "version": "1.41"}
    client = SandboxClient(**config)
    assert client._instance == mock_docker_client


def test_image_exists_local_success(mock_docker_client):
    """Test image_exists method for a local image."""
    mock_docker_client.images.get.return_value = MagicMock()

    client = SandboxClient()
    result = client.image_exists("test-image")

    assert result is True
    mock_docker_client.images.get.assert_called_once_with("test-image")


def test_image_exists_registry_success(mock_docker_client):
    """Test image_exists method for a registry image."""
    mock_docker_client.images.get_registry_data.return_value = MagicMock()

    client = SandboxClient()
    result = client.image_exists("test-image", where="registry")

    assert result is True
    mock_docker_client.images.get_registry_data.assert_called_once_with("test-image")


def test_image_exists_not_found(mock_docker_client):
    """Test image_exists method when image is not found."""
    mock_docker_client.images.get.side_effect = NotFound("Image not found")

    client = SandboxClient()
    result = client.image_exists("non-existent-image")

    assert result is False


def test_build_image_local_image_exists(mock_docker_client, caplog):
    """Test build_image when image already exists locally."""
    mock_docker_client.images.get.return_value = MagicMock()

    client = SandboxClient()
    client.build_image("existing-image")

    assert "Skipping build process" in caplog.text


def test_build_image_pull_from_registry(mock_docker_client):
    """Test build_image pulling an image from registry."""
    mock_docker_client.images.get.side_effect = NotFound("Not local")
    mock_docker_client.images.pull.return_value = MagicMock()

    client = SandboxClient()
    client.build_image("registry-image:latest")

    mock_docker_client.images.pull.assert_called_once()


def test_build_image_from_dockerfile(mock_docker_client, caplog):
    """Test build_image with a dockerfile."""
    mock_docker_client.images.get.side_effect = NotFound("Not local")
    mock_docker_client.api.build.return_value = [{"stream": "Building..."}]

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as dockerfile:
        dockerfile.write("FROM python:3.9")
        dockerfile.close()

        client = SandboxClient()
        client.build_image("custom-image", dockerfile=Path(dockerfile.name))

    assert "Building..." in caplog.text
    os.unlink(dockerfile.name)


def test_build_image_from_bytesio(mock_docker_client, caplog):
    """Test build_image with a BytesIO dockerfile."""
    mock_docker_client.images.get.side_effect = NotFound("Not local")
    mock_docker_client.api.build.return_value = [{"stream": "Building..."}]

    dockerfile_bytes = io.BytesIO(b"FROM python:3.9\n")

    client = SandboxClient()
    client.build_image("custom-image", dockerfile=dockerfile_bytes)

    assert "Building..." in caplog.text


def test_run_container_image_not_found(mock_docker_client):
    """Test run_container when image is not available locally."""
    mock_docker_client.images.get.side_effect = NotFound("Image not found")

    client = SandboxClient()
    with pytest.raises(Exception, match="Build not found for image 'non-existent-image'."):
        client.run_container("non-existent-image")


def test_run_container_with_volumes(mock_docker_client):
    """Test run_container with volume mounting."""
    mock_docker_client.images.get.return_value = MagicMock()
    mock_docker_client.containers.run.return_value = MagicMock()

    volumes = {Path("/host/path"): {"bind": "/container/path", "mode": "rw"}}

    client = SandboxClient()
    container = client.run_container("test-image", volumes=volumes)

    assert container is not None
    mock_docker_client.containers.run.assert_called_once_with(
        image="test-image", volumes={str(Path("/host/path")): {"bind": "/container/path", "mode": "rw"}}
    )


def test_run_container_additional_kwargs(mock_docker_client):
    """Test run_container with additional Docker run kwargs."""
    mock_docker_client.images.get.return_value = MagicMock()
    mock_docker_client.containers.run.return_value = MagicMock()

    client = SandboxClient()
    container = client.run_container("test-image", command="echo hello", detach=True)  # noqa: F841

    mock_docker_client.containers.run.assert_called_once_with(image="test-image", command="echo hello", detach=True)
