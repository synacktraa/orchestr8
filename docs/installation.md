# Installing Orchestr8

Orchestr8 requires Python 3.9 or greater, and is tested on all major Python versions and operating systems.

=== "pip"

    ```bash
    pip install orchestr8
    ```

=== "uv"

    ```bash
    uv pip install orchestr8
    ```

Upgrade to the latest released version at any time:

=== "pip"

    ```bash
    pip install -U orchestr8
    ```

=== "uv"

    ```bash
    uv pip install -U orchestr8
    ```

## Optional dependencies

Some components has their own dependencies that are not installed by default.
If you wish to use all the components, you can install it through:

=== "pip"

    ```bash
    pip install orchestr8[all]
    ```

=== "uv"

    ```bash
    uv pip install orchestr8[all]
    ```

If you wish to use particular components, you can install them by providing their module names as extra:

For the `adapter` module:

=== "pip"

    ```bash
    pip install orchestr8[adapter]
    ```

=== "uv"

    ```bash
    uv pip install orchestr8[adapter]
    ```

For the `execution-runtime` module:

=== "pip"

    ```bash
    pip install orchestr8[execution-runtime]
    ```

=== "uv"

    ```bash
    uv pip install orchestr8[execution-runtime]
    ```

For the `sandbox-client` module:

=== "pip"

    ```bash
    pip install orchestr8[sandbox-client]
    ```

=== "uv"

    ```bash
    uv pip install orchestr8[sandbox-client]
    ```

For the `shell` module:

=== "pip"

    ```bash
    pip install orchestr8[shell]
    ```

=== "uv"

    ```bash
    uv pip install orchestr8[shell]
    ```

## Third party tool dependencies

Few components require third party tool dependencies to work. These tools must be installed separately.

- `DirectoryTracker` requires `git` for version control, you can download it from [here](https://git-scm.com/downloads)
- `OAuthFlow` requires `mkcert` for setting up local redirect server, refer [here](https://github.com/FiloSottile/mkcert?tab=readme-ov-file#installation) for installation instructions
- `SandboxClient`, `IsolatedShell` and `IsolatedRuntime` depends on `docker`, refer [here](https://docs.docker.com/engine/install/) for installation instructions
