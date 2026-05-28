---
name: xiaomi-cli
description: Use this skill whenever the user wants to manage Xiaomi Cloud Notes or Todo items through the local `xiaomi-cli` project in this workspace, including creating, listing, updating, deleting, syncing notes, or setting Todo reminder times. This skill should also trigger when the user mentions 小米云笔记、小米待办、提醒时间、`remind-at`, `remind-in`, CRUD 操作, or asks to use the CLI instead of browser automation.
---

# Xiaomi CLI

Use this skill to operate the Xiaomi Cloud Notes / Todo CLI in this repository.

The goal is to prefer the local CLI over browser-side ad hoc actions whenever the user asks to create, edit, delete, list, or sync Xiaomi notes and todos.

## What this skill is for

Use this skill when the user wants to:

- manage Xiaomi notes from the terminal
- manage Xiaomi todo items from the terminal
- create, edit, delete, or inspect notes / todos
- set todo reminder times
- use relative reminder time such as `5分钟后` or `1h`
- trigger sync-related actions

Do not use this skill when the user is asking to reverse-engineer a new Xiaomi endpoint from scratch. In that case, inspect the browser/network flow first and then come back here if CLI changes are needed.

## Project assumptions

- Repo root: current repository root
- Main command: `uv run xiaomi-cli`
- Authentication config path: user-local config, inspect with `uv run xiaomi-cli auth show-path`
- The current CLI uses browser cookie-based auth

## Core workflow

1. Work from the repo root of this repository
2. Prefer `uv run xiaomi-cli ...`
3. If the command fails with `401 Unauthorized`, assume the cookie expired
4. If auth is missing, guide the user to refresh the cookie or pass `--cookie` / `--cookie-file`
5. After `note update`, remember that the server may return a new `tag`
6. After `todo update`, remember that the server may return a new `eTag`

## Authentication

Check whether the user-local auth config exists before asking the user for cookies. Prefer checking it via:

```bash
uv run xiaomi-cli auth show-path
```

If auth is missing, use one of these:

- `uv run xiaomi-cli auth save`
- `uv run xiaomi-cli ... --cookie '...'`
- `uv run xiaomi-cli ... --cookie-file ./xiaomi.cookie`

If the user asks you to save a provided cookie, write it into the config file and then continue with CLI execution.

## Command patterns

### Notes

List notes:

```bash
uv run xiaomi-cli note list
```

Get one note:

```bash
uv run xiaomi-cli note get <note_id>
```

Create a note:

```bash
uv run xiaomi-cli note create --content '正文内容'
```

Update a note:

```bash
uv run xiaomi-cli note update <note_id> \
  --tag <current_tag> \
  --title '标题' \
  --content '新的正文'
```

Delete a note:

```bash
uv run xiaomi-cli note delete <note_id> --tag <current_tag>
```

### Todos

List todos:

```bash
uv run xiaomi-cli todo list
```

Get one todo:

```bash
uv run xiaomi-cli todo get <record_id>
```

Create a todo:

```bash
uv run xiaomi-cli todo create --title '待办标题'
```

Create a todo with absolute reminder time:

```bash
uv run xiaomi-cli todo create \
  --title '明早开会' \
  --remind-at '2026-05-29 09:30' \
  --repeat none
```

Create a todo with relative reminder time:

```bash
uv run xiaomi-cli todo create \
  --title '10分钟后提醒我' \
  --remind-in '10分钟后' \
  --repeat none
```

Short relative format is also supported:

```bash
uv run xiaomi-cli todo create \
  --title '1小时后提醒我' \
  --remind-in '1h' \
  --repeat none
```

Update a todo:

```bash
uv run xiaomi-cli todo update <record_id> \
  --e-tag <current_etag> \
  --title '新的标题' \
  --remind-in '1d' \
  --repeat none
```

Finish / unfinish:

```bash
uv run xiaomi-cli todo finish <record_id> --e-tag <current_etag>
uv run xiaomi-cli todo unfinish <record_id> --e-tag <current_etag>
```

Delete:

```bash
uv run xiaomi-cli todo delete <record_id> --e-tag <current_etag>
```

### Sync

```bash
uv run xiaomi-cli sync notes
uv run xiaomi-cli sync index-check
uv run xiaomi-cli sync index-update
```

## Reminder rules

`--remind-at` and `--remind-in` are mutually exclusive. Never pass both at the same time.

Supported `--remind-in` formats:

- Chinese natural format:
  - `5分钟后`
  - `2小时后`
  - `1天后`
  - `30秒后`
  - `1周后`
- Short format:
  - `1m`
  - `1h`
  - `1d`
  - `1s`
  - `1w`

Supported repeat values:

- `none`
- `daily`
- `weekly`
- `weekday`
- `monthly`
- `yearly`

If the user asks for “10 分钟后提醒我”, prefer:

```bash
uv run xiaomi-cli todo create \
  --title '...' \
  --remind-in '10分钟后' \
  --repeat none
```

## Expected outputs

Prefer returning:

- the exact command you ran when useful
- the created / updated `id`
- the latest `tag` or `eTag` if it changed
- the resolved reminder time if the user used relative time
- any `401` / auth failure clearly and briefly

## Failure handling

If a command fails:

- `401 Unauthorized`: cookie expired or invalid
- note delete conflict: retry with the newest `tag`
- todo delete/update conflict: retry with the newest `eTag`

When a retry is needed, explain why in one sentence and then run the corrected command.

## Verification

After changing data, verify with the most relevant follow-up command:

- note create/update: `note get`
- todo create/update: `todo get` or `todo list`
- sync commands: inspect returned JSON

## References

Primary project docs:

- `README.md`
- `src/xiaomi_cli/cli.py`
