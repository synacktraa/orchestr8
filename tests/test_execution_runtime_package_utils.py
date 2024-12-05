import ast
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from orchestr8.execution_runtime.package_utils import (
    extract_module_names,
    generate_requirements,
    get_module_mapped_packages,
    get_package_release_info,
    get_stdlib_modules,
)


def create_temp_script(content: str) -> Path:
    """Create a temporary Python script with given content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        temp_file.write(content)
        temp_file.flush()
    return Path(temp_file.name)


class TestPackageUtils:
    def test_get_stdlib_modules(self):
        """Verify standard library modules are correctly retrieved."""
        stdlib_modules = get_stdlib_modules()
        assert isinstance(stdlib_modules, frozenset)
        assert all(isinstance(module, str) for module in stdlib_modules)
        assert "os" in stdlib_modules
        assert "sys" in stdlib_modules

    def test_get_module_mapped_packages(self):
        """Test module to package mapping retrieval."""
        module_map = get_module_mapped_packages()
        assert isinstance(module_map, dict)

        # Verify nested dictionary structure
        for module, packages in module_map.items():
            assert isinstance(module, str)
            assert isinstance(packages, dict)
            for pkg_name, version in packages.items():
                assert isinstance(pkg_name, str)
                assert isinstance(version, str)

    @patch("urllib.request.urlopen")
    def test_get_package_release_info_success(self, mock_urlopen):
        """Test successful package release information retrieval."""
        mock_response = {"releases": {"1.0.0": [], "1.1.0": [], "2.0.0": []}, "info": {"version": "2.0.0"}}

        mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(mock_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value.status = 200

        result = get_package_release_info("test-package")

        assert result == {"ids": ["1.0.0", "1.1.0", "2.0.0"], "latest": "2.0.0"}

    @patch("urllib.request.urlopen")
    def test_get_package_release_info_not_found(self, mock_urlopen):
        """Verify handling of non-existent package."""
        from urllib.error import HTTPError

        mock_urlopen.return_value.__enter__.side_effect = HTTPError(
            url="https://pypi.python.org/pypi/nonexistent-package/json", code=404, msg="Not Found", hdrs=None, fp=None
        )
        with pytest.raises(LookupError, match="Package 'nonexistent-package' not found."):
            get_package_release_info("nonexistent-package")

    def test_extract_module_names_basic_script(self):
        """Test extracting module names from a simple script."""
        script_content = """
import os
import sys
from math import sin
from datetime import datetime
"""
        temp_script = create_temp_script(script_content)

        try:
            modules = extract_module_names(temp_script)
            assert set(modules) == {"os", "sys", "math", "datetime"}
        finally:
            temp_script.unlink()

    def test_extract_module_names_conditional_imports(self):
        """Test extracting module names with conditional imports."""
        script_content = """
import sys
try:
    import numpy
except ImportError:
    pass

if sys.version_info >= (3, 8):
    import pandas
else:
    import csv
"""
        temp_script = create_temp_script(script_content)

        try:
            modules = extract_module_names(temp_script)
            assert set(modules) == {"numpy", "sys", "pandas", "csv"}
        finally:
            temp_script.unlink()

    def test_extract_module_names_ast_input(self):
        """Test extracting module names from an AST module."""
        script_ast = ast.parse("""
import requests
from urllib import parse
""")

        modules = extract_module_names(script_ast)
        assert set(modules) == {"requests", "urllib"}

    def test_extract_module_names_file_not_found(self):
        """Verify error handling for non-existent file."""
        with pytest.raises(FileNotFoundError):
            extract_module_names(Path("/path/to/nonexistent/script.py"))

    @patch("orchestr8.execution_runtime.package_utils.get_stdlib_modules")
    @patch("orchestr8.execution_runtime.package_utils.get_module_mapped_packages")
    @patch("orchestr8.execution_runtime.package_utils.get_package_release_info")
    def test_generate_requirements_basic(self, mock_release_info, mock_module_packages, mock_stdlib_modules):
        """Test generating requirements with mocked dependencies."""
        mock_stdlib_modules.return_value = frozenset(["os", "sys"])
        mock_module_packages.return_value = {"pandas": {"pandas": "2.0.0"}, "numpy": {"numpy": "1.24.0"}}

        def mock_release_side_effect(package_name):
            release_map = {
                "pandas": {"ids": ["2.0.0"], "latest": "2.0.0"},
                "numpy": {"ids": ["1.24.0"], "latest": "1.24.0"},
            }
            return release_map.get(package_name, {"ids": [], "latest": None})

        mock_release_info.side_effect = mock_release_side_effect

        requirements = generate_requirements(["pandas", "numpy"])
        assert set(requirements) == {"pandas==2.0.0", "numpy==1.24.0"}

    def test_generate_requirements_with_overrides(self):
        """Test generating requirements with dependency overrides."""
        dependency_overrides = {"yaml": {"package_name": "PyYAML", "specifiers": [{"version": "6.0", "op": "=="}]}}

        with patch("orchestr8.execution_runtime.package_utils.get_package_release_info") as mock_release_info:
            mock_release_info.return_value = {"ids": ["5.4", "6.0", "6.1"], "latest": "6.1"}

            requirements = generate_requirements(["yaml"], dependency_overrides)
            assert requirements == ["PyYAML==6.0"]

    def test_generate_requirements_invalid_version(self):
        """Test generating requirements with an invalid version."""
        dependency_overrides = {"yaml": {"package_name": "PyYAML", "specifiers": [{"version": "999.0", "op": "=="}]}}

        with patch("orchestr8.execution_runtime.package_utils.get_package_release_info") as mock_release_info:
            mock_release_info.return_value = {"ids": ["5.4", "6.0", "6.1"], "latest": "6.1"}

            with pytest.raises(ValueError, match="Versions \\['999.0'\\] mentioned in specifiers not found"):
                generate_requirements(["yaml"], dependency_overrides)

    def test_generate_requirements_stdlib_exclusion(self):
        """Verify standard library modules are excluded from requirements."""
        with patch("orchestr8.execution_runtime.package_utils.get_stdlib_modules") as mock_stdlib:
            mock_stdlib.return_value = frozenset(["os", "sys", "json"])

            requirements = generate_requirements(["os", "sys", "json"])
            assert len(requirements) == 0


@pytest.mark.parametrize("python_version", ["3.8", "3.9", "3.10", "3.11", "3.12"])
def test_python_version_compatibility(python_version):
    """Ensure compatibility with specified Python versions."""
    current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    current_version_matches_tested = current_version == python_version

    if current_version_matches_tested:
        assert sys.version_info[:2] == tuple(map(int, python_version.split(".")))
        stdlib_modules = get_stdlib_modules()
        assert len(stdlib_modules) > 0
