# Neptune MCP Release Process

This document explains the complete release workflow for Neptune MCP, including version management, PyInstaller builds, git tags, and GitHub releases.

## Table of Contents

-   [Neptune MCP Release Process](#neptune-mcp-release-process)
    -   [Table of Contents](#table-of-contents)
    -   [Release Workflow](#release-workflow)
        -   [Step 1: Bump the Version](#step-1-bump-the-version)
        -   [Step 2: Automatic Build Trigger](#step-2-automatic-build-trigger)
        -   [Step 3: Multi-Platform Builds](#step-3-multi-platform-builds)
        -   [Step 4: GitHub Release Creation](#step-4-github-release-creation)
    -   [Version Bumping](#version-bumping)
        -   [Semantic Versioning Rules](#semantic-versioning-rules)
        -   [Version File Locations](#version-file-locations)
    -   [PyInstaller Build Process](#pyinstaller-build-process)
        -   [Local Build](#local-build)
        -   [Keeping neptune.spec in Sync with Dependencies](#keeping-neptunespec-in-sync-with-dependencies)
        -   [Testing the Binary](#testing-the-binary)
        -   [Manual MCP Tool Testing](#manual-mcp-tool-testing)
    -   [Post-Release Testing](#post-release-testing)
        -   [What Gets Tested](#what-gets-tested)
        -   [Platforms Tested](#platforms-tested)
    -   [Summary Checklist](#summary-checklist)

## Release Workflow

### Step 1: Bump the Version

**Dry Run First** (Recommended):
Preview what would be changed without making actual changes:

```bash
python scripts/bump_version.py --dry-run
```

Example output:

```text
Latest tag: v0.1.2
Bumping patch version: 0.1.2 -> 0.1.3

Currently on 'main' branch
[DRY RUN] Would create and switch to branch: chore/bump-v0.1.3
[DRY RUN] Would update pyproject.toml to version: 0.1.3
[DRY RUN] Would create tag: v0.1.3
[DRY RUN] Would push branch 'chore/bump-v0.1.3' with upstream tracking
[DRY RUN] Would push tag to remote
```

Once you've verified the changes look correct, use the `bump_version.py` script to increment the version following semantic versioning:

```bash
# Patch version (0.0.x) - default for bug fixes
python scripts/bump_version.py --patch

# Minor version (0.x.0) - for new features
python scripts/bump_version.py --minor

# Major version (x.0.0) - for breaking changes
python scripts/bump_version.py --major
```

The script automatically handles branch creation and pushing. After the script runs, you can create a pull request to merge the version bump into main.

**What this script does**:

1. Detects if you're on the main branch
2. If on main, creates a new branch named `chore/bump-vX.Y.Z` and switches to it
3. Retrieves the latest git tag (e.g., `v0.1.2`)
4. Parses and increments the version based on the flag
5. Updates `version` in [pyproject.toml](../pyproject.toml)
6. Updates [uv.lock](../uv.lock) to reflect the new version
7. Commits the changes with message: `Bump version to X.Y.Z`
8. Pushes the branch to remote with upstream tracking
9. Creates a new git tag (e.g., `v0.1.3`)
10. Pushes the tag to the remote repository

**Local Only**:
To bump version without pushing to remote (useful for testing):

```bash
python scripts/bump_version.py --patch --no-push
```

**Note**: If you're already on a feature branch (not main), the script will use your current branch instead of creating a new one.

### Step 2: Automatic Build Trigger

Once the version tag is pushed, GitHub Actions automatically triggers the build workflow defined in [.github/workflows/build.yml](../.github/workflows/build.yml).

**Trigger Conditions**:

-   Automatic: When a tag matching `v*` pattern is pushed
-   Manual: Via workflow dispatch from GitHub Actions UI

### Step 3: Multi-Platform Builds

The build workflow creates executables for all supported platforms:

| Platform              | OS Runner        | Artifact Name             |
| --------------------- | ---------------- | ------------------------- |
| Linux (x64)           | ubuntu-latest    | neptune-linux-amd64       |
| Linux (ARM64)         | ubuntu-24.04-arm | neptune-linux-arm64       |
| macOS (Intel)         | macos-15-intel   | neptune-macos-amd64       |
| macOS (Apple Silicon) | macos-latest     | neptune-macos-arm64       |
| Windows (x64)         | windows-latest   | neptune-windows-amd64.exe |

### Step 4: GitHub Release Creation

After all platform builds complete successfully, the workflow:

1. Downloads all build artifacts
2. Creates a GitHub release with the tag name
3. Attaches all platform binaries to the release
4. Auto-generates release notes from recent commits
5. Marks the release as the latest

## Version Bumping

### Semantic Versioning Rules

Neptune MCP follows [Semantic Versioning](https://semver.org/):

-   **MAJOR** (X.0.0): Breaking changes, incompatible API changes
-   **MINOR** (0.X.0): New features, backward-compatible
-   **PATCH** (0.0.X): Bug fixes, backward-compatible

### Version File Locations

The version is stored in:

-   [pyproject.toml](../pyproject.toml): Line 3 - `version = "X.Y.Z"`
-   Git tags: Format `vX.Y.Z`

## PyInstaller Build Process

### Local Build

To test the PyInstaller build locally:

```bash
# Quick build
./scripts/build.sh
```

The build script:

1. Cleans previous build artifacts from `build/` and `dist/`
2. Runs PyInstaller with [neptune.spec](../neptune.spec)
3. Produces a single executable at `dist/neptune`
4. Verifies the binary works by running `neptune --help`

### Keeping neptune.spec in Sync with Dependencies

PyInstaller uses the same dependencies as its environment, so in the workflow packages are always in sync with [pyproject.toml](../pyproject.toml). The spec file collects dependencies from the installed environment during build. Only update [neptune.spec](../neptune.spec) manually if a package uses dynamic imports or plugins (add to `packages_to_collect`) or if the build fails with import errors (add to `hiddenimports`).

For more information, see [PyInstaller spec files documentation](https://pyinstaller.org/en/stable/spec-files.html).

### Testing the Binary

After building:

```bash
# Check binary exists and size
ls -lh dist/neptune

# Test help output
./dist/neptune --help

# Test MCP server mode
./dist/neptune mcp
```

### Manual MCP Tool Testing

Python lacks compile-time safety and supports dynamic imports (e.g., conditional imports), so all MCP tools must be manually tested for edge cases. A binary may compile successfully and some tools may work, while others fail due to dependencies with dynamic imports missing from neptune.spec. These errors only surface at runtime.

## Post-Release Testing

After a release is published, automated tests run via [.github/workflows/test-releases.yml](../.github/workflows/test-releases.yml). This is more of an install script test rather than a binary test—it doesn't ensure that all MCP tools work. Dynamic import errors won't be caught here.

### What Gets Tested

The test workflow validates:

1. Installation scripts work on all platforms
2. Binaries are downloadable from the latest release
3. Installed binary runs successfully (`neptune --help`)

### Platforms Tested

-   **Unix**: ubuntu-latest, ubuntu-24.04-arm, macos-latest, macos-15-intel
-   **Windows**: windows-latest

## Summary Checklist

For a complete release:

-   [ ] Ensure working directory is clean
-   [ ] Pull latest changes from main branch
-   [ ] Run dry run first: `python scripts/bump_version.py --dry-run`
-   [ ] Verify the dry run output looks correct
-   [ ] Run `python scripts/bump_version.py` (or `--minor`/`--major`)
-   [ ] Script automatically creates branch, commits, tags, and pushes
-   [ ] Create a pull request to merge the version bump into main
-   [ ] Merge the pull request
-   [ ] GitHub Actions builds all platform binaries (triggered by tag)
-   [ ] GitHub release is created with all assets
-   [ ] (Optional) Manually run the post-release tests workflow to test the binary on all platforms
-   [ ] Manually verify installation works
-   [ ] Update documentation if needed
