"""Utility functions for the Neptune CLI."""

from __future__ import annotations

import io
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Maximum archive size (200MB)
MAX_ARCHIVE_SIZE = 200 * 1024 * 1024

# Files to always include in lint config
LINT_CONFIG_FILES = [".neptune-lint.toml", "neptune-lint.toml"]


def create_project_archive(
    root: Path,
    respect_gitignore: bool = True,
    max_size: int = MAX_ARCHIVE_SIZE,
) -> bytes:
    """Create a ZIP archive of the project directory.

    Args:
        root: Root directory to archive
        respect_gitignore: Whether to respect .gitignore patterns
        max_size: Maximum archive size in bytes

    Returns:
        ZIP archive as bytes

    Raises:
        ValueError: If archive exceeds max size
    """
    buffer = io.BytesIO()
    total_size = 0

    # Get list of files to include
    if respect_gitignore and (root / ".gitignore").exists():
        files = _get_git_tracked_files(root)
    else:
        files = _walk_directory(root)

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        included_paths: set[str] = set()

        for file_path in files:
            if not file_path.is_file():
                continue

            # Check total size
            file_size = file_path.stat().st_size
            total_size += file_size

            if total_size > max_size:
                raise ValueError(
                    f"Archive size would exceed {max_size // (1024 * 1024)}MB limit. "
                    f"Current size: {total_size} bytes"
                )

            rel_path = file_path.relative_to(root)
            zf.write(file_path, rel_path)
            included_paths.add(str(rel_path))

        # Always include lint config files if present
        for lint_file in LINT_CONFIG_FILES:
            lint_path = root / lint_file
            if lint_path.is_file() and lint_file not in included_paths:
                zf.write(lint_path, lint_file)

    return buffer.getvalue()


def _get_git_tracked_files(root: Path) -> list[Path]:
    """Get list of files tracked by git (respects .gitignore)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        files = [root / f for f in result.stdout.strip().split("\n") if f]
        return [f for f in files if f.is_file()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fall back to walking directory
        return _walk_directory(root)


def _walk_directory(root: Path, ignore_patterns: list[str] | None = None) -> list[Path]:
    """Walk directory and return list of files."""
    ignore = ignore_patterns or [
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".env",
        "target",
        "dist",
        "build",
        "*.pyc",
        ".DS_Store",
    ]

    files: list[Path] = []

    for item in root.rglob("*"):
        if item.is_file():
            # Check if any parent directory is ignored
            skip = False
            for part in item.parts:
                if any(_matches_pattern(part, p) for p in ignore):
                    skip = True
                    break

            if not skip and not any(_matches_pattern(item.name, p) for p in ignore):
                files.append(item)

    return files


def _matches_pattern(name: str, pattern: str) -> bool:
    """Check if name matches a simple glob pattern."""
    if pattern.startswith("*"):
        return name.endswith(pattern[1:])
    return name == pattern


def ai_spec_to_platform_request(ai_spec: dict, project_name: str | None = None) -> dict:
    """Convert AI service Spec format to platform PutProjectRequest format.

    The AI service returns specs with kind like "Backend"/"ETLJob",
    but the platform API expects kind "Service".

    Args:
        ai_spec: Spec dict from AI service
        project_name: Optional project name override

    Returns:
        Dict in PutProjectRequest format
    """
    # Map AI service resource kinds to platform kinds
    resource_kind_map = {
        "ObjectStorageBucket": "StorageBucket",
        # Keep these the same
        "Database": "Database",
        "StorageBucket": "StorageBucket",
        "Secret": "Secret",
    }

    # Convert resources
    resources = []
    for res in ai_spec.get("resources", []):
        kind = res.get("kind", "")
        mapped_kind = resource_kind_map.get(kind, kind)
        resources.append(
            {
                "kind": mapped_kind,
                "name": res.get("name", ""),
            }
        )

    # Build platform request format
    return {
        "kind": "Service",  # Platform API always uses "Service"
        "name": project_name or ai_spec.get("name", ""),
        "resources": resources,
    }


def read_neptune_json(directory: Path | None = None) -> dict | None:
    """Read neptune.json from directory.

    Args:
        directory: Directory to look in (defaults to cwd)

    Returns:
        Parsed neptune.json content or None if not found
    """
    import json

    dir_path = directory or Path.cwd()
    neptune_json = dir_path / "neptune.json"

    if not neptune_json.exists():
        return None

    with open(neptune_json) as f:
        return json.load(f)


def write_neptune_json(data: dict, directory: Path | None = None) -> Path:
    """Write neptune.json to directory.

    Args:
        data: Data to write
        directory: Directory to write to (defaults to cwd)

    Returns:
        Path to written file
    """
    import json

    dir_path = directory or Path.cwd()
    neptune_json = dir_path / "neptune.json"

    with open(neptune_json, "w") as f:
        json.dump(data, f, indent=2)

    return neptune_json


def read_project_name(directory: Path | None = None) -> str | None:
    """Read project name from .neptune/project_name or neptune.json.

    Args:
        directory: Directory to look in (defaults to cwd)

    Returns:
        Project name or None if not found
    """
    dir_path = directory or Path.cwd()

    # Try .neptune/project_name first
    project_name_file = dir_path / ".neptune" / "project_name"
    if project_name_file.exists():
        return project_name_file.read_text().strip()

    # Try neptune.json
    neptune_data = read_neptune_json(dir_path)
    if neptune_data:
        # Could be at top level or in spec
        if "name" in neptune_data:
            return neptune_data["name"]
        if "spec" in neptune_data and "name" in neptune_data["spec"]:
            return neptune_data["spec"]["name"]

    return None


def write_project_metadata(directory: Path, project_name: str) -> None:
    """Write project metadata to .neptune directory.

    Args:
        directory: Project directory
        project_name: Name of the project
    """
    meta_dir = directory / ".neptune"
    meta_dir.mkdir(parents=True, exist_ok=True)

    project_name_file = meta_dir / "project_name"
    project_name_file.write_text(project_name)


def write_start_command(directory: Path, start_command: str) -> None:
    """Write the generated start command to .neptune/start_command.

    Args:
        directory: Project directory
        start_command: The start command
    """
    meta_dir = directory / ".neptune"
    meta_dir.mkdir(parents=True, exist_ok=True)

    start_file = meta_dir / "start_command"
    start_file.write_text(start_command)


def read_start_command(directory: Path) -> str | None:
    """Read the start command from .neptune/start_command.

    Args:
        directory: Project directory

    Returns:
        Start command or None if not found
    """
    start_file = directory / ".neptune" / "start_command"
    if start_file.exists():
        return start_file.read_text().strip()
    return None


def resolve_project_name(directory: Path | None = None) -> str:
    """Resolve the project name from various sources.

    Priority:
    1. neptune.json spec.name
    2. .neptune/project_name
    3. Directory name

    Args:
        directory: Directory to resolve from (defaults to cwd)

    Returns:
        Project name

    Raises:
        ValueError: If no project name could be determined
    """
    dir_path = directory or Path.cwd()

    # Try neptune.json first
    neptune_data = read_neptune_json(dir_path)
    if neptune_data:
        if "name" in neptune_data:
            return neptune_data["name"]
        if "spec" in neptune_data and "name" in neptune_data["spec"]:
            return neptune_data["spec"]["name"]

    # Try .neptune/project_name
    meta_name = read_project_name(dir_path)
    if meta_name:
        return meta_name

    # Fall back to directory name
    return dir_path.resolve().name


def docker_installed() -> bool:
    """Check if Docker is installed."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def docker_running() -> bool:
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def clone_repo(
    url: str,
    dest: Path,
    subfolder: str | None = None,
    remove_git: bool = True,
) -> None:
    """Clone a git repository.

    Args:
        url: Repository URL
        dest: Destination directory
        subfolder: Optional subfolder within the repo
        remove_git: Whether to remove .git directory after cloning
    """
    if subfolder:
        # Clone to temp directory then copy subfolder
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            subprocess.run(
                ["git", "clone", "--depth", "1", url, str(tmp_path)],
                check=True,
                capture_output=True,
            )

            src = tmp_path / subfolder
            if not src.exists() or not src.is_dir():
                raise ValueError(f"Subfolder '{subfolder}' not found in repository")

            dest.mkdir(parents=True, exist_ok=True)
            _copy_tree(src, dest, ignore_git=True)
    else:
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            check=True,
            capture_output=True,
        )

        if remove_git:
            git_dir = dest / ".git"
            if git_dir.exists():
                shutil.rmtree(git_dir)


def _copy_tree(src: Path, dest: Path, ignore_git: bool = True) -> None:
    """Copy directory tree recursively."""
    dest.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        if ignore_git and item.name == ".git":
            continue

        dest_item = dest / item.name

        if item.is_dir():
            _copy_tree(item, dest_item, ignore_git)
        else:
            if not dest_item.exists():
                shutil.copy2(item, dest_item)
