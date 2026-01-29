from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Iterable


@dataclass(frozen=True)
class CmdResult:
    stdout: str
    stderr: str
    returncode: int


class CommandError(RuntimeError):
    def __init__(self, message: str, result: CmdResult):
        super().__init__(message)
        self.result = result


def run_cmd(cmd: Iterable[str], cwd: Path, check: bool = False) -> CmdResult:
    completed = subprocess.run(
        list(cmd),
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    result = CmdResult(
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        returncode=completed.returncode,
    )
    if check and result.returncode != 0:
        raise CommandError(f"Command failed: {' '.join(cmd)}", result)
    return result


def git_cmd(args: Iterable[str], cwd: Path, check: bool = True) -> CmdResult:
    return run_cmd(["git", *list(args)], cwd=cwd, check=check)


def get_repo_root(cwd: Path) -> Path:
    result = git_cmd(["rev-parse", "--show-toplevel"], cwd=cwd, check=True)
    return Path(result.stdout)


def get_current_branch(cwd: Path) -> str:
    result = git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, check=True)
    return result.stdout


def add_worktree(path: Path, branch: str, base: str, cwd: Path) -> bool:
    primary = git_cmd(
        ["worktree", "add", "-b", branch, str(path), base],
        cwd=cwd,
        check=False,
    )
    if primary.returncode == 0:
        return True
    if "already exists" in primary.stderr.lower():
        fallback = git_cmd(
            ["worktree", "add", str(path), branch],
            cwd=cwd,
            check=False,
        )
        if fallback.returncode == 0:
            return False
        raise CommandError("Failed to add worktree with existing branch", fallback)
    raise CommandError("Failed to add worktree", primary)


def remove_worktree(path: Path, cwd: Path, force: bool) -> None:
    args = ["worktree", "remove", str(path)]
    result = git_cmd(args, cwd=cwd, check=False)
    if result.returncode == 0:
        return
    if force:
        force_result = git_cmd(["worktree", "remove", "--force", str(path)], cwd=cwd, check=False)
        if force_result.returncode == 0:
            return
        raise CommandError("Failed to force remove worktree", force_result)
    raise CommandError("Failed to remove worktree", result)


def prune_worktrees(cwd: Path) -> None:
    git_cmd(["worktree", "prune"], cwd=cwd, check=False)


def delete_branch(branch: str, cwd: Path, force: bool) -> None:
    args = ["branch", "-d", branch]
    result = git_cmd(args, cwd=cwd, check=False)
    if result.returncode == 0:
        return
    if force:
        force_result = git_cmd(["branch", "-D", branch], cwd=cwd, check=False)
        if force_result.returncode == 0:
            return
        raise CommandError("Failed to force delete branch", force_result)
    raise CommandError("Failed to delete branch", result)


def list_worktrees(cwd: Path, porcelain: bool) -> CmdResult:
    args = ["worktree", "list"]
    if porcelain:
        args.append("--porcelain")
    return git_cmd(args, cwd=cwd, check=False)
