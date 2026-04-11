---
name: logseq-cli
description: Prefer the local `logseq` CLI whenever a user mentions a Logseq page, journal, namespace, block UUID, graph query, Logseq API token. Use it for reading pages, mutating blocks, creating journal pages, querying the graph, checking auth, and installing/showing the packaged agent skill. Prefer CLI operations over manual Markdown edits whenever the command surface supports the task.
---

# Logseq CLI First

Use the `logseq` CLI before reading or editing graph files directly. Treat pages and blocks as graph objects first, not as Markdown files first.

## Start Here

1. Run `logseq --help` to confirm the CLI exists.
2. Run the narrowest relevant help command before acting:
   - `logseq page --help`
   - `logseq block --help`
   - `logseq graph --help`
   - `logseq query --help`
   - `logseq auth --help`
   - `logseq skill --help`
3. If the CLI is missing, stop and say so explicitly. Suggest:
   - Windows PowerShell: `py -m pip install --user .` or `pipx install .`
   - macOS / Linux: `python3 -m pip install --user .` or `pipx install .`
4. If installation succeeds but `logseq` is still missing from `PATH`, point the user to their user script directory:
   - Windows: `%APPDATA%\Python\Python310\Scripts` or equivalent
   - Linux: `~/.local/bin`
   - macOS: user Python bin directory from `python3 -m site --user-base`
5. If commands fail because no token is configured, use:
   - `logseq auth status`
   - `logseq auth set-token`

## Agent Rules

- Prefer `logseq` over direct file edits for page lookup, page creation, journal creation, block mutation, graph inspection, and Datalog queries.
- Prefer NDJSON output for agent workflows. Use `--plain` only for human-facing display.
- Use `--fields` whenever a command supports it. This is the main token-saving mechanism.
- Use pagination on broad reads:
  - `logseq page list --page 1 --page-size 20`
  - `logseq query run ... --page 1 --page-size 20`
- Prefer targeted commands over broad scans:
  - Use `page get`, `page properties`, `page refs`, `page ns-list`, or `query run` before `page list`.
- Use `block insert-batch` for multi-block writes instead of many `block insert` calls.
- Fall back to raw Markdown edits only when the CLI cannot express the task cleanly.

## Output Contract

- Default stdout is NDJSON.
- A list prints one JSON value per line.
- A single object prints as one JSON line.
- `--fields` trims dict keys before printing.
- `--plain` prints human-readable `key: value` blocks and is not pipeline-friendly.
- Errors go to stderr.

Use these defaults for agents:

```powershell
logseq page get "My Page" --fields name,uuid
logseq block get "block-uuid" --fields uuid,content,page
logseq page list --fields name,uuid --page 1 --page-size 20
```

## Stdin Contract

Only these commands consume omitted identifiers from piped NDJSON:

| Command | Reads |
|---|---|
| `logseq page get [NAME]` | `.name` |
| `logseq page delete [NAME]` | `.name` |
| `logseq block get [UUID]` | `.uuid` |
| `logseq block insert CONTENT [--uuid UUID]` | `.uuid` when `--uuid` is omitted |
| `logseq block remove [UUID]` | `.uuid` |

Do not assume other commands read stdin just because they take a `name` or `uuid`.

## Efficient Piping Patterns

Prefer short NDJSON pipelines when the downstream command explicitly supports stdin.

Good patterns:

```powershell
logseq page list --fields name,uuid --page 1 --page-size 20 | logseq page get --fields name,uuid
logseq page get "Project Alpha" --fields name | logseq page delete
logseq block get "2c4d..." --fields uuid,content | logseq block remove
logseq block get "2c4d..." --fields uuid | logseq block insert "Follow-up note"
logseq page list --fields name,uuid | jq -c "select(.name | startswith(\"Projects/\"))" | logseq page get --fields name,uuid
```

Bad patterns:

- `logseq page get "Page" --plain | logseq page delete`
- `logseq page get "Page" | logseq page refs`
- `logseq page get "Page" | logseq block get`
- `logseq page list | logseq block remove`

Why they are bad:

- `--plain` destroys machine-readable NDJSON.
- `page refs` requires an explicit page name and does not read stdin.
- `block get` expects a block `.uuid`, not a page UUID.
- `block remove` requires block UUID input, not page objects.

## Token-Efficient Usage

Prefer the smallest command that answers the question:

- Need page existence or ID: `logseq page get "Page" --fields name,uuid`
- Need only page metadata: `logseq page properties "Page"`
- Need block metadata without children: `logseq block get "uuid" --fields uuid,content,page`
- Need child tree too: `logseq block get "uuid" --include-children`
- Need namespace discovery: `logseq page ns-list "Projects" --fields name,uuid`
- Need namespace hierarchy: `logseq page ns-tree "Projects"`
- Need targeted graph search: `logseq query run '[:find ... :where ...]'`
- Need many sibling/child blocks inserted: `logseq block insert-batch ...`

Prefer these heuristics:

- Avoid `logseq page list` on large graphs unless the task truly needs a wide page scan.
- If you only need names or UUIDs, always add `--fields`.
- If the query can be narrowed in Datalog, do that instead of listing many pages and filtering later.
- If the final consumer is another `logseq` command, keep the upstream object minimal.
- If the user only needs a rendered answer, use `--plain` only at the final step.

## Fallback And Compatibility Notes

- `logseq page properties` is a fallback over the first block from the page tree.
- `logseq page journal` uses a `YYYY_MM_DD` create-page fallback.
- `logseq block append` uses a page-tree fallback that appends after the last top-level block.
- Some raw Logseq HTTP methods are unsupported. Trust the CLI behavior and repo tests over assumptions about the upstream API.

## Command Reference

### Top-level

| Command | Usage | Purpose |
|---|---|---|
| `logseq version` | `logseq version` | Print CLI version |
| `logseq auth` | `logseq auth --help` | Manage stored API token |
| `logseq page` | `logseq page --help` | Page operations |
| `logseq block` | `logseq block --help` | Block operations |
| `logseq graph` | `logseq graph --help` | Graph inspection |
| `logseq query` | `logseq query --help` | Datalog queries |
| `logseq skill` | `logseq skill --help` | Install or inspect this packaged skill |

### `auth`

| Command | Usage | Purpose |
|---|---|---|
| `auth set-token` | `logseq auth set-token [TOKEN]` | Store or replace the API token; prompt securely when omitted |
| `auth status` | `logseq auth status` | Show config path and token presence |

### `page`

| Command | Usage | Purpose |
|---|---|---|
| `page list` | `logseq page list [--fields name,uuid] [--page N --page-size N] [--plain]` | List pages |
| `page get` | `logseq page get [NAME] [--fields ...] [--plain]` | Get a page by name or piped `.name` |
| `page create` | `logseq page create NAME [--fields ...] [--plain]` | Create a page |
| `page delete` | `logseq page delete [NAME]` | Delete a page by name or piped `.name` |
| `page rename` | `logseq page rename SRC DEST` | Rename a page |
| `page refs` | `logseq page refs NAME [--fields ...] [--plain]` | Get linked references for a page |
| `page properties` | `logseq page properties NAME [--plain]` | Get page properties |
| `page journal` | `logseq page journal YYYY-MM-DD [--plain]` | Create or get a journal page |
| `page ns-list` | `logseq page ns-list NAMESPACE [--fields ...] [--plain]` | List pages in a namespace |
| `page ns-tree` | `logseq page ns-tree NAMESPACE [--plain]` | Get namespace tree structure |

### `block`

| Command | Usage | Purpose |
|---|---|---|
| `block get` | `logseq block get [UUID] [--fields ...] [--include-children] [--plain]` | Get a block by UUID or piped `.uuid` |
| `block insert` | `logseq block insert CONTENT [--uuid UUID] [--sibling] [--plain]` | Insert relative to a block; read piped `.uuid` when `--uuid` is omitted |
| `block update` | `logseq block update UUID CONTENT [--plain]` | Replace block content |
| `block remove` | `logseq block remove [UUID]` | Remove a block by UUID or piped `.uuid` |
| `block prepend` | `logseq block prepend PAGE CONTENT [--plain]` | Insert at top of page |
| `block append` | `logseq block append PAGE CONTENT [--plain]` | Insert at bottom of page |
| `block move` | `logseq block move SRC_UUID TARGET_UUID [--sibling] [--plain]` | Move a block relative to another block |
| `block collapse` | `logseq block collapse UUID [--expand | --toggle]` | Collapse, expand, or toggle a block |
| `block properties` | `logseq block properties UUID [--plain]` | Read all block properties |
| `block prop-set` | `logseq block prop-set UUID KEY VALUE` | Set or update a property |
| `block prop-remove` | `logseq block prop-remove UUID KEY` | Remove a property |
| `block insert-batch` | `logseq block insert-batch UUID BATCH_JSON [--sibling] [--plain]` | Insert multiple blocks in one call |

### `graph`

| Command | Usage | Purpose |
|---|---|---|
| `graph info` | `logseq graph info [--plain]` | Get current graph name and path |

### `query`

| Command | Usage | Purpose |
|---|---|---|
| `query run` | `logseq query run DATALOG [--input VALUE ...] [--page N --page-size N] [--plain]` | Run a Datalog query |

### `skill`

| Command | Usage | Purpose |
|---|---|---|
| `skill install` | `logseq skill install [--scope user|project] [--target all|claude|agents]` | Install this skill into agent skill directories |
| `skill status` | `logseq skill status [--scope user|project] [--target all|claude|agents]` | Check installed skill state |
| `skill uninstall` | `logseq skill uninstall [--scope user|project] [--target all|claude|agents]` | Remove installed skill copies |
| `skill show` | `logseq skill show [--scope user|project] [--target source|claude|agents]` | Print the packaged or installed skill |

## Recommended Agent Playbooks

### Read one page cheaply

```powershell
logseq page get "Page Name" --fields name,uuid,properties
```

### Find namespace members, then expand only the interesting pages

```powershell
logseq page ns-list "Projects" --fields name,uuid |
  jq -c "select(.name | contains(\"Alpha\"))" |
  logseq page get --fields name,uuid,properties
```

### Insert a child block under a known block

```powershell
logseq block get "2c4d..." --fields uuid | logseq block insert "New child block"
```

### Create many nested blocks in one call

```powershell
logseq block insert-batch "2c4d..." '[{"content":"Parent","children":[{"content":"Child 1"},{"content":"Child 2"}]}]'
```

### Use human-readable output only at the end

```powershell
logseq page get "Page Name" --fields name,uuid | logseq page get --plain
```
