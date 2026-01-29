from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib
from typing import Any

from . import git


@dataclass(frozen=True)
class Config:
    ide_cmd: str
    ai_cmd: str
    ide_enabled_default: bool
    ai_enabled_default: bool
    allow_shell: bool


DEFAULT_CONFIG = Config(
    ide_cmd="",
    ai_cmd="",
    ide_enabled_default=False,
    ai_enabled_default=False,
    allow_shell=False,
)


def get_config_file_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        base_path = Path(base)
    else:
        base_path = Path.home() / ".config"
    return base_path / "codeshard" / "config.toml"


def load_config_file() -> dict[str, Any]:
    path = get_config_file_path()
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text())


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\"", "\\\"")


def write_config_file(data: dict[str, Any]) -> None:
    path = get_config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for key in sorted(data.keys()):
        value = data[key]
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = f"\"{_toml_escape(str(value))}\""
        lines.append(f"{key} = {rendered}")
    path.write_text("\n".join(lines) + "\n")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    raise ValueError(f"Invalid boolean value: {value}")


def resolve_repo_root(repo: Path | None, cwd: Path) -> Path:
    repo_cwd = cwd if repo is None else Path(repo).expanduser()
    return git.get_repo_root(repo_cwd)


def default_worktrees_root(repo_root: Path) -> Path:
    return repo_root.parent / f"{repo_root.name}-wt"


def resolve_worktrees_root(repo_root: Path, cli_root: Path | None, env_root: str | None) -> Path:
    if cli_root is not None:
        return Path(cli_root).expanduser()
    if env_root:
        return Path(env_root).expanduser()
    return default_worktrees_root(repo_root)


def resolve_target_path(name: str, worktrees_root: Path, cli_path: Path | None) -> Path:
    if cli_path is not None:
        return Path(cli_path).expanduser()
    return worktrees_root / name


def resolve_config(
    cli_overrides: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
    config_data: dict[str, Any] | None = None,
) -> tuple[Config, dict[str, str]]:
    sources: dict[str, str] = {}
    env = env or os.environ
    config_data = config_data or load_config_file()
    cli_overrides = cli_overrides or {}

    def pick(key: str, default: Any, env_key: str | None = None) -> Any:
        if key in cli_overrides and cli_overrides[key] is not None:
            sources[key] = "cli"
            return cli_overrides[key]
        if env_key and env_key in env and env[env_key]:
            sources[key] = "env"
            return env[env_key]
        if key in config_data and config_data[key] is not None:
            sources[key] = "config"
            return config_data[key]
        sources[key] = "default"
        return default

    ide_cmd = str(pick("ide_cmd", DEFAULT_CONFIG.ide_cmd, "CODESHARD_IDE_CMD"))
    ai_cmd = str(pick("ai_cmd", DEFAULT_CONFIG.ai_cmd, "CODESHARD_AI_CMD"))
    ide_enabled_default = _coerce_bool(pick("ide_enabled_default", DEFAULT_CONFIG.ide_enabled_default))
    ai_enabled_default = _coerce_bool(pick("ai_enabled_default", DEFAULT_CONFIG.ai_enabled_default))
    allow_shell = _coerce_bool(pick("allow_shell", DEFAULT_CONFIG.allow_shell))

    config = Config(
        ide_cmd=ide_cmd,
        ai_cmd=ai_cmd,
        ide_enabled_default=ide_enabled_default,
        ai_enabled_default=ai_enabled_default,
        allow_shell=allow_shell,
    )
    return config, sources


def update_config_value(key: str, value: Any) -> None:
    data = load_config_file()
    data[key] = value
    write_config_file(data)
