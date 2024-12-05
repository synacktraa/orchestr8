from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tarfile import open as tar_open
from typing import TYPE_CHECKING, Any, Dict, Literal, TypedDict

if TYPE_CHECKING:
    from docker.models.containers import Container  # type: ignore[import-untyped]

from .logger import Logger

__all__ = ("SandboxClient",)


class VolumeValue(TypedDict):
    bind: str
    mode: str


class SandboxClient(Logger):
    """
    A wrapper around docker client for building and running containers.

    ```python
    client = SandboxClient()

    # Check if image build exists locally
    client.image_exists("ubuntu:22.04", where="local")

    # Check if image is available in registry
    client.image_exists("ubuntu:22.04", where="registry")

    # Pull image from Docker Hub
    client.build_image("ubuntu:22.04")

    # Build image from Dockerfile
    client.build_image("my-image:my-tag", dockerfile=Path("/path/to/Dockerfile"))

    # Run container
    container = client.run_container("ubuntu:22.04", detach=True)
    ```
    """

    def __init__(self, **config: Any) -> None:
        """
        Initialize the client.

        Args:
            config: Docker client configuration
        """
        from docker.errors import DockerException  # type: ignore[import-untyped]

        try:
            import docker  # type: ignore[import-untyped]

            self._instance = docker.DockerClient(**config) if config else docker.from_env()
        except DockerException as e:
            if "The system cannot find the file specified." in str(e):
                raise DockerException("Unable to connect. Make sure docker service is running.") from e
            raise

    def image_exists(self, image: str, *, where: Literal["local", "registry"] = "local") -> bool:
        """
        Check if an image exists.

        Args:
            image: The image name
            where: The source to check. Defaults to "local"

        Returns:
            True if the image exists, False otherwise
        """
        from docker.errors import NotFound

        try:
            if where == "local":  # noqa: SIM108
                _ = self._instance.images.get(image)
            else:
                _ = self._instance.images.get_registry_data(image)
            return True  # noqa: TRY300
        except NotFound:
            return False

    def build_image(self, image: str, *, dockerfile: Path | BytesIO | None = None) -> None:
        """
        Build an image from pulling it from the registry or building it from a dockerfile.

        Args:
            image: The image name
            dockerfile: The dockerfile to build. Defaults to None

        Raises:
            Exception: If the image not found in the registry
        """
        if self.image_exists(image, where="local"):
            self.logger.info(f"Skipping build process. Image {image!r} already exists.")
            return

        if not dockerfile:
            if not self.image_exists(image, where="registry"):
                raise Exception(f"Image {image!r} not found on docker hub.")

            self.logger.info(f"Pulling image {image!r} from registry")
            _ = self._instance.images.pull(*(s if len(s := image.split(":")) == 2 else s[:1]))
            return

        if isinstance(dockerfile, BytesIO):  # noqa: SIM108
            fileobj = dockerfile
        else:
            fileobj = BytesIO(dockerfile.read_bytes())

        self.logger.info(f"Building image {image!r} from dockerfile")
        for line in self._instance.api.build(fileobj=fileobj, tag=image, rm=True, quiet=False, decode=True):
            if (log := line.get("stream")) is not None:
                self.logger.info(log.strip())

    def run_container(  # type: ignore[no-any-unimported]
        self, image: str, *, volumes: Dict[Path, VolumeValue] | None = None, **run_kwargs: Any
    ) -> Container:
        """
        Run a container from a locally available image build.
        Use `.build_image` before requesting for container instance.

        Args:
            image: The image to create container instance from
            volumes: Volumes to mount inside the container. Defaults to None
            run_kwargs: Keyword arguments to pass to `docker run`

        Returns:
            The container instance

        Raises:
            Exception: If the image build is not found
        """

        if not self.image_exists(image, where="local"):
            raise Exception(f"Build not found for image {image!r}.")

        if volumes:
            run_kwargs["volumes"] = {}
            for path, vv in volumes.items():
                run_kwargs["volumes"][str(path)] = vv

        self.logger.info(f"Starting up container from image {image!r}")
        return self._instance.containers.run(image=image, **run_kwargs)

    def copy_path_to_container(self, __id: str, *, src: str | Path, target: str | Path) -> None:
        """
        Copy a path from the local system to the container.

        Args:
            __id: Container ID
            src: Source path in the local system
            target: Target path inside the container.

        Raises:
            FileNotFoundError: If the source path does not exist
        """
        path = Path(src)
        if not path.exists():
            raise FileNotFoundError(f"Source path not found: {path!s}")

        self.logger.info(f"Copying {str(path)!r} to {str(target)!r} inside container(sid={__id[:12]!r})")
        with BytesIO() as buffer, tar_open(fileobj=buffer, mode="w") as tar:
            tar.add(path, arcname=path.name)
            buffer.seek(0)

            self._instance.api.put_archive(__id, path=Path(target).as_posix(), data=buffer)
