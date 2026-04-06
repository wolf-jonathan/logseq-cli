# Contributing to Logseq CLI

Thank you for your interest in contributing. This document covers everything you need to get started.

---


## Prerequisites

- **Python 3.10+**
- **Git**
- **Logseq Desktop** with the HTTP API server enabled (required to run integration tests against a live graph)
- `pip` or `pipx`

---

## Development Setup

### 1. Fork and clone

Fork the repository on GitHub, then clone your fork:

```bash
git clone https://github.com/<your-username>/logseq-cli.git
cd logseq-cli
```

Add the upstream remote so you can pull in future changes:

```bash
git remote add upstream https://github.com/wolf-jonathan/logseq-cli.git
```

### 2. Create a virtual environment

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install with dev dependencies

```bash
pip install -e ".[dev]"
```

### 4. Configure the API token

Copy the example env file and fill in your Logseq API token:

```bash
cp .env.example .env
# edit .env and set LOGSEQ_TOKEN=your-token-here
```

Verify the connection:

```bash
logseq graph info
```

---

## Making Changes

### Branch naming

Create a branch off `main` for every change. Use a short, descriptive name with a prefix that reflects the type of work:

| Prefix | Use for |
|--------|---------|
| `feat/` | New commands or capabilities |
| `fix/` | Bug fixes |
| `refactor/` | Internal restructuring without behavior change |
| `docs/` | Documentation-only changes |
| `test/` | Test additions or fixes |
| `chore/` | Dependency bumps, tooling, CI |

Examples:

```bash
git checkout -b feat/block-search
git checkout -b fix/stdin-empty-input
git checkout -b docs/update-query-examples
```

### Workflow

1. Sync with upstream before starting:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
2. Make your changes in small, focused commits (one logical change per commit).
3. Run the test suite before pushing — see [Running Tests](#running-tests).
4. Push to your fork and open a pull request against `main`.

### Commit messages

Write commit messages in the imperative mood, present tense:

```
add block search command
fix stdin parsing on empty input
update README with new query examples
```

Keep the subject line under 72 characters. Add a body if the change needs context beyond what the subject conveys.

### Pull requests

- Keep PRs focused on a single concern. Split unrelated changes into separate PRs.
- Reference the relevant issue in the PR description (e.g. `Closes #42`).
- Describe *what* changed and *why* — not just what the diff shows.
- All tests must pass before a PR can be merged.

---

## Code Guidelines

### General

- Follow the existing module structure: thin HTTP client → service layer → CLI commands.
- Keep CLI modules (`src/cli/*.py`) free of business logic — delegate to `logseq_service.py`.
- Use `async`/`await` in the client and service layers; wrap with `asyncio.run` at the CLI boundary only.
- Errors go to **stderr**; stdout is reserved for data. Use `handle_errors()` in CLI commands.
- Output via `format_output()` — do not write to stdout directly in command handlers.

### Style

- Python standard style (PEP 8). No formatter is enforced yet, but keep lines under 100 characters.
- Name CLI commands as `noun verb` (e.g. `page get`, `block insert`).
- NDJSON is the default output format; `--plain` and `--fields` are standard options on all data-returning commands.

### Unsupported API methods

If you discover that a Logseq HTTP API method does not work against a real running instance, do not leave it documented as supported:

1. Add an entry to `UNSUPPORTED-LOGSEQ-HTTP-METHODS.md` with the method name, date discovered, reproduction steps, and the exact server error.
2. Remove or replace any CLI command, test, or documentation that claims the method works.

---

## Running Tests

```bash
# Run all tests
pytest --tb=short

# Run a specific module
pytest tests/test_page.py --tb=short

# Run tests matching a keyword
pytest -k "test_block" --tb=short
```

Tests use mocked HTTP responses and do not require Logseq to be running. If you add a new command, add corresponding tests in the relevant `tests/test_*.py` file.

---

## Reporting Bugs

Open an issue on GitHub and include:

- **What you did** — the exact command you ran
- **What you expected** — the output or behavior you anticipated
- **What happened** — the actual output, including any error messages from stderr
- **Environment** — OS, Python version (`python --version`), Logseq version

Use the `bug` label when filing.

---

## Requesting Features

Open an issue on GitHub with:

- **The problem you want to solve** — describe the use case, not just the solution
- **What you would expect the CLI to do** — example commands and output if possible
- **Alternatives you have considered**

Use the `enhancement` label when filing.

For larger changes (new subcommand groups, breaking output format changes, etc.), open an issue to discuss the approach before writing code. This avoids wasted effort if the direction doesn't fit the project.
