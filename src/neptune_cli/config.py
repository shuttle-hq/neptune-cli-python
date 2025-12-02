from pathlib import Path

from platformdirs import user_config_dir
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class CLISettings(BaseSettings):
    """Configuration settings for the Neptune CLI."""

    # Local development: use `NEPTUNE_API_BASE_URL=http://localhost:8000/v1`
    api_base_url: str = "https://beta.neptune.dev/v1"

    access_token: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="NEPTUNE_",
        json_file=Path(user_config_dir("neptune")) / "config.json",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            JsonConfigSettingsSource(settings_cls),
        )

    def save_to_file(self) -> None:
        """Save the current settings to the configuration file."""
        config_path = Path(user_config_dir("neptune"))
        config_path.mkdir(parents=True, exist_ok=True)
        with open(config_path / "config.json", "w") as f:
            f.write(self.model_dump_json())


SETTINGS = CLISettings()
