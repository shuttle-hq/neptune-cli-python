"""Logs-related services.

These services handle log retrieval operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neptune_cli.client import Client, get_client


@dataclass
class LogsResult:
    """Result of logs retrieval."""

    project_name: str
    logs: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_name": self.project_name,
            "logs": self.logs,
        }


def get_logs(
    project_name: str,
    client: Client | None = None,
) -> LogsResult:
    """Get logs for a project.

    Args:
        project_name: Name of the project
        client: Optional client instance

    Returns:
        LogsResult with log lines
    """
    client = client or get_client()
    logs_response = client.get_logs(project_name)

    return LogsResult(
        project_name=project_name,
        logs=logs_response.logs,
    )
