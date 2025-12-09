import os
from pathlib import Path
import platform
import stat
import sys
import tempfile
import time

from loguru import logger as log
import requests

from neptune_cli.config import SETTINGS
from neptune_cli.version import (
    UpdateInfo,
    check_for_update,
    is_running_as_binary,
)


CHECK_INTERVAL = 86400  # 24 hours in seconds


def should_check_for_updates() -> bool:
    """Check if enough time has passed since last update check."""
    if SETTINGS.skip_update_check:
        return False

    if SETTINGS.last_update_check is None:
        return True

    elapsed = time.time() - SETTINGS.last_update_check
    return elapsed >= CHECK_INTERVAL


def update_last_check_timestamp() -> None:
    """Update the last update check timestamp in settings."""
    SETTINGS.last_update_check = time.time()
    SETTINGS.save_to_file()


def get_current_executable() -> Path:
    """Get the path to the currently running executable."""
    if is_running_as_binary():
        return Path(sys.executable)
    else:
        return Path(sys.argv[0]).resolve()


def download_binary(url: str, dest: Path) -> bool:
    """Download a binary from URL to destination path.

    Args:
        url: URL to download from
        dest: Destination path for the downloaded file

    Returns:
        True if download succeeded, False otherwise
    """
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        log.debug(f"Download failed: {e}")
        return False


def perform_upgrade(update_info: UpdateInfo, silent: bool = False) -> bool:
    """Perform the binary upgrade.

    Args:
        update_info: Information about the available update
        silent: If True, suppress output messages

    Returns:
        True if upgrade succeeded, False otherwise
    """
    if not is_running_as_binary():
        if not silent:
            print("Cannot upgrade: not running as a compiled binary")
        return False

    current_exe = get_current_executable()
    system = platform.system().lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        if not silent:
            print(f"Downloading neptune {update_info.latest_version}...")

        if not download_binary(update_info.download_url, tmp_path):
            if not silent:
                print("Failed to download update")
            return False

        if system != "windows":
            tmp_path.chmod(tmp_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        if system == "windows":
            success = _perform_windows_upgrade(current_exe, tmp_path, silent)
        else:
            success = _perform_unix_upgrade(current_exe, tmp_path, silent)

        if success:
            update_last_check_timestamp()
            if not silent:
                print(f"Successfully upgraded to {update_info.latest_version}")

        return success

    except Exception as e:
        if not silent:
            print(f"Upgrade failed: {e}")
        return False
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def _perform_unix_upgrade(current_exe: Path, new_binary: Path, silent: bool) -> bool:
    """Perform upgrade on Unix systems using atomic replace."""
    try:
        os.replace(new_binary, current_exe)
        return True
    except PermissionError:
        if not silent:
            print("Permission denied. Try running with sudo:")
            print("  sudo neptune upgrade")
        return False
    except Exception as e:
        if not silent:
            print(f"Failed to replace binary: {e}")
        return False


def _perform_windows_upgrade(current_exe: Path, new_binary: Path, silent: bool) -> bool:
    """Perform upgrade on Windows by renaming current exe and moving new one."""
    old_exe = current_exe.with_suffix(".exe.old")

    try:
        if old_exe.exists():
            old_exe.unlink()

        current_exe.rename(old_exe)
        new_binary.rename(current_exe)
        _spawn_windows_cleanup(old_exe)
        return True
    except PermissionError:
        if not silent:
            print("Permission denied. Try running as Administrator")
        return False
    except Exception as e:
        if not silent:
            print(f"Failed to replace binary: {e}")
        if old_exe.exists() and not current_exe.exists():
            try:
                old_exe.rename(current_exe)
            except Exception:
                pass
        return False


def _spawn_windows_cleanup(old_exe: Path) -> None:
    """Spawn a detached process to clean up the old exe after exit."""
    import subprocess

    cleanup_script = f'''
@echo off
:retry
timeout /t 1 /nobreak >nul
del "{old_exe}" 2>nul
if exist "{old_exe}" goto retry
del "%~f0"
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".bat", delete=False) as f:
        f.write(cleanup_script)
        bat_path = f.name

    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def auto_check_and_upgrade() -> None:
    """Perform automatic update check and upgrade if available.

    This runs silently and never interrupts the CLI.
    """
    if not should_check_for_updates():
        return

    if not is_running_as_binary():
        update_last_check_timestamp()
        return

    try:
        update_info = check_for_update()

        if update_info is None:
            update_last_check_timestamp()
            return

        if not update_info.update_available:
            update_last_check_timestamp()
            return

        perform_upgrade(update_info, silent=True)

    except Exception:
        pass
