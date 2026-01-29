# codeshard

`codeshard` manages Git worktrees as disposable AI coding sandboxes. It is designed to be run from an anchor clone and creates sibling worktree directories for isolated sessions.

## Requirements

- Python 3.12+
- macOS or Linux

## Install (local dev)

```bash
uv run codeshard --help
```

## Usage

```bash
uv run codeshard new ABC-123
uv run codeshard new ABC-123 --open-ide --ide-cmd 'code "{path}"'
uv run codeshard new ABC-123 --open-ai --ai-cmd 'wezterm start --cwd "{path}" -- codex'
uv run codeshard ls
uv run codeshard rm ABC-123
uv run codeshard rm ABC-123 --delete-branch
uv run codeshard config set ide_cmd 'code "{path}"'
uv run codeshard config set ai_cmd 'codex'
uv build
```

Tip: if you want a shorter command, you can add `alias cs="codeshard"` to your shell profile.

## Behavior

- The anchor repo is discovered via `git rev-parse --show-toplevel` (or `--repo`).
- Worktrees live under a sibling directory: `<anchor_parent>/<anchor_name>-wt`, unless overridden by `--root` or `WT_ROOT`.
- `codeshard new` defaults its base ref to the current branch of the anchor repo.

## Configuration

Config is stored in:

- `$XDG_CONFIG_HOME/codeshard/config.toml` if `XDG_CONFIG_HOME` is set
- otherwise `~/.config/codeshard/config.toml`

Config keys:

- `ide_cmd`: command template to open an IDE at `{path}`
- `ai_cmd`: command template to launch an AI tool (uses `{path}` if present, otherwise relies on `cwd`)
- `ide_enabled_default`: default for `--open-ide`
- `ai_enabled_default`: default for `--open-ai`
- `allow_shell`: opt-in to execute IDE/AI commands through a shell (default false)

Environment variables override config:

- `CODESHARD_IDE_CMD`
- `CODESHARD_AI_CMD`

### Recommended command templates

IDE command examples (must include `{path}`):

- VS Code: `code "{path}"`
- Cursor: `cursor "{path}"`
- IntelliJ IDEA: `idea "{path}"`

AI command examples (may include `{path}`; otherwise uses the worktree as `cwd`):

- Simple CLI in current terminal: `codex`
- WezTerm (new window): `wezterm start --cwd "{path}" -- codex`
- Kitty (new window): `kitty --directory "{path}" codex`
- macOS Terminal (new window): `open -a Terminal "{path}"`
- macOS iTerm (new window): `open -a iTerm "{path}"`

Tip: If you want a new tab instead of a new window, use your terminal's CLI flags in `ai_cmd` (terminal-specific).

## Using codeshard with Codex

1) Create a shard: `uv run codeshard new MY-TASK`
2) `cd` into it
3) Run your AI tool (e.g. `codex`)
4) Remove the shard when finished: `uv run codeshard rm MY-TASK`
