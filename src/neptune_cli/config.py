# Standard Library Imports
import json
import os
from functools import cached_property
from pathlib import Path
from typing import Any

# Third-Party Imports
from platformdirs import user_config_dir
from pydantic import (
    Field,
    computed_field,
)
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

LOCAL_API_BASE_URL: str = "http://localhost:8000/v1"
DEFAULT_API_BASE_URL: str = "https://neptune.shuttle.dev/v1"

NEPTUNE_CFG_FILE_PATH: Path = Path(user_config_dir("neptune")) / "config.json"

os.environ["NEPTUNE_API_BASE_URL"] = (
    LOCAL_API_BASE_URL
    if str(os.environ.get("NEPTUNE_API_ENV")).casefold() == "local"
    else DEFAULT_API_BASE_URL
)


class NeptuneJsonConfigSource(PydanticBaseSettingsSource):
    """A simple settings source class that loads variables from a JSON file
    in the local platform's configuration directory.
    """

    @computed_field
    @cached_property
    def _json_data(self) -> dict[str, Any]:
        data = json.loads(NEPTUNE_CFG_FILE_PATH.read_bytes())

        return data

    def get_field_value(
        self,
        field: FieldInfo,
        field_name: str,
    ) -> tuple[Any, str, bool]:
        value = self._json_data.get(field_name) or field.default_factory()

        return value, field_name, False

    def __call__(self) -> dict[str, Any]:
        data: dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(
                field,
                field_name,
            )

            data[field_key] = self.prepare_field_value(
                field_name,
                field,
                field_value,
                value_is_complex,
            )

        return data


class CLISettings(BaseSettings):
    """Configuration settings for the Neptune CLI."""

    model_config = SettingsConfigDict(
        env_prefix="NEPTUNE_",
    )

    access_token: str | None = Field(default=None)
    api_base_url: str = Field(default=DEFAULT_API_BASE_URL)

    def save_to_file(self) -> None:
        """Save the current settings to the configuration file."""
        NEPTUNE_CFG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        with NEPTUNE_CFG_FILE_PATH.open("w") as writer:
            writer.write(self.model_dump_json())

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
            NeptuneJsonConfigSource(settings_cls),
        )


SETTINGS = CLISettings()
