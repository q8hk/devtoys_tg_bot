# DevToys Telegram Bot Privacy Policy

_Last updated: 2025-10-31_

## Overview

This document describes how the self-hosted DevToys Telegram Bot ("the Bot") processes and stores information. Operators deploying the Bot are responsible for ensuring compliance with local laws and for informing their users about any changes made to this policy.

## Data we process

The Bot processes the following categories of data:

- **Telegram metadata** such as chat identifiers, user identifiers, and usernames required to deliver messages and enforce permissions.
- **User-provided content** including text, files, and command parameters necessary to execute the requested utility.
- **Operational telemetry** such as timestamps, execution durations, and error details logged for observability and troubleshooting.

## Storage and retention

- Processed artifacts and temporary files are stored under the directory defined by the `PERSIST_DIR` environment variable (default `/data`).
- Temporary files created during tool execution are automatically purged as part of scheduled maintenance tasks (recommended interval: 24 hours).
- Operators may configure external storage (e.g., mounted volumes or object storage) to retain generated results for longer periods. Any extended retention is at the operator's discretion.

## Redis usage (optional)

When a Redis instance is configured via `REDIS_URL`, the Bot may store ephemeral job state, rate limiting counters, and cached results. These keys are short-lived and are automatically expired by Redis. No sensitive secrets or user payloads are persisted in Redis beyond what is required for task orchestration.

## Data sharing

- The Bot does not share user data with third parties by default.
- Telegram, as the hosting platform, receives content transmitted through their APIs as part of normal bot operation. Refer to Telegram's [Privacy Policy](https://telegram.org/privacy) for details.
- Operators may integrate external services (e.g., webhooks or storage providers). Such integrations are outside the scope of this document and must be disclosed separately by the operator.

## Security measures

- All processing occurs within the operator's infrastructure. No requests are sent to external APIs unless explicitly configured by the operator.
- Sensitive tokens (like `BOT_TOKEN`) should be stored in environment variables or secrets managers and never committed to version control.
- Access to the deployment host, Redis, and persistent volumes should be restricted to trusted administrators.

## User controls

Users can request removal of their data by contacting the bot operator directly. Administrators can delete stored artifacts by removing files from the persistence directory or clearing Redis keys.

## Contact

For privacy inquiries, contact the operator/administrator of your deployment. The open-source maintainers do not operate the bot on behalf of third parties.
