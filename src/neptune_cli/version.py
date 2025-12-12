from dataclasses import dataclass
import platform
import sys

from packaging.version import Version
import requests


REPO = "dcodesdev/neptune-mcp"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_BASE_URL = f"https://github.com/{REPO}/releases/latest/download"
REQUEST_TIMEOUT = 5


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    download_url: str
    asset_name: str

    @property
    def update_available(self) -> bool:
        return Version(self.latest_version) > Version(self.current_version)


def get_current_version() -> str:
    """Get the current installed version of neptune-cli."""
    try:
        from importlib.metadata import version

        return version("neptune-cli")
    except Exception:
        return "0.0.0"


def get_latest_version() -> tuple[str, str] | None:
    """Fetch the latest version and download URL from GitHub releases.

    Returns:
        Tuple of (version, download_url) or None if fetch fails.
    """
    try:
        response = requests.get(
            GITHUB_API_URL,
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        response.raise_for_status()
        data = response.json()

        tag_name = data.get("tag_name", "")
        version = tag_name.lstrip("v")

        asset_name = get_platform_asset_name()
        if asset_name is None:
            return None

        download_url = f"{DOWNLOAD_BASE_URL}/{asset_name}"
        return version, download_url
    except Exception:
        return None


def get_platform_asset_name() -> str | None:
    """Get the platform-specific binary asset name.

    Returns:
        Asset name string or None if platform is unsupported.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }

    arch = arch_map.get(machine)
    if arch is None:
        return None

    if system == "linux":
        return f"neptune-linux-{arch}"
    elif system == "darwin":
        return f"neptune-macos-{arch}"
    elif system == "windows":
        return f"neptune-windows-{arch}.exe"
    else:
        return None


def check_for_update() -> UpdateInfo | None:
    """Check if an update is available.

    Returns:
        UpdateInfo if check succeeds, None if check fails.
    """
    current = get_current_version()
    latest_info = get_latest_version()

    if latest_info is None:
        return None

    latest_version, download_url = latest_info
    asset_name = get_platform_asset_name()

    if asset_name is None:
        return None

    return UpdateInfo(
        current_version=current,
        latest_version=latest_version,
        download_url=download_url,
        asset_name=asset_name,
    )


def is_running_as_binary() -> bool:
    """Check if running as a compiled binary (PyInstaller) vs Python script."""
    return getattr(sys, "frozen", False)
