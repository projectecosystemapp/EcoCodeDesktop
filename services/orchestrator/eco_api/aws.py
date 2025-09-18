from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, cast, runtime_checkable

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, NoCredentialsError

from .config import AWSSettings


@dataclass(slots=True)
class AWSStatus:
    region: str | None
    profile: str | None
    identity_arn: str | None
    account_id: str | None
    workspace_bucket_exists: bool | None
    errors: list[str]


@runtime_checkable
class _SupportsRead(Protocol):
    def read(self, __n: int | None = ...) -> bytes:  # pragma: no cover - protocol definition
        ...


class AWSClient:
    """Lightweight wrapper around boto3 for MVP status checks.

    Uses default credential/provider chain if explicit profile/region are not provided.
    """

    def __init__(self, settings: AWSSettings):
        self._settings = settings
        self._session = boto3.Session(
            profile_name=settings.profile_name or None,
            region_name=settings.region_name or None,
        )

    @property
    def region(self) -> str | None:
        return cast(str | None, getattr(self._session, "region_name", None))

    @property
    def profile(self) -> str | None:
        # boto3 does not expose profile on the session publicly; use provided config
        return self._settings.profile_name

    def _client(self, service: str) -> BaseClient:
        return self._session.client(service)

    def sts_identity(self) -> tuple[str | None, str | None, str | None]:
        try:
            sts = self._client("sts")
            resp = sts.get_caller_identity()
            arn = resp.get("Arn")
            account = resp.get("Account")
            user_id = resp.get("UserId")
            return (
                arn if isinstance(arn, str) else None,
                account if isinstance(account, str) else None,
                user_id if isinstance(user_id, str) else None,
            )
        except (BotoCoreError, NoCredentialsError):
            return None, None, None
        except Exception:
            return None, None, None

    def s3_bucket_exists(self, bucket: str) -> bool | None:
        try:
            s3 = self._client("s3")
            s3.head_bucket(Bucket=bucket)
            return True
        except (BotoCoreError, NoCredentialsError):
            return None
        except Exception:
            # If NotFound the SDK throws a generic ClientError; treat as False
            return False

    def status(self) -> AWSStatus:
        errors: list[str] = []
        arn, account_id, _ = self.sts_identity()
        bucket_exists: bool | None = None
        if self._settings.workspace_bucket:
            bucket_exists = self.s3_bucket_exists(self._settings.workspace_bucket)
            if bucket_exists is None:
                errors.append("S3 check skipped due to missing credentials or region")
        else:
            bucket_exists = None
        if arn is None:
            errors.append("Unable to resolve STS caller identity; credentials may be missing")
        return AWSStatus(
            region=self.region,
            profile=self.profile,
            identity_arn=arn,
            account_id=account_id,
            workspace_bucket_exists=bucket_exists,
            errors=errors,
        )

    # ---- Bedrock helpers ----
    def list_bedrock_models(self) -> list[str]:
        """Return a simple list of Bedrock model IDs.

        Uses the control-plane service 'bedrock' and the operation
        list_foundation_models. Returns an empty list if unavailable.
        """
        try:
            bedrock = self._client("bedrock")
            resp: dict[str, Any] = bedrock.list_foundation_models()
            summaries = resp.get("modelSummaries") or []
            models: list[str] = []
            for item in summaries:
                mid = item.get("modelId") if isinstance(item, dict) else None
                if isinstance(mid, str):
                    models.append(mid)
            return models
        except (BotoCoreError, NoCredentialsError):
            return []
        except Exception:
            return []

    def invoke_bedrock_text(self, model_id: str, prompt: str) -> str | None:
        """Invoke a Bedrock text model with a minimal prompt and return plain text.

        This uses the data-plane 'bedrock-runtime' invoke_model API with a
        generic body containing an 'inputText' field which is widely accepted
        by Amazon Titan; for other providers we still return best-effort by
        looking for a common 'outputText' field in the response JSON.
        """
        try:
            runtime = self._client("bedrock-runtime")
            body = json.dumps({"inputText": prompt})
            resp: dict[str, Any] = runtime.invoke_model(
                modelId=model_id,
                body=body,
                accept="application/json",
                contentType="application/json",
            )
            raw = resp.get("body")
            data_bytes: bytes
            if isinstance(raw, _SupportsRead):
                data_bytes = raw.read()
            elif isinstance(raw, (bytes, bytearray)):
                data_bytes = bytes(raw)
            elif isinstance(raw, str):
                data_bytes = raw.encode("utf-8")
            else:
                return None
            parsed = json.loads(data_bytes.decode("utf-8"))
            # Prefer 'outputText'; fall back to common shapes if needed
            if isinstance(parsed, dict):
                output_text = parsed.get("outputText")
                if isinstance(output_text, str):
                    return output_text
                # Anthropic messages proxy shape (very simplified)
                content = parsed.get("content")
                if isinstance(content, list) and content:
                    first = content[0]
                    if isinstance(first, dict):
                        text_value = first.get("text")
                        if isinstance(text_value, str):
                            return text_value
            return None
        except (BotoCoreError, NoCredentialsError):
            return None
        except Exception:
            return None
