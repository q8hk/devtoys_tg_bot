<p align="center">
  <img src="assets/banner.png" alt="DevToys Telegram Bot Banner" width="100%" />
</p>

# DevToys Telegram Bot

Self-hostable Telegram bot inspired by [DevToys](https://github.com/veler/DevToys). The bot delivers a curated set of developer utilities (formatters, encoders, converters, generators) through a friendly conversational UX, designed for private teams and personal productivity.

## Features

- Rich catalog of developer utilities grouped into intuitive categories.
- Fully async bot powered by [aiogram](https://docs.aiogram.dev/) with optional Redis-backed rate limiting and background work queues.
- File-safe processing with configurable size limits and persistent storage on mounted volumes.
- Structured logging, admin tooling, and extensible router architecture for adding new utilities.

## Screenshots

> :camera: Replace or extend the gallery below with real screenshots of your deployment.

| Home menu | Tool result |
| --- | --- |
| ![Home menu](assets/banner.png) | ![Tool result placeholder](assets/banner.png) |

## Quick start

1. Copy `.env.example` to `.env` and populate the values (at minimum `BOT_TOKEN`).
2. Build the Docker image:
   ```bash
   docker build -t devtoys-tg-bot .
   ```
3. Launch the stack with Docker Compose (Redis optional, enabled via the `redis` profile):
   ```bash
   docker compose --profile redis up --build
   ```
   Omit `--profile redis` to run without Redis.
4. Invite your Telegram account to the bot and run `/start`.

## Configuration

All configuration is sourced from environment variables. See [`.env.example`](.env.example) for inline documentation of every setting.

| Variable | Required | Description |
| --- | --- | --- |
| `BOT_TOKEN` | ✅ | Telegram bot token from [@BotFather](https://t.me/BotFather). |
| `ADMINS` | ⚙️ | Comma-separated Telegram user IDs that receive elevated privileges. |
| `MAX_FILE_MB` | ⚙️ | Maximum file size accepted from users (defaults to 15). |
| `RATE_LIMIT_PER_USER_PER_MIN` | ⚙️ | Per-user rate limit for executed utilities per minute (defaults to 30). |
| `PERSIST_DIR` | ⚙️ | Directory where user workspaces and generated files are stored (defaults to `/data`). |
| `REDIS_URL` | ⚙️ | Optional Redis connection string for caching, queues, and shared rate limiting. Leave blank to disable Redis. |

## Command reference

| Command | Purpose |
| --- | --- |
| `/start` | Open the main menu. |
| `/help` | Display usage guidance and onboarding tips. |
| `/tools` | Browse the full catalog of utilities. |
| `/recent` | Show the last 10 tasks performed by the current user. |
| `/cancel` | Cancel the current operation and return to the home menu. |
| `/settings` | Adjust per-user preferences (output format, timezone, etc.). |
| `/admin` | Open the admin dashboard (admins only). |
| `/privacy` | View the privacy policy. |

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Run formatting and linting:

```bash
ruff check src tests
black src tests
```

Execute tests:

```bash
pytest
```

Launch the bot locally without Docker:

```bash
export $(grep -v '^#' .env | xargs)
python -m bot.main
```

## Docker deployment

The provided [`Dockerfile`](Dockerfile) builds a slim production image and exposes `/data` as a volume for persistent storage. [`docker-compose.yml`](docker-compose.yml) wires the bot together with optional Redis and mounts the `data` volume by default.

- Mount a host directory to `data` if you need to back up generated files.
- Start Redis by adding the `redis` profile: `docker compose --profile redis up -d`.
- Scale horizontally by running multiple bot containers that share the same Redis instance.

## Privacy

A human-readable privacy policy is available at [`assets/privacy_policy.md`](assets/privacy_policy.md) and is surfaced to users via the `/privacy` command.

## Attribution

Inspired by the DevToys project. Functionality is re-implemented in Python specifically for Telegram; no UI assets or code were copied.

## License

MIT
