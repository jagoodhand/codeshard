from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import codeshard.config as config
import codeshard.git as git


def _mock_run(stdout: str, stderr: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_get_repo_root(monkeypatch):
    def fake_run(cmd, cwd, text, capture_output):
        return _mock_run("/repo\n")

    monkeypatch.setattr(git.subprocess, "run", fake_run)
    assert git.get_repo_root(Path("/tmp")).as_posix() == "/repo"


def test_get_current_branch(monkeypatch):
    def fake_run(cmd, cwd, text, capture_output):
        return _mock_run("main\n")

    monkeypatch.setattr(git.subprocess, "run", fake_run)
    assert git.get_current_branch(Path("/tmp")) == "main"


def test_worktrees_root_precedence():
    repo_root = Path("/repo")
    cli_root = Path("/custom")
    env_root = "/env"
    assert config.resolve_worktrees_root(repo_root, cli_root, env_root) == cli_root
    assert config.resolve_worktrees_root(repo_root, None, env_root) == Path(env_root)
    assert config.resolve_worktrees_root(repo_root, None, None) == Path("/repo-wt")


def test_resolve_target_path():
    worktrees_root = Path("/root")
    assert config.resolve_target_path("abc", worktrees_root, None) == Path("/root/abc")
    assert config.resolve_target_path("abc", worktrees_root, Path("/explicit")) == Path("/explicit")
