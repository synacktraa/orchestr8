from __future__ import annotations

import ast
import json
from collections import defaultdict
from importlib.metadata import distributions
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Literal, Set

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from typing_extensions import NotRequired, TypedDict


class ReleaseInfo(TypedDict):
    """Release information"""

    ids: List[str]
    latest: str


class Specifier(TypedDict):
    """
    Version specifier.

    Represents a package version specifier with an operator and version string.
    """

    version: str
    op: Literal["==", ">=", "<=", ">", "<", "~=", "===", "!="]


class Dependency(TypedDict):
    """Dependency specification with package name and version requirements."""

    package_name: NotRequired[str]
    specifiers: NotRequired[List[Specifier]]


def get_stdlib_modules() -> FrozenSet[str]:
    """
    Get a set of all Python standard library module names.

    Returns:
        Set of standard library module names read from stdlib.txt
    """
    return frozenset(line.strip() for line in (Path(__file__).parent / "stdlib.txt").open().readlines())


def get_module_mapped_packages() -> Dict[str, Dict[str, str]]:
    """
    Map Python module names to their corresponding package information.

    Creates a mapping of module names to dictionaries containing package names
    and their versions based on installed distributions.

    Returns:
        Dictionary mapping module names to {package_name: version} dictionaries
    """
    module_to_packages = defaultdict(dict[str, str])  # type: ignore[var-annotated]
    for dist in distributions():
        try:
            if not (
                pkg_name := getattr(
                    dist,
                    "name",
                    dist.metadata.get("Name", ""),  # type: ignore[attr-defined]
                )
            ):
                continue

            top_level_text = dist.read_text("top_level.txt")
            if top_level_text:
                for mod_name in top_level_text.split():
                    module_to_packages[mod_name][pkg_name] = (
                        getattr(dist, "version", None) or dist.metadata.get("Version", "") or ""  # type: ignore[attr-defined]
                    )
        except Exception:  # noqa: S112
            # Silently skip distributions that cause issues
            continue

    return dict(module_to_packages)


def get_package_release_info(__name: str, resolver_url: str | None = None, **urllib_request_kwargs: Any) -> ReleaseInfo:
    """
    Fetch package release information from PyPI or custom package index.

    Args:
        __name: Name of the package to look up
        resolver_url: Custom package index URL. Defaults to PyPI
        urllib_request_kwargs: Additional keyword arguments for urllib.request.Request

    Returns:
        Dictionary containing 'ids' (list of versions) and 'latest' (latest version)

    Raises:
        LookupError: If the package is not found
        ConnectionError: If there are network issues or invalid responses
    """
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    base_url = (resolver_url or "https://pypi.python.org/pypi/").rstrip("/")
    url = f"{base_url}/{__name}/json"
    try:
        with urlopen(Request(url, **urllib_request_kwargs)) as response:  # noqa: S310
            if response.status != 200:
                raise ConnectionError(
                    f"An error occurred requesting {base_url!r} for package {__name!r}. "
                    f"Status code: {response.status}"
                )

            response_data = response.read().decode("utf-8")
            json_data: Dict[str, dict] = json.loads(response_data)

            return {
                "ids": list(json_data.get("releases", {}).keys()),
                "latest": json_data.get("info", {}).get("version"),  # type: ignore[typeddict-item]
            }

    except HTTPError as e:
        if e.code == 404:
            raise LookupError(f"Package {__name!r} not found.") from e
        raise ConnectionError(
            f"An error occurred requesting {base_url!r} for package {__name!r}. "
            f"Status code: {e.code}, Response: {e.read().decode('utf-8')}"
        ) from e

    except URLError as e:
        raise ConnectionError(f"Failed to connect to {base_url!r} for package {__name!r}. " f"Error: {e!s}") from e


def extract_module_names(script: Path | ast.Module) -> List[str]:  # noqa: C901
    """
    Extract imported module names from a Python script or AST Module.

    Analyzes Python source code to find all imported module names, including those within
    conditional statements (if/else) and try/except blocks. For 'import' statements,
    only the root module name is extracted (e.g., 'pandas' from 'pandas.DataFrame').
    For 'from' imports, the module being imported from is extracted.


    ```python
    script = Path('example.py')  # Contains: import pandas as pd; from numpy import array
    extract_module_names(script)
    # output: ['pandas', 'numpy']

    Args:
        script: Either a Path to a Python file or an ast.Module object

    Returns:
        List of unique module names found in the script

    Raises:
        FileNotFoundError: If the script path does not exist
    """

    class ModuleExtractor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.module_names: Set[str] = set()

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                self.module_names.add(alias.name.split(".")[0])

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.level == 0 and node.module:
                self.module_names.add(node.module)

        def visit_If(self, node: ast.If) -> None:
            self.visit(node.test)

            for stmt in node.body:
                self.visit(stmt)

            if node.orelse:
                for stmt in node.orelse:
                    self.visit(stmt)

        def visit_Try(self, node: ast.Try) -> None:
            for stmt in node.body:
                self.visit(stmt)

            for handler in node.handlers:
                for stmt in handler.body:
                    self.visit(stmt)

            if node.orelse:
                for stmt in node.orelse:
                    self.visit(stmt)

            if node.finalbody:
                for stmt in node.finalbody:
                    self.visit(stmt)

    if isinstance(script, Path):
        if not script.is_file():
            raise FileNotFoundError(f"Script {script!r} not found.")
        script = ast.parse(script.read_bytes())

    extractor = ModuleExtractor()
    extractor.visit(script)
    return list(extractor.module_names)


def generate_requirements(
    module_names: List[str], dependency_overrides: Dict[str, Dependency] | None = None
) -> List[str]:
    """
    Generate a list of Python package requirements from module names.

    For extracting module names from a Python script, use:

    ```python
    from orchestr8.runtime.utils import extract_module_names
    module_names = extract_module_names("/path/to/script.py")
    ```

    The function follows a systematic approach to resolving package dependencies:

    First, standard library modules are automatically excluded from the processing.
    The remaining modules are then searched among globally installed packages.
    When a module is found in installed packages, its package name and version are used.

    If a module is not installed locally, the function searches the PyPI package index.
    When a package is found on PyPI, its latest version is utilized.
    If no package can be found, the function raises an error.

    The function provides flexibility through the `dependency_overrides` parameter.
    This is particularly useful in scenarios where:
    - The package name differs from the module name
    - Custom version specifications are required

    A prime example is the `yaml` module, which corresponds to the `PyYAML` package.
    Through dependency overrides, you can specify custom package names or version constraints.

    The function performs comprehensive validation:
    - Checks if specified versions exist in package releases
    - Validates version specifiers against available package versions
    - Ensures precise and correct dependency specification

    ```python
    generate_requirements(['pandas', 'numpy'])
    # output: ['pandas==2.0.0', 'numpy==1.24.0']

    overrides = {
        'yaml': {
            'package_name': 'PyYAML',
            'specifiers': [{'version': '6.0', 'op': '=='}]
        }
    }
    generate_requirements(['yaml'], overrides)
    # output: ['PyYAML==6.0']
    ```

    Args:
        module_names: List of Python module names to process
        dependency_overrides: Dependency overrides for specific modules

    Returns:
        List of requirement strings (e.g., ["package==1.0.0"])

    Raises:
        ValueError: If specified package name or versions in overrides are invalid or not found
        LookupError: If a package cannot be located on PyPI
        ConnectionError: If network-related issues occur when fetching package information
    """
    requirements = []
    installables = set(module_names) - get_stdlib_modules()
    for mod_name, dep in (dependency_overrides or {}).items():
        if mod_name in installables:
            installables.remove(mod_name)
        pkg_name = dep.get("package_name") or mod_name
        release_info = get_package_release_info(pkg_name)
        if specifiers := dep.get("specifiers"):
            spec_versions = {spec["version"] for spec in specifiers}
            specifier_set = SpecifierSet(",".join(f"{spec['op']}{spec['version']}" for spec in specifiers))
            available_versions = release_info["ids"]
            not_found = list(spec_versions.difference(available_versions))
            if not_found:
                raise ValueError(f"Versions {not_found!r} mentioned in specifiers not found in {pkg_name!r} releases.")

            if not any(Version(v) in specifier_set for v in available_versions):
                raise ValueError(
                    f"Specifiers specified for package {pkg_name!r} are invalid. "
                    f"Avaiable versions: {available_versions!r}"
                )
            requirements.append(f"{pkg_name}{specifier_set!s}")
        else:
            requirements.append(f"{pkg_name}=={release_info['latest']}")

    mod_mapped_pkgs = get_module_mapped_packages()
    for mod_name in installables:
        if local_pkgs := mod_mapped_pkgs.get(mod_name):
            # Some modules have more than one package, so we'll include all available ones.
            for pkg_name, version in local_pkgs.items():
                release_info = get_package_release_info(pkg_name)
                if version in release_info["ids"]:
                    requirements.append(f"{pkg_name}=={version}")
        else:
            # We use the module name as the package name
            release_info = get_package_release_info(mod_name)
            requirements.append(f"{mod_name}=={release_info['latest']}")

    return requirements
