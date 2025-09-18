# Cloud Setup

EcoCode relies on AWS for secure storage, agent orchestration, and monitoring. This guide describes the minimum configuration required for the early-access release.

## Required Services

- **Amazon Bedrock**: Access to `anthropic.claude-3-5-sonnet-20240620-v1:0`, `anthropic.claude-3-sonnet-20240229-v1:0`, `amazon.titan-text-express-v1`, and `meta.llama3-70b-instruct-v1:0` foundation models.
- **Amazon S3**: Versioned bucket dedicated to encrypted workspace backups.
- **AWS Secrets Manager**: Central repository for API keys (OpenAI, Anthropic, Google, Groq, Perplexity, Stripe).
- **AWS KMS**: Customer-managed key for encrypting S3 objects and Secrets Manager records.
- **Amazon CloudWatch**: Dashboards and alarms covering agent cost, request latency, and error rates.

## Provisioning Checklist

1. Create an IAM role `EcoCodeOrchestratorRole` with permissions for Bedrock InvokeModel, S3 object CRUD on the workspace bucket, Secrets Manager read/write, KMS encrypt/decrypt, and CloudWatch PutMetricData.
2. Create an S3 bucket, e.g. `ecocode-${ENVIRONMENT}-workspaces`, enable versioning, block public access, and enforce default encryption using the KMS key.
3. In Secrets Manager, store API credentials under the following names:
   - `ecocode/bedrock/api`
   - `ecocode/openai/api`
   - `ecocode/anthropic/api`
   - `ecocode/google/api`
   - `ecocode/groq/api`
   - `ecocode/perplexity/api`
   - `ecocode/stripe/secret`
4. Configure automatic rotation for each secret (30-day cadence) using Lambda functions that refresh provider API keys where supported.
5. Define CloudWatch log groups: `/ecocode/orchestrator` and `/ecocode/desktop`. Enable log retention (at least 30 days) and create metrics filters for HTTP 4xx/5xx counts and Bedrock latency.
6. Set up CloudWatch alarms:
   - `EcoCodeAgentCostAnomaly` triggered when daily spend exceeds the rolling 7-day average by 40%.
   - `EcoCodeWorkspaceSyncFailures` triggered when failed S3 sync attempts exceed 5 in a 15-minute period.
7. Record the ARNs for the role, bucket, secrets, and KMS key; provide them as environment variables or configuration entries for the orchestrator service.

## Environment Variables

Add the following to the orchestrator runtime environment (e.g., `.env` file or process manager):

```
export ECOCODE_AWS_REGION_NAME="us-east-1"
export ECOCODE_AWS_PROFILE_NAME="ecocode-dev"
export ECOCODE_AWS_WORKSPACE_BUCKET="ecocode-dev-workspaces"
export ECOCODE_AWS_USE_BEDROCK=true
export ECOCODE_AWS_USE_S3_SYNC=true
export ECOCODE_AWS_USE_SECRETS_MANAGER=true
```

The orchestrator validates these settings during startup. If connectivity fails, the service logs a warning and continues operating in local-only mode.

