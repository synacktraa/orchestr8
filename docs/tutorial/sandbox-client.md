SandboxClient is a component that wraps docker client to provide a simple interface for pulling/building images, running containers and copying files from host to container.

> Make sure you have `docker` installed on your machine, refer [here](https://docs.docker.com/engine/install/) for installation instructions.

```python
sandbox_client = o8.SandboxClient()

# Pulling an image
# If you don't pass the dockerfile, it will try to pull the image from docker hub
sandbox_client.build_image("ubuntu:latest")

# Building an image from a dockerfile
sandbox_client.build_image("my-image:my-tag", dockerfile="/path/to/Dockerfile")

# Running a container
container = sandbox_client.run_container("ubuntu:latest", detach=True, remove=True)

# Copying files from host to container
sandbox_client.copy_path_to_container(container.id, "/path/on/host", "/path/on/container")
```
