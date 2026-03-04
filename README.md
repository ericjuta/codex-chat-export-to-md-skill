# codex-chat-export

Export a Codex CLI session from `~/.codex/sessions/*.jsonl` into a clean Markdown transcript.

## What it does

- Exports only `user` and `assistant` messages by default.
- Selects the current session from `CODEX_THREAD_ID` when available.
- Falls back to the newest `rollout-*.jsonl` session file when no thread id is provided.
- Writes output to:
  - `specs/standup/` if present
  - otherwise `specs/`
  - otherwise the current directory

## Usage

Run from the repository root:

```bash
python3 .agents/skills/codex-chat-export/scripts/export_codex_chat_to_md.py --ascii-only
```

The command prints the output Markdown path to stdout.

## Common options

- `--thread-id <id>`: Export a specific session by thread id.
- `--session-jsonl <path>`: Export from an explicit JSONL file.
- `--out <path>`: Write to a specific Markdown file.
- `--include-developer`: Include `developer` role messages.
- `--ascii-only`: Replace non-ASCII characters with `?`.

## Quick check

```bash
sed -n '1,80p' <exported-file>
```

## Safety

- Review and redact sensitive content before sharing transcripts.
- Tool logs are excluded by default because they can include secrets.
