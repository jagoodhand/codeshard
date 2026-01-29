from __future__ import annotations

from pathlib import Path

from codeshard import launch


def test_build_launch_plan_with_path_split():
    plan = launch.build_launch_plan(
        'code "{path}"',
        Path("/tmp/my repo"),
        allow_shell=False,
        require_path=True,
        cwd=None,
    )
    assert plan is not None
    assert list(plan.cmd) == ["code", "/tmp/my repo"]
    assert plan.use_shell is False


def test_build_launch_plan_missing_required_path():
    plan = launch.build_launch_plan(
        "code",
        Path("/tmp/thing"),
        allow_shell=False,
        require_path=True,
        cwd=None,
    )
    assert plan is None


def test_build_launch_plan_allow_shell():
    plan = launch.build_launch_plan(
        "open -a Terminal {path}",
        Path("/tmp/thing"),
        allow_shell=True,
        require_path=False,
        cwd=Path("/tmp"),
    )
    assert plan is not None
    assert plan.use_shell is True
    assert plan.cmd == "open -a Terminal /tmp/thing"
    assert plan.cwd == Path("/tmp")
