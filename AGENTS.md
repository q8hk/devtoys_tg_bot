# AGENTS.md

## Purpose
Build a **production-ready, self-hostable Telegram bot** that exposes a rich set of developer utilities (converters, encoders/decoders, generators, validators, formatters, testers) inspired by the **DevToys** project. The bot must be elegant, fast, reliable, and easy to deploy with Docker.

---

## Tech & Standards
- **Language:** Python 3.12+
- **Framework:** `aiogram` v3 (preferred) or `python-telegram-bot` v21+ (async)
- **Packaging:** `uv` or `pip` (lock dependencies)
- **Container:** Dockerfile + docker-compose
- **Style:** PEP-8, type hints, `ruff` + `black`
- **Logging:** `structlog` or `logging` w/ JSON output
- **Tests:** `pytest` (unit for core utils, smoke for handlers)
- **License/Attribution:** include a short NOTICE acknowledging inspiration by DevToys; do not copy their UI; re-implement utilities in Python.

---

## Repository Layout
```
devtoys_tg_bot/
  src/
    bot/__init__.py
    bot/main.py
    bot/config.py
    bot/keyboards.py
    bot/middlewares.py
    bot/rate_limit.py
    bot/routers/__init__.py
    bot/routers/home.py
    bot/routers/admin.py
    bot/routers/files.py
    bot/routers/tools/
      text_tools.py
      json_yaml.py
      url_codec.py
      base64_codec.py
      hash_tools.py
      jwt_tools.py
      uuid_ulid.py
      time_tools.py
      regex_tools.py
      color_tools.py
      qr_tools.py
      image_tools.py
      csv_tsv.py
      xml_tools.py
      html_tools.py
      code_tools.py
  src/core/
    __init__.py
    errors.py
    i18n.py
    utils/
      text.py
      json_yaml.py
      url.py
      base64_.py
      hash_.py
      jwt_.py
      uuid_ulid.py
      time_.py
      regex_.py
      color_.py
      qr_.py
      image_.py
      csv_tsv.py
      xml_.py
      html_.py
      code_.py
  tests/
  Dockerfile
  docker-compose.yml
  README.md
  .env.example
  pyproject.toml
  ruff.toml
```

---

## Configuration
Environment variables:
- `BOT_TOKEN` (required)
- `ADMINS` (comma-separated user IDs)
- `MAX_FILE_MB` (default 15)
- `RATE_LIMIT_PER_USER_PER_MIN` (default 30)
- `PERSIST_DIR` (default `/data`)
- `REDIS_URL` (optional; for rate limits + job queue)

---

## User Experience
- **Start/Home:** `/start` shows an elegant home menu with InlineKeyboard grouping tools by category. Include `/help`, `/about`, `/privacy`.
- **Per-tool flow:** concise intro -> choose input method (text/file/buttons) -> validate -> render result -> offer **Back / Copy / Share / Run again**.
- **Large results:** send as files (`.txt`, `.json`, `.yaml`, etc.).
- **I18N-ready:** English default with simple JSON catalogs.
- **Accessibility:** clear error messages with tips and examples.

---

## Tool Set (first-class)
Implement as pure, tested functions in `src/core/utils/` and expose via routers.

1. **Text Tools**
   - Trim/indent/outdent; whitespace normalize; case convert; slugify
   - Sort lines; unique/dedupe; add/remove line numbers
   - Random text / lorem ipsum generator

2. **JSON / YAML**
   - Pretty/minify; **JSON <-> YAML** convert; validate; diff summary
   - Auto-detect inputs when possible

3. **URL Tools**
   - Encode/decode; parse & pretty query params; rebuild URLs

4. **Base64**
   - Encode/decode strings and files; handle `data:` URIs

5. **Hash & HMAC**
   - MD5, SHA-1/224/256/384/512; streamed file hashing
   - HMAC with selectable digest + secret (masked)

6. **JWT**
   - Decode header/payload; pretty-print; verify if key provided; warn on `alg: none` / weak signing

7. **UUID / ULID**
   - Generate v1/v4/v7; ULID; validate & extract timestamps

8. **Time & Dates**
   - Epoch <-> human; add/subtract; RFC3339/ISO-8601; tz convert (zoneinfo)
   - Natural language parse (e.g., "in 2h", "2025-10-31 13:00 GMT+3")

9. **Regex Tester**
   - Run pattern with flags; show first N matches and groups; prevent ReDoS with timeouts

10. **Colors**
    - HEX <-> RGB <-> HSL <-> CMYK; WCAG contrast; random palettes; small swatch PNGs

11. **QR / Barcodes**
    - Generate QR for text/URL/Wi-Fi; size + error-correction options; return PNG

12. **Images (lightweight)**
    - Inspect metadata (format/size/EXIF subset)
    - PNG<->JPG convert; resize (width/height/percent); compress
    - Base64<->image; `Pillow`; enforce `MAX_FILE_MB`

13. **CSV/TSV**
    - Parse; re-delimit; quote normalize; **CSV<->TSV**; stats (rows/cols); to JSON / NDJSON

14. **XML**
    - Pretty/minify; XML<->JSON (best-effort); XPath query (safe subset)

15. **HTML**
    - Minify; prettify; entity encode/decode; strip tags -> text

16. **Code Tools**
    - Formatter/minifier for JSON/CSS/JS; unified diff between two texts
    - Random password/token generator with policy options

> Deterministic, validated behavior with friendly errors is mandatory for all tools.

---

## Bot Commands
```
/start - Open main menu
/help - How to use the bot
/tools - Browse all tools
/recent - Last 10 tasks (per user)
/cancel - Cancel current action
/settings - Personal settings (output format, tz, etc.)
/admin - Admin panel (admins only)
```

### Keyboards
- **Home:** Text -> Data -> Security -> Media -> Web -> Time -> Color -> Admin (if admin)
- **Tool:** Run -> Paste sample -> Switch direction -> Back -> Home

### Input Handling
- Support reply-based and direct commands (e.g., `/base64_encode <text>`).
- Dual-input tools (diff, HMAC) use FSM state per user.
- Files stream to `PERSIST_DIR/users/<uid>/jobs/<job_id>/`.
- Auto-detect content type by MIME + sniffing.

---

## Performance & Safety
- Fully async; offload long tasks to background (`asyncio` or Redis-backed queue when `REDIS_URL` set).
- **Rate limit** per user (configurable) with friendly cooldown responses.
- Enforce input length & file size limits; detect binary vs text.
- Security: no code eval; regex/XPath timeouts; safe temp files; redact secrets in logs.
- Privacy: `/privacy` page; auto-purge temp files older than 24h via scheduled task.

---

## Admin & Observability
- `/admin`: usage stats, top tools, queue depth, storage use.
- `/ping` health check.
- Structured logs with request IDs; (optional) Prometheus metrics.

---

## Testing & CI
- `pytest` unit tests for every utility (happy + edge cases).
- Smoke tests for representative handlers.
- GitHub Actions workflow: lint (`ruff`, `black --check`), tests, build.

---

## Deployment
- Multi-stage Dockerfile (slim image) + `docker-compose.yml` mounting `/data`.
- `.env.example` including all variables.
- `README.md` with quick start, screenshots/GIFs, privacy notes, and DevToys attribution.

---

## Acceptance Stories
- **JSON->YAML:** user sends JSON -> bot returns YAML (code block or `result.yaml` if large).
- **JWT decode/verify:** send token -> show header/payload; optional verify with secret.
- **File SHA-256:** upload file -> stream hash result + downloadable `.txt`.
- **Wi-Fi QR:** guided form -> return PNG.
- **Resize image:** upload JPG -> choose width/height/percent -> send compressed image.
- **CSV->JSON:** upload CSV -> options (header, delimiter) -> return `result.json`.
- **Regex test:** provide pattern + flags + text -> show first 20 matches & groups with timing.

---

## Notes
- This bot is *inspired by* DevToys. Re-implement functionality; do not copy their UI code.
- Prioritize elegance and UX polish throughout.
