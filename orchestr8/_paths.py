from os import environ as env
from pathlib import Path

DOT_ORCHESTR8 = Path.home() / ".orchestr8"
DOT_ORCHESTR8.mkdir(exist_ok=True)
MKCERT_LOCALHOST_SSL_CERT_FILE = DOT_ORCHESTR8 / "mkcert-localhost.pem"
"""The certificate file for localhost."""
MKCERT_LOCALHOST_SSL_PKEY_FILE = DOT_ORCHESTR8 / "mkcert-localhost-key.pem"
"""The private key file for localhost."""

RUNTIME_DIR = DOT_ORCHESTR8 / "runtime"
"""The directory for storing created projects and volumes."""

if (runtime_dir := env.get("ORCHESTR8_RUNTIME_DIR")) is not None:
    RUNTIME_DIR = Path(runtime_dir)

RUNTIME_DIR.mkdir(exist_ok=True)

RUNTIME_PROJECTS_DIR = RUNTIME_DIR / "projects"
"""The directory to store projects."""
RUNTIME_PROJECTS_DIR.mkdir(exist_ok=True)

ISOLATED_RUNTIME_VENVS_VOLUME_DIR = RUNTIME_DIR / "venvs-volume"
"""
The volume directory to store virtual environements for projects for
each python version. For example, if the python version is 3.10, the
venvs directory will be at:
    ~/.orchestr8/runtime/venvs-volume/3.10/
"""
ISOLATED_RUNTIME_VENVS_VOLUME_DIR.mkdir(exist_ok=True)
