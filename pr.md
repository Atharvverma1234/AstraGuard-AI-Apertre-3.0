# PR: Create troubleshooting script (closes #706)

## Summary

Adds a practical, developer-facing troubleshooting script (`scripts/troubleshoot.py`) that helps quickly diagnose common setup and runtime issues in the AstraGuard AI project.

## What it does

The script runs **11 independent checks** and prints a clear pass/fail summary:

| Check | What it verifies |
|-------|-----------------|
| `python` | Python ≥ 3.9 is installed |
| `node` | Node.js and npm are available (needed for frontend) |
| `deps` | Core Python packages (`numpy`, `fastapi`, `redis`, etc.) are importable |
| `env` | A `.env` or `.env.local` file exists, with key variables defined |
| `ports` | Common service ports (8000, 8002, 3000, 8501, 6379) are not already occupied |
| `redis` | Redis is reachable on the configured host/port |
| `docker` | Docker & Docker Compose are installed and the daemon is running |
| `dirs` | Essential project directories (`src/`, `tests/`, `docs/`, etc.) exist |
| `resources` | Disk space and available memory are sufficient |
| `config` | Key config files (`requirements.txt`, `pyproject.toml`, `package.json`) exist |
| `permissions` | Key directories are writable |

## Usage

```bash
# Run all checks
python scripts/troubleshoot.py

# Run a single check
python scripts/troubleshoot.py --check env

# Auto-fix what can be fixed (e.g. copy .env.example → .env)
python scripts/troubleshoot.py --fix
```

### Exit codes

- `0` — all checks passed
- `1` — one or more checks failed (details in output)

## Design decisions

- **Single file, zero external dependencies** — uses only the Python stdlib (plus optional `psutil` if installed). Runs before any project dependencies are installed.
- **Lives in `scripts/`** — consistent with the existing script layout (`scripts/maintenance/verify_install.py`, `scripts/maintenance/build.py`, etc.).
- **Actionable output** — every failure includes a concrete "what to do" hint (install command, config path, link to docs).
- **`--fix` flag** — auto-fixes trivial issues (currently: copies `.env.example` → `.env`). Safe to extend later.
- **`--check` flag** — lets developers run a single check without waiting for the full suite.
- **Python 3.9+ compatible** — uses `Optional[str]` instead of `str | None` to stay compatible with the project's minimum Python version.

## Files changed

| File | Change |
|------|--------|
| `scripts/troubleshoot.py` | **New** — troubleshooting script |
| `pr.md` | **New** — this PR description |

## Testing

The script was manually tested with:
- `--check python`, `--check dirs`, `--check ports`, `--check env` (individual checks)
- `--fix` (auto-creates `.env` from template)
- `--help` (shows usage)
- Full run (all 11 checks, correct exit code)

## Category

`dev-experience` — as specified in the roadmap issue.

## Closes

Closes #706
