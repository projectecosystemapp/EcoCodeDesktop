from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AWSSettings(BaseSettings):
    """Configuration for AWS integrations."""

    region_name: str | None = None
    profile_name: str | None = None
    workspace_bucket: str | None = None
    use_bedrock: bool = True
    use_s3_sync: bool = True
    use_secrets_manager: bool = True

    model_config = SettingsConfigDict(env_prefix="ECOCODE_AWS_", env_file=None)


class AgentSettings(BaseSettings):
    """Controls for agent orchestration."""

    supervisor_model: Literal[
        "amazon.titan-text-express-v1",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "meta.llama3-70b-instruct-v1:0",
    ] = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    planning_model: str = "anthropic.claude-3-haiku-20240307-v1:0"
    coding_model: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    review_model: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    research_model: str = "amazon.titan-text-express-v1"

    model_config = SettingsConfigDict(env_prefix="ECOCODE_AGENT_", env_file=None)


class Settings(BaseSettings):
    """Application configuration."""

    master_passphrase: str
    projects_root: Path = Path.cwd()
    workspace_suffix: str = "__eco_workspace"
    enforce_encryption: bool = True
    aws: AWSSettings = Field(default_factory=AWSSettings)
    agents: AgentSettings = Field(default_factory=AgentSettings)

    model_config = SettingsConfigDict(env_prefix="ECOCODE_", env_file=None)

    def workspace_path_for(self, project_path: Path) -> Path:
        project_path = project_path.expanduser().resolve()
        return project_path.parent / f"{project_path.name}{self.workspace_suffix}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]  # BaseSettings reads values from env/config at runtime
    if not settings.master_passphrase:
        raise ValueError("ECOCODE_MASTER_PASSPHRASE is required for secure operation")
    return settings
