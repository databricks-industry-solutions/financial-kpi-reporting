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


def _derive_ai_gateway_url(databricks_host: str) -> str:
    """Derive an OpenAI-compatible base URL from the Databricks workspace host.

    Uses the direct foundation-model serving endpoint URL, which works on all
    clouds (AWS, Azure, GCP) without requiring a dedicated AI Gateway route:

        https://<workspace-host>/serving-endpoints

    Preferred over an AI Gateway subdomain URL because it needs no extra setup —
    any workspace with foundation models enabled works immediately.

    The KPI_REPORTING_AI_GATEWAY_URL env var (set by notebook 03) overrides this
    entirely, so explicit AI Gateway routes still take precedence.
    """
    host = (databricks_host or "").strip().rstrip("/")
    if not host:
        return ""
    if not host.startswith("https://"):
        host = f"https://{host}"
    return f"{host}/serving-endpoints"


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
    # Used to build deep links and to derive the AI Gateway URL.
    databricks_host: str = Field(default_factory=lambda: os.environ.get("DATABRICKS_HOST", ""))

    # OpenAI-compatible base URL for the agent features. When set explicitly (by
    # notebook 03) this value is used as-is — it can be an AI Gateway route URL or
    # a direct serving-endpoint URL. When blank it falls back to
    # https://<DATABRICKS_HOST>/serving-endpoints, which works on all clouds.
    ai_gateway_url: str = Field(default="")

    # AI/BI Dashboard ID — injected by notebook 03 after creating the dashboard.
    aibi_dashboard_id: str = Field(default="")

    def get_ai_gateway_url(self) -> str:
        """Return the AI Gateway URL, deriving it from the workspace host if unset."""
        if self.ai_gateway_url:
            return self.ai_gateway_url
        return _derive_ai_gateway_url(self.databricks_host)
