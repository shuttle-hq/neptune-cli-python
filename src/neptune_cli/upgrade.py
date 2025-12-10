import os
from pathlib import Path
import platform
import stat
import sys
import tempfile

from loguru import logger as log
import requests

from neptune_cli.version import (
    UpdateInfo,
    is_running_as_binary,
)


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
    """Spawn a detached process to clean up the old exe after exit.
    
    Uses a limited retry count to avoid infinite loops when the file
    stays locked (e.g., when running as an MCP server in Cursor).
    """
    import subprocess

    # Limited retries (60 attempts * 2 sec = 2 minutes max)
    # After that, give up - the .old file isn't critical
    cleanup_script = f'''@echo off
setlocal
set count=0
:retry
if %count% geq 60 goto cleanup
set /a count+=1
timeout /t 2 /nobreak >nul 2>nul
del "{old_exe}" 2>nul
if exist "{old_exe}" goto retry
:cleanup
del "%~f0" 2>nul
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".bat", delete=False) as f:
        f.write(cleanup_script)
        bat_path = f.name

    # Use CREATE_NO_WINDOW to prevent any visible terminal
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0  # SW_HIDE

    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
        startupinfo=startupinfo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
