from __future__ import annotations

from pathlib import Path
import os
import typer

from . import config
from . import git
from . import launch

app = typer.Typer(add_completion=False, help="Manage Git worktrees as AI coding sandboxes.")
config_app = typer.Typer(help="Configure codeshard defaults.")
app.add_typer(config_app, name="config")


def _resolve_common_paths(
    name: str,
    repo: Path | None,
    root: Path | None,
    path: Path | None,
) -> tuple[Path, Path, Path]:
    repo_root = config.resolve_repo_root(repo, Path.cwd())
    worktrees_root = config.resolve_worktrees_root(repo_root, root, os.environ.get("WT_ROOT"))
    target_path = config.resolve_target_path(name, worktrees_root, path)
    return repo_root, worktrees_root, target_path


def _resolve_launch_config(ide_cmd: str | None, ai_cmd: str | None) -> config.Config:
    overrides = {"ide_cmd": ide_cmd, "ai_cmd": ai_cmd}
    resolved, _ = config.resolve_config(cli_overrides=overrides)
    return resolved


def _maybe_launch_ide(cfg: config.Config, path: Path) -> None:
    plan = launch.build_launch_plan(
        cfg.ide_cmd,
        path,
        allow_shell=cfg.allow_shell,
        require_path=True,
        cwd=None,
    )
    if plan is None:
        typer.secho("IDE command not configured; skipping IDE launch.", fg=typer.colors.YELLOW)
        return
    launch.run_launch(plan)


def _maybe_launch_ai(cfg: config.Config, path: Path) -> None:
    plan = launch.build_launch_plan(
        cfg.ai_cmd,
        path,
        allow_shell=cfg.allow_shell,
        require_path=False,
        cwd=path,
    )
    if plan is None:
        typer.secho("AI command not configured; skipping AI launch.", fg=typer.colors.YELLOW)
        return
    launch.run_launch(plan)


@app.command()
def new(
    name: str = typer.Argument(..., help="Name for the worktree."),
    base: str | None = typer.Option(None, help="Base ref for the new worktree."),
    branch: str | None = typer.Option(None, help="Branch name to create or use."),
    path: Path | None = typer.Option(None, help="Explicit worktree path."),
    root: Path | None = typer.Option(None, "--root", help="Override worktrees root."),
    repo: Path | None = typer.Option(None, "--repo", help="Anchor repository path."),
    open_ide: bool | None = typer.Option(None, "--open-ide/--no-open-ide", help="Open IDE."),
    ide_cmd: str | None = typer.Option(None, "--ide-cmd", help="Override IDE command."),
    open_ai: bool | None = typer.Option(None, "--open-ai/--no-open-ai", help="Open AI tool."),
    ai_cmd: str | None = typer.Option(None, "--ai-cmd", help="Override AI command."),
) -> None:
    repo_root, worktrees_root, target_path = _resolve_common_paths(name, repo, root, path)
    branch_name = branch or name
    base_ref = base or git.get_current_branch(repo_root)
    worktrees_root.mkdir(parents=True, exist_ok=True)

    try:
        created = git.add_worktree(target_path, branch_name, base_ref, repo_root)
    except git.CommandError as exc:
        typer.secho(exc.args[0], fg=typer.colors.RED, err=True)
        if exc.result.stderr:
            typer.echo(exc.result.stderr, err=True)
        raise typer.Exit(code=1)

    cfg = _resolve_launch_config(ide_cmd, ai_cmd)
    ide_enabled = cfg.ide_enabled_default if open_ide is None else open_ide
    ai_enabled = cfg.ai_enabled_default if open_ai is None else open_ai

    typer.echo(f"Created worktree: {target_path}")
    typer.echo(f"Branch: {branch_name}{'' if created else ' (existing)'}")
    typer.echo(f"Base ref: {base_ref}")

    suggested_ai = cfg.ai_cmd or "codex"
    suggested_ai = launch.render_template(suggested_ai, target_path)
    typer.echo(f"Next: cd {target_path} && {suggested_ai}")

    if ide_enabled:
        _maybe_launch_ide(cfg, target_path)
    if ai_enabled:
        _maybe_launch_ai(cfg, target_path)


@app.command()
def rm(
    name: str = typer.Argument(..., help="Worktree name."),
    path: Path | None = typer.Option(None, help="Explicit worktree path."),
    root: Path | None = typer.Option(None, "--root", help="Override worktrees root."),
    repo: Path | None = typer.Option(None, "--repo", help="Anchor repository path."),
    prune: bool = typer.Option(True, "--prune/--no-prune", help="Prune worktrees."),
    delete_branch: bool = typer.Option(False, "--delete-branch/--no-delete-branch", help="Delete branch."),
    force: bool = typer.Option(False, help="Force removal if needed."),
) -> None:
    repo_root, _, target_path = _resolve_common_paths(name, repo, root, path)
    try:
        git.remove_worktree(target_path, repo_root, force=force)
    except git.CommandError as exc:
        typer.secho(exc.args[0], fg=typer.colors.RED, err=True)
        if exc.result.stderr:
            typer.echo(exc.result.stderr, err=True)
        raise typer.Exit(code=1)

    if prune:
        git.prune_worktrees(repo_root)

    branch_deleted = False
    if delete_branch:
        try:
            git.delete_branch(name, repo_root, force=force)
            branch_deleted = True
        except git.CommandError as exc:
            typer.secho(exc.args[0], fg=typer.colors.RED, err=True)
            if exc.result.stderr:
                typer.echo(exc.result.stderr, err=True)
            raise typer.Exit(code=1)

    typer.echo(f"Removed worktree: {target_path}")
    typer.echo(f"Branch deleted: {'yes' if branch_deleted else 'no'}")


@app.command()
def ls(
    porcelain: bool = typer.Option(False, "--porcelain", help="Machine-friendly output."),
    repo: Path | None = typer.Option(None, "--repo", help="Anchor repository path."),
) -> None:
    repo_root = config.resolve_repo_root(repo, Path.cwd())
    result = git.list_worktrees(repo_root, porcelain=porcelain)
    if result.stdout:
        typer.echo(result.stdout)


@app.command()
def open(
    name: str = typer.Argument(..., help="Worktree name."),
    path: Path | None = typer.Option(None, help="Explicit worktree path."),
    root: Path | None = typer.Option(None, "--root", help="Override worktrees root."),
    repo: Path | None = typer.Option(None, "--repo", help="Anchor repository path."),
    open_ide: bool | None = typer.Option(None, "--open-ide/--no-open-ide", help="Open IDE."),
    ide_cmd: str | None = typer.Option(None, "--ide-cmd", help="Override IDE command."),
    open_ai: bool | None = typer.Option(None, "--open-ai/--no-open-ai", help="Open AI tool."),
    ai_cmd: str | None = typer.Option(None, "--ai-cmd", help="Override AI command."),
) -> None:
    _, _, target_path = _resolve_common_paths(name, repo, root, path)
    cfg = _resolve_launch_config(ide_cmd, ai_cmd)
    ide_enabled = cfg.ide_enabled_default if open_ide is None else open_ide
    ai_enabled = cfg.ai_enabled_default if open_ai is None else open_ai

    if ide_enabled:
        _maybe_launch_ide(cfg, target_path)
    if ai_enabled:
        _maybe_launch_ai(cfg, target_path)


@config_app.command("show")
def config_show() -> None:
    cfg, sources = config.resolve_config()
    typer.echo(f"Config file: {config.get_config_file_path()}")
    typer.echo(f"ide_cmd = {cfg.ide_cmd!r} (source: {sources['ide_cmd']})")
    typer.echo(f"ai_cmd = {cfg.ai_cmd!r} (source: {sources['ai_cmd']})")
    typer.echo(
        f"ide_enabled_default = {cfg.ide_enabled_default} (source: {sources['ide_enabled_default']})"
    )
    typer.echo(
        f"ai_enabled_default = {cfg.ai_enabled_default} (source: {sources['ai_enabled_default']})"
    )
    typer.echo(f"allow_shell = {cfg.allow_shell} (source: {sources['allow_shell']})")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key to set."),
    value: str = typer.Argument(..., help="Value to store."),
) -> None:
    valid_keys = {
        "ide_cmd",
        "ai_cmd",
        "ide_enabled_default",
        "ai_enabled_default",
        "allow_shell",
    }
    if key not in valid_keys:
        typer.secho(f"Unknown config key: {key}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if key in {"ide_enabled_default", "ai_enabled_default", "allow_shell"}:
        try:
            parsed = config._coerce_bool(value)
        except ValueError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        config.update_config_value(key, parsed)
    else:
        config.update_config_value(key, value)

    typer.echo(f"Updated {key} in {config.get_config_file_path()}")


if __name__ == "__main__":
    app()
