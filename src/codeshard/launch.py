from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
from typing import Iterable


@dataclass(frozen=True)
class LaunchPlan:
    cmd: Iterable[str] | str
    use_shell: bool
    cwd: Path | None


def render_template(template: str, path: Path) -> str:
    return template.replace("{path}", str(path))


def build_launch_plan(
    template: str,
    path: Path,
    *,
    allow_shell: bool,
    require_path: bool,
    cwd: Path | None,
) -> LaunchPlan | None:
    if not template.strip():
        return None
    if require_path and "{path}" not in template:
        return None
    rendered = render_template(template, path)
    if allow_shell:
        return LaunchPlan(cmd=rendered, use_shell=True, cwd=cwd)
    return LaunchPlan(cmd=shlex.split(rendered), use_shell=False, cwd=cwd)


def run_launch(plan: LaunchPlan) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        plan.cmd,
        cwd=plan.cwd,
        shell=plan.use_shell,
        check=False,
    )
