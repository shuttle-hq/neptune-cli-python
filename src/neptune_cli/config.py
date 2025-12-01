"""Configuration management for the Neptune CLI.

Supports hierarchical configuration loading:
1. Default values
2. Global config (~/.config/neptune/config.toml)
3. Local config (Neptune.toml in project directory)
4. Local internal config (.neptune/config.toml)
5. Environment variables (NEPTUNE_*)
6. CLI arguments (highest priority)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import toml
from dotenv import load_dotenv, find_dotenv
from platformdirs import user_config_dir

# Load .env files - first from global config dir, then from cwd (cwd takes precedence)
_global_env = Path(user_config_dir("neptune")) / ".env"
if _global_env.exists():
    load_dotenv(_global_env)
load_dotenv(find_dotenv(usecwd=True))

# Default API URLs
DEFAULT_API_URL = "https://neptune.shuttle.dev/v1"
DEFAULT_AI_URL = "https://tooling-demo.impulse.shuttle.dev"

# Config directory name
CONFIG_DIR_NAME = "neptune"


@dataclass
class NeptuneConfig:
    """Neptune CLI configuration.

    All fields are optional to support layered merging.
    """

    api_url: str | None = None
    ai_url: str | None = None
    api_key: str | None = None
    access_token: str | None = None
    ai_token: str | None = None
    debug: bool | None = None

    def merge_with(self, other: NeptuneConfig) -> NeptuneConfig:
        """Create a new config with values from other overriding self."""
        return NeptuneConfig(
            api_url=other.api_url or self.api_url,
            ai_url=other.ai_url or self.ai_url,
            api_key=other.api_key or self.api_key,
            access_token=other.access_token or self.access_token,
            ai_token=other.ai_token or self.ai_token,
            debug=other.debug if other.debug is not None else self.debug,
        )


@dataclass
class ResolvedConfig:
    """Fully resolved configuration with no optional fields."""

    api_url: str
    ai_url: str
    api_key: str | None
    access_token: str | None
    ai_token: str | None
    debug: bool

    @property
    def auth_token(self) -> str | None:
        """Get the authentication token (API key or access token)."""
        return self.api_key or self.access_token

    @property
    def ai_auth_token(self) -> str | None:
        """Get the authentication token for AI service."""
        return self.ai_token or self.auth_token


def get_global_config_dir() -> Path:
    """Get the global config directory path."""
    return Path(user_config_dir(CONFIG_DIR_NAME))


def get_global_config_path() -> Path:
    """Get the global config file path."""
    return get_global_config_dir() / "config.toml"


def get_local_config_path(directory: Path | None = None) -> Path:
    """Get the local config file path (Neptune.toml)."""
    return (directory or Path.cwd()) / "Neptune.toml"


def get_local_internal_config_path(directory: Path | None = None) -> Path:
    """Get the local internal config file path (.neptune/config.toml)."""
    return (directory or Path.cwd()) / ".neptune" / "config.toml"


def load_toml_config(path: Path) -> NeptuneConfig:
    """Load configuration from a TOML file."""
    if not path.exists():
        return NeptuneConfig()

    try:
        data = toml.load(path)
        return NeptuneConfig(
            api_url=data.get("api_url"),
            ai_url=data.get("ai_url"),
            api_key=data.get("api_key"),
            access_token=data.get("access_token"),
            ai_token=data.get("ai_token"),
            debug=data.get("debug"),
        )
    except Exception:
        return NeptuneConfig()


def load_env_config() -> NeptuneConfig:
    """Load configuration from environment variables."""
    return NeptuneConfig(
        api_url=os.environ.get("NEPTUNE_API_URL") or os.environ.get("NEPTUNE_API"),
        ai_url=os.environ.get("NEPTUNE_AI_URL") or os.environ.get("NEPTUNE_AI"),
        api_key=os.environ.get("NEPTUNE_API_KEY"),
        access_token=os.environ.get("NEPTUNE_ACCESS_TOKEN"),
        ai_token=os.environ.get("NEPTUNE_AI_TOKEN"),
        debug=_parse_bool_env("NEPTUNE_DEBUG"),
    )


def _parse_bool_env(name: str) -> bool | None:
    """Parse a boolean environment variable."""
    value = os.environ.get(name)
    if value is None:
        return None
    return value.lower() in ("1", "true", "yes", "on")


def default_config() -> NeptuneConfig:
    """Get the default configuration values."""
    return NeptuneConfig(
        api_url=DEFAULT_API_URL,
        ai_url=DEFAULT_AI_URL,
        api_key=None,
        access_token=None,
        ai_token=None,
        debug=False,
    )


def load_config(
    working_directory: Path | None = None,
    cli_overrides: NeptuneConfig | None = None,
) -> ResolvedConfig:
    """Load and resolve configuration from all sources.

    Priority (lowest to highest):
    1. Default values
    2. Global config (~/.config/neptune/config.toml)
    3. Local config (Neptune.toml)
    4. Local internal config (.neptune/config.toml)
    5. Environment variables
    6. CLI arguments

    Args:
        working_directory: The working directory for local configs
        cli_overrides: Configuration from CLI arguments

    Returns:
        Fully resolved configuration
    """
    config = default_config()

    # Global config
    config = config.merge_with(load_toml_config(get_global_config_path()))

    # Local configs
    wd = working_directory or Path.cwd()
    config = config.merge_with(load_toml_config(get_local_config_path(wd)))
    config = config.merge_with(load_toml_config(get_local_internal_config_path(wd)))

    # Environment variables
    config = config.merge_with(load_env_config())

    # CLI overrides
    if cli_overrides:
        config = config.merge_with(cli_overrides)

    # Convert to resolved config
    return ResolvedConfig(
        api_url=config.api_url or DEFAULT_API_URL,
        ai_url=config.ai_url or DEFAULT_AI_URL,
        api_key=config.api_key,
        access_token=config.access_token,
        ai_token=config.ai_token,
        debug=config.debug or False,
    )


def save_global_config(config: NeptuneConfig) -> None:
    """Save configuration to the global config file."""
    config_dir = get_global_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = get_global_config_path()

    # Load existing config and merge
    existing = load_toml_config(config_path)
    merged = existing.merge_with(config)

    # Convert to dict, filtering out None values
    data = {
        k: v
        for k, v in {
            "api_url": merged.api_url,
            "ai_url": merged.ai_url,
            "api_key": merged.api_key,
            "access_token": merged.access_token,
            "ai_token": merged.ai_token,
            "debug": merged.debug,
        }.items()
        if v is not None
    }

    with open(config_path, "w") as f:
        toml.dump(data, f)


def clear_auth() -> None:
    """Clear authentication tokens from global config."""
    config_path = get_global_config_path()
    if not config_path.exists():
        return

    try:
        data = toml.load(config_path)
        data.pop("api_key", None)
        data.pop("access_token", None)

        with open(config_path, "w") as f:
            toml.dump(data, f)
    except Exception:
        pass


# ==============================================================================
# Global Settings
# ==============================================================================


class Settings:
    """Lazy-loaded settings singleton for CLI usage."""

    def __init__(self) -> None:
        self._config: ResolvedConfig | None = None

    def _get_config(self) -> ResolvedConfig:
        if self._config is None:
            self._config = load_config()
        return self._config

    def reload(self, working_directory: Path | None = None) -> None:
        """Reload configuration from disk."""
        self._config = load_config(working_directory)

    @property
    def api_base_url(self) -> str:
        return self._get_config().api_url

    @property
    def auth_token(self) -> str | None:
        return self._get_config().auth_token


SETTINGS = Settings()
