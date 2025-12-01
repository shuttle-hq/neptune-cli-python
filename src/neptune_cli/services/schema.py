"""Schema-related services.

These services handle JSON schema operations.
"""

from __future__ import annotations

from typing import Any

from neptune_cli.client import Client, get_client


def get_project_schema(client: Client | None = None) -> dict[str, Any]:
    """Get the JSON schema for neptune.json configuration.

    Args:
        client: Optional client instance

    Returns:
        JSON schema as dictionary
    """
    client = client or get_client()
    return client.get_project_schema()
