# logseq-cli

A Python CLI that wraps the Logseq local HTTP API, exposing its capabilities as Unix-composable commands.

---

## Project Overview

**Goal:** A `logseq` CLI command that wraps the Logseq local HTTP API — LLM-optimized, Unix-composable, noun-verb structured.

**Stack:**
- Language: Python 3.10+
- CLI framework: `typer`
- HTTP client: `httpx` (async, wrapped with `asyncio.run` at CLI boundary)
- Config: user-level stored auth token
- Test framework: `pytest` + `pytest-asyncio`
- Logseq HTTP API: local server (default port 12315)

---

## Architecture

```
src/
  logseq_client.py    # HTTP client — thin wrapper around httpx.AsyncClient
  logseq_service.py   # Service layer — async methods over logseq_client
  config.py           # User config path + stored auth profile management
  cli/
    main.py           # Typer app entry point, get_service(), handle_errors()
    auth.py           # auth subcommand group
    output.py         # format_output(data, fields, plain) — NDJSON or plain text
    stdin.py          # read_stdin_field(field) — reads NDJSON lines from stdin
    page.py           # page subcommand group
    block.py          # block subcommand group
    graph.py          # graph subcommand group
    query.py          # query subcommand group
tests/
  conftest.py
  test_output.py
  test_stdin.py
  test_page.py
  test_block.py
  test_graph.py
  test_query.py
  test_errors.py
  test_entrypoint.py
```

---

## Logseq API

- Logseq must be running with the HTTP API server enabled
- Default base URL: `http://127.0.0.1:12315/api`
- Requests are POST with JSON body: `{ "method": "...", "args": [...] }`
- Token resolved from `LOGSEQ_TOKEN` or the stored CLI auth token

---

## Build & Run

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run CLI
logseq --help

# Run tests
pytest --tb=short
```

---

## CLI Commands

### auth

| Command | Args | Notes |
|---------|------|-------|
| `auth set-token [token]` | | Stores or replaces the token; prompts securely if `token` is omitted |
| `auth status` | | Shows config path and whether a token is stored |

### top-level

| Command | Notes |
|---------|-------|
| `version` | Prints the current CLI version |

### page

| Command | Args | Notes |
|---------|------|-------|
| `page list` | `--fields`, `--plain`, `--page`, `--page-size` | Lists all pages; auto-paginated with `--page` |
| `page get [name]` | `--fields`, `--plain` | Auto-stdin: reads `.name` from piped NDJSON |
| `page create <name>` | `--fields`, `--plain` | |
| `page delete [name]` | | Auto-stdin: reads `.name` from piped NDJSON |
| `page rename <src> <dest>` | | |
| `page refs <name>` | `--fields`, `--plain` | Linked references |
| `page properties <name>` | `--plain` | Derived from the first block in the page tree |
| `page journal <date>` | `--plain` | Creates/gets a journal via `createPage(YYYY_MM_DD)` fallback |
| `page ns-list <namespace>` | `--fields`, `--plain` | Pages under a namespace |
| `page ns-tree <namespace>` | `--plain` | Namespace as nested tree |

### block

| Command | Args | Notes |
|---------|------|-------|
| `block get [uuid]` | `--fields`, `--include-children`, `--plain` | Auto-stdin: reads `.uuid` |
| `block insert <content>` | `--uuid`, `--sibling`, `--plain` | Auto-stdin: reads `.uuid`; default inserts as child |
| `block update <uuid> <content>` | `--plain` | |
| `block remove [uuid]` | | Auto-stdin: reads `.uuid` |
| `block prepend <page> <content>` | `--plain` | Prepend to top of page |
| `block append <page> <content>` | `--plain` | Append via page-tree fallback |
| `block move <src_uuid> <target_uuid>` | `--sibling`, `--plain` | Default: move as child |
| `block collapse <uuid>` | `--expand`, `--toggle` | Collapse/expand/toggle |
| `block properties <uuid>` | `--plain` | |
| `block prop-set <uuid> <key> <value>` | | Upsert a block property |
| `block prop-remove <uuid> <key>` | | Remove a block property |
| `block insert-batch <uuid> <json>` | `--sibling`, `--plain` | JSON array with `content` + optional `children` |

### graph

| Command | Notes |
|---------|-------|
| `graph info` | Returns current graph name/path |

### query

| Command | Args | Notes |
|---------|------|-------|
| `query run <datalog>` | `--plain`, `--page`, `--page-size`, `--input` | `--input` repeatable for parameterized queries |

---

## Conventions

- NDJSON output by default — one JSON object per line, pipe-safe
- Errors go to stderr; stdout stays clean (safe for piping)
- Auto-stdin: commands that accept `name`/`uuid` read from piped NDJSON when no arg given
- `--fields name,uuid` filters output to specific keys (token-efficient for LLMs)
- `--plain` outputs `key: value` pairs instead of JSON
- When adding a new command or changing an existing command, update the README in the same task.
- When adding a new command or changing an existing command, verify it appears in the CLI help output in the same task.
- When making a code or release-relevant behavior change, also increment the version in `pyproject.toml`.
- Do not bump the version for documentation-only, comment-only, or other non-code changes.
- Use semantic versioning for that bump unless the user asks otherwise:
  - patch (`0.1.1`) for bug fixes and compatible maintenance work
  - minor (`0.2.0`) for new backward-compatible features
  - major (`1.0.0`) for breaking changes

---

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project config; entry point: `logseq = "src.cli.main:app"` |
| `src/logseq_client.py` | HTTP client (`LogseqClient`) |
| `src/logseq_service.py` | Service layer (`LogseqService`) |
| `src/cli/main.py` | CLI entry point, `get_service()`, `handle_errors()` |
| `src/cli/output.py` | `format_output(data, fields, plain)` |
| `src/cli/stdin.py` | `read_stdin_field(field)` |

---

## Workflow Files

### TODO.md
Maintains a prioritized list of work items.

**Format:**
- `- [ ]` / `- [x]` for task status
- Group under descriptive headers
- Priority prefixes: `[HIGH]`, `[MEDIUM]`, `[LOW]`

## Unsupported Method Tracking

Maintain `UNSUPPORTED-LOGSEQ-HTTP-METHODS.md` as the ledger of live-tested
Logseq HTTP methods that turned out to be unsupported.

When a method fails against a real running Logseq server because it does not
exist or is unsupported:

- add an entry to `UNSUPPORTED-LOGSEQ-HTTP-METHODS.md`
- include the exact method name
- include the date discovered
- include the exact command or reproduction steps
- include the returned server error
- update the CLI, tests, and docs so the repo stops claiming that method works

Do not leave disproven HTTP methods documented as supported.
