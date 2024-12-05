Shell component is prettry self-explanatory. It allows you to run commands in host machine or inside a container.

There are two types of shell:

- `Shell`: This shell is used to run commands in host machine.
- `IsolatedShell`: This shell is used to run commands inside a container.

## Using Shell (host-based)

```python
import orchestr8 as o8

# Initialize the shell
shell = o8.Shell(workdir="/path/to/directory")

# Run command
print(shell.run("echo", "Hello from shell!"))

# Stream run command
for line in shell.stream("ls", "-l"):
    print(line)
```

## Using IsolatedShell

> Isolation requires docker, refer [here](https://docs.docker.com/engine/install/) for installation instructions

```python
import orchestr8 as o8

# Create a detached container
container = o8.SandboxClient().run_container(
    "ubuntu:22.04", detach=True, remove=True
)

# Initialize the shell
shell = o8.IsolatedShell(
    container=container, workdir="/path/to/directory"
)

# Run command
print(shell.run("echo", "Hello from shell!"))

# Stream run command
for line in shell.stream("ls", "-l"):
    print(line)
```
