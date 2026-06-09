import os
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .._metadata import app_name, app_slug

project_root = Path(__file__).parent.parent.parent.parent
env_file = project_root / ".env"

if env_file.exists():
    load_dotenv(dotenv_path=env_file)


class AppConfig(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=env_file, env_prefix=f"{app_slug.upper()}_", extra="ignore"
    )
    app_name: str = Field(default=app_name)
    lakebase_project: str = Field(default="kpi-reporting")
    force_mock: bool = Field(default=False)

    # Lakebase — injected by Databricks App resource (PGHOST, PGUSER, ENDPOINT_NAME)
    pg_host: str = Field(default_factory=lambda: os.environ.get("PGHOST", ""))
    pg_user: str = Field(default_factory=lambda: os.environ.get("PGUSER", ""))
    pg_password: str = Field(default="")
    pg_endpoint_name: str = Field(default_factory=lambda: os.environ.get("ENDPOINT_NAME", ""))

    # Confluence integration
    confluence_base_url: str = Field(default="")
    confluence_api_token: str = Field(default="")
    confluence_user_email: str = Field(default="")
    confluence_space_key: str = Field(default="")
    confluence_parent_page_id: str = Field(default="")

    # Genie Space — injected by Databricks App resource (GENIE_SPACE_ID)
    genie_space_id: str = Field(default_factory=lambda: os.environ.get("GENIE_SPACE_ID", ""))

    # Databricks workspace host — auto-injected by Apps as DATABRICKS_HOST.
    # Used to build the deep link to the embedded Genie Space.
    databricks_host: str = Field(default_factory=lambda: os.environ.get("DATABRICKS_HOST", ""))
