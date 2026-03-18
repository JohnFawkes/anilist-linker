# CLAUDE.md — Anilist Linker

## Project Overview

**Anilist Linker** — A Python automation script that enriches Plex Media Server anime libraries with Anilist metadata. It cross-references external IDs (TMDB, TVDB, IMDb) against the Kometa Anime-IDs database to find matching Anilist entries, then prepends Anilist URLs to Plex item summaries.

Flow: `Plex Library → fetch items → match IDs → Anilist GraphQL API → update Plex summaries`

## Running the App

```bash
# Recommended: Docker Compose
docker compose up -d

# Python directly (one-shot or with -y to skip confirmation)
python anilist_linker.py
python anilist_linker.py -y  # bypass confirmation prompt
```

Copy `.env.example` to `.env` and fill in values before running.

## Key Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `PLEX_URL` | yes | `YOUR_PLEX_URL` | Plex server address |
| `PLEX_TOKEN` | yes | `YOUR_PLEX_TOKEN` | Plex auth token |
| `PLEX_MAKE_CHANGES` | no | `False` | Set `True` to write changes (dry run by default) |
| `PLEX_DEBUG` | no | `False` | Enable verbose debug logging |
| `PLEX_LOG_PATH` | no | `./logs` | Directory for log files |
| `PLEX_TARGET_TV_SHOW_LIBRARIES` | no | — | Comma-separated Plex TV library names to target |
| `PLEX_TARGET_MOVIE_LIBRARIES` | no | — | Comma-separated Plex movie library names to target |
| `CRON_SCHEDULE` | no | — | Cron expression for scheduled runs (e.g. `0 3 * * *`) |
| `FORCE_RUN_ON_START` | no | `False` | Set `True` to run immediately on container start |
| `ANIME_IDS_JSON_URL` | no | Kometa GitHub URL | Source for anime ID mapping data |
| `ANILIST_API_URL` | no | `https://graphql.anilist.co` | Anilist GraphQL endpoint |
| `ANILIST_PREFIX_FORMAT` | no | `[Anilist: {anilist_url}]\n` | Format string for prepended prefix |

Full reference in README.md and `.env.example`.

## Project Structure

```
anilist_linker.py       Main script (Plex + Anilist integration logic)
requirements.txt        Python dependencies (plexapi, requests, python-dotenv)
compose.yaml            Docker Compose config (pulls from ghcr.io)
compose-dev.yaml        Docker Compose for local development (builds from source)
.env.example            Environment variable template
Docker/
  Dockerfile            Python 3.11-slim image, non-root appuser (uid 1001)
  start.sh              Entrypoint: optional immediate run + supercronic cron scheduler
```

## Key Internals

- **ID matching priority:** TMDB → TVDB → IMDb
- **Anilist rate limiting:** 1 call per 2 seconds, with reactive backoff on 429 responses
- **Dry run mode:** `PLEX_MAKE_CHANGES=False` previews changes without writing to Plex
- **Duplicate prevention:** Checks for existing `[Anilist: ...]` prefix before updating
- **Unmatched tracking:** Items with no Anilist match are collected and reported at the end
- **Supercronic:** Used for container-native cron scheduling (no root required)

## Dependencies

```bash
pip install -r requirements.txt
# plexapi, requests, python-dotenv
```

## No Tests

There is no automated test suite. Validate changes by running with `PLEX_MAKE_CHANGES=False` first to preview what would be updated.

## Docker

```bash
docker build -f Docker/Dockerfile -t anilist-linker .
docker compose up -d
```

- Non-root user `appuser` (uid 1001)
- Log volume: `./logs:/app/logs`
- No web server — runs as a scheduled script via supercronic

## CI/CD

GitHub Actions workflow (`.github/workflows/docker-ci.yml`):

1. **Triggers:** Push to `main` or PR against `main` (only when `.github/`, `Docker/Dockerfile`, `anilist_linker.py`, or `requirements.txt` change)
2. **Build:** Docker image built with BuildX and GHA cache
3. **Version:** Auto semantic version bump on push to main
4. **Release:** GitHub Release created with changelog
5. **Security:** Trivy vulnerability scan (CRITICAL/HIGH) with SARIF upload
6. **Publish:** Image pushed to `ghcr.io/johnfawkes/anilist-linker`

Note: No container startup test — this is a cron script, not a web server.
