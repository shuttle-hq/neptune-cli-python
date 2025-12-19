#!/usr/bin/env python3
"""
Script to bump version in git tags and pyproject.toml.
Increments patch version by default, or minor/major with flags.
"""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def find_uv():
    """Find uv executable path."""
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    fallback = os.path.expanduser("~/.local/bin/uv")
    if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
        return fallback
    return "uv"


def run_command(cmd, check=True, capture_output=True):
    """Run a shell command and return result."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture_output,
        text=True,
        check=check,
    )
    return result


def get_latest_tag():
    """Get the latest git tag."""
    result = run_command("git tag --sort=-v:refname", check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None

    tags = result.stdout.strip().split("\n")
    for tag in tags:
        # Find first tag that matches semver pattern
        if re.match(r"^v?\d+\.\d+\.\d+$", tag):
            return tag
    return None


def parse_version(version_str):
    """Parse version string into major, minor, patch."""
    # Remove 'v' prefix if present
    version_str = version_str.lstrip("v")
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(map(int, match.groups()))


def bump_version(version, bump_type):
    """Bump version based on type (major, minor, patch)."""
    major, minor, patch = version

    if bump_type == "major":
        return (major + 1, 0, 0)
    elif bump_type == "minor":
        return (major, minor + 1, 0)
    elif bump_type == "patch":
        return (major, minor, patch + 1)
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def format_version(version, with_v=False):
    """Format version tuple as string."""
    version_str = f"{version[0]}.{version[1]}.{version[2]}"
    return f"v{version_str}" if with_v else version_str


def update_pyproject_toml(new_version):
    """Update version in pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found", file=sys.stderr)
        sys.exit(1)

    content = pyproject_path.read_text()

    # Update version line
    updated_content = re.sub(
        r'^version\s*=\s*"[^"]+"', f'version = "{new_version}"', content, count=1, flags=re.MULTILINE
    )

    if content == updated_content:
        print(f"Warning: No version field found in {pyproject_path}", file=sys.stderr)
        return False

    pyproject_path.write_text(updated_content)
    return True


def get_current_branch():
    """Get the current git branch name."""
    result = run_command("git branch --show-current", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def create_branch(branch_name):
    """Create a new git branch and switch to it."""
    result = run_command(f"git checkout -b {branch_name}", check=False)
    if result.returncode != 0:
        print(f"Error creating branch: {result.stderr}", file=sys.stderr)
        return False
    print(f"Created and switched to branch: {branch_name}")
    return True


def push_branch_with_upstream(branch_name):
    """Push branch to remote and set upstream tracking."""
    result = run_command(f"git push -u origin {branch_name}", check=False)
    if result.returncode != 0:
        print(f"Error pushing branch: {result.stderr}", file=sys.stderr)
        return False
    print(f"Pushed branch to remote with upstream tracking: {branch_name}")
    return True


def create_and_push_tag(tag_name, push=True):
    """Create git tag and optionally push to remote."""
    # Create the tag
    result = run_command(f"git tag {tag_name}", check=False)
    if result.returncode != 0:
        print(f"Error creating tag: {result.stderr}", file=sys.stderr)
        return False

    print(f"Created tag: {tag_name}")

    if push:
        # Push the tag to remote
        result = run_command(f"git push origin {tag_name}", check=False)
        if result.returncode != 0:
            print(f"Error pushing tag: {result.stderr}", file=sys.stderr)
            # Delete the local tag if push failed
            run_command(f"git tag -d {tag_name}", check=False)
            return False
        print(f"Pushed tag to remote: {tag_name}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Bump version in git tags and pyproject.toml")
    parser.add_argument("--major", action="store_true", help="Bump major version (x.0.0)")
    parser.add_argument("--minor", action="store_true", help="Bump minor version (0.x.0)")
    parser.add_argument("--patch", action="store_true", help="Bump patch version (0.0.x) - default")
    parser.add_argument("--no-push", action="store_true", help="Do not push tag to remote")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    args = parser.parse_args()

    # Determine bump type
    bump_type = "patch"  # default
    if args.major:
        bump_type = "major"
    elif args.minor:
        bump_type = "minor"
    elif args.patch:
        bump_type = "patch"

    # Get latest tag
    latest_tag = get_latest_tag()

    if latest_tag:
        print(f"Latest tag: {latest_tag}")
        current_version = parse_version(latest_tag)
    else:
        print("No existing tags found, starting from 0.0.0")
        current_version = (0, 0, 0)

    # Bump version
    new_version = bump_version(current_version, bump_type)
    new_version_str = format_version(new_version)
    new_tag = format_version(new_version, with_v=True)

    print(f"Bumping {bump_type} version: {format_version(current_version)} -> {new_version_str}")

    # Check if we're on main/master branch
    current_branch = get_current_branch()
    if current_branch in ["main"]:
        print(f"\nCurrently on '{current_branch}' branch")
        branch_name = f"chore/bump-{new_tag}"

        if args.dry_run:
            print(f"[DRY RUN] Would create and switch to branch: {branch_name}")
        else:
            if not create_branch(branch_name):
                sys.exit(1)
    else:
        print(f"\nCurrently on branch: {current_branch}")
        branch_name = current_branch

    if args.dry_run:
        print(f"\n[DRY RUN] Would update pyproject.toml to version: {new_version_str}")
        print(f"[DRY RUN] Would create tag: {new_tag}")
        if not args.no_push:
            print(f"[DRY RUN] Would push branch '{branch_name}' with upstream tracking")
            print("[DRY RUN] Would push tag to remote")
        return

    # Update pyproject.toml
    print(f"\nUpdating pyproject.toml to version {new_version_str}...")
    if not update_pyproject_toml(new_version_str):
        sys.exit(1)

    # Update uv lock file
    print("Updating uv.lock...")
    uv_cmd = find_uv()
    result = run_command(f"{uv_cmd} lock", check=False)
    if result.returncode != 0:
        print(f"Error updating uv.lock: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Stage the pyproject.toml and uv.lock changes
    result = run_command("git add pyproject.toml uv.lock", check=False)
    if result.returncode != 0:
        print(f"Error staging files: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Commit the version change
    commit_msg = f"Bump version to {new_version_str}"
    result = run_command(f'git commit -m "{commit_msg}"', check=False)
    if result.returncode != 0:
        print(f"Error committing version change: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    print("Committed version change")

    # Push the branch with upstream tracking
    if not args.no_push:
        if not push_branch_with_upstream(branch_name):
            sys.exit(1)

    # Create and push tag
    if not create_and_push_tag(new_tag, push=not args.no_push):
        sys.exit(1)

    print(f"\n✓ Successfully bumped version to {new_version_str} ({new_tag})")
    print(f"✓ Branch '{branch_name}' is ready for a pull request")


if __name__ == "__main__":
    main()
