"""Generation-related services.

These services handle spec generation and related operations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from neptune_cli.client import Client, get_client
from neptune_cli.utils import (
    create_project_archive,
    read_neptune_json,
    resolve_project_name,
    ai_spec_to_platform_request,
    write_neptune_json,
    write_start_command,
)

if TYPE_CHECKING:
    pass


class SpecGenerationError(Exception):
    """Raised when spec generation fails."""

    def __init__(self, message: str):
        super().__init__(message)


@dataclass
class GenerateSpecResult:
    """Result of spec generation."""

    spec: dict[str, Any]
    spec_path: Path
    start_command: str | None
    ai_lint_report: Any | None = None
    changed: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "spec": self.spec,
            "spec_path": str(self.spec_path),
            "start_command": self.start_command,
            "changed": self.changed,
        }
        if self.ai_lint_report:
            result["ai_lint_report"] = self.ai_lint_report.model_dump(mode="json")
        return result


def generate_spec(
    working_dir: Path | None = None,
    project_name: str | None = None,
    client: Client | None = None,
) -> GenerateSpecResult:
    """Generate a neptune.json spec for a project.

    Uses the AI service to analyze the project and generate an appropriate
    configuration.

    Args:
        working_dir: Project directory (defaults to cwd)
        project_name: Optional project name override
        client: Optional client instance

    Returns:
        GenerateSpecResult with generated spec and metadata

    Raises:
        SpecGenerationError: If generation fails
    """
    working_dir = working_dir or Path.cwd()
    client = client or get_client()

    # Resolve project name
    if project_name is None:
        try:
            project_name = resolve_project_name(working_dir)
        except Exception:
            project_name = working_dir.name

    # Create archive and generate
    try:
        archive = create_project_archive(working_dir)
        gen_response = client.generate(archive, project_name)
    except Exception as e:
        raise SpecGenerationError(f"Failed to generate spec: {e}") from e

    # Convert to platform format
    ai_spec = gen_response.platform_spec.model_dump(mode="json")
    new_spec = ai_spec_to_platform_request(ai_spec, project_name)

    # Check if spec changed
    spec_path = working_dir / "neptune.json"
    changed = True

    if spec_path.exists():
        existing = read_neptune_json(working_dir)
        if existing:
            existing_normalized = json.dumps(existing, sort_keys=True)
            new_normalized = json.dumps(new_spec, sort_keys=True)
            changed = existing_normalized != new_normalized

    # Write spec
    write_neptune_json(new_spec, working_dir)

    # Save start command
    if gen_response.start_command:
        write_start_command(working_dir, gen_response.start_command)

    return GenerateSpecResult(
        spec=new_spec,
        spec_path=spec_path,
        start_command=gen_response.start_command,
        ai_lint_report=gen_response.ai_lint_report,
        changed=changed,
    )


def get_agents_md(client: Client | None = None) -> str:
    """Get the AGENTS.md content from the AI service.

    Args:
        client: Optional client instance

    Returns:
        AGENTS.md content as string

    Raises:
        Exception: If fetching fails
    """
    client = client or get_client()
    return client.get_agents_md()
