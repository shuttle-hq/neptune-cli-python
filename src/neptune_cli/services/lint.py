"""Lint-related services.

These services handle AI lint operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from neptune_cli.client import Client, get_client
from neptune_cli.utils import create_project_archive

if TYPE_CHECKING:
    from neptune_cli.types import AiLintReport


def run_ai_lint(
    working_dir: Path | None = None,
    client: Client | None = None,
) -> AiLintReport:
    """Run AI lint on a project.

    Args:
        working_dir: Project directory (defaults to cwd)
        client: Optional client instance

    Returns:
        AiLintReport with findings
    """
    working_dir = working_dir or Path.cwd()
    client = client or get_client()

    archive = create_project_archive(working_dir)
    return client.ai_lint(archive)
