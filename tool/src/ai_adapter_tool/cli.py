from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .config import AppConfig, load_config
from .jsonio import now_iso
from .prd import PRDTemplateCreated, load_prd
from .runner import AIInvocation, create_strategy


class PreparedTask:
    def __init__(self, config: Any, agent: str, task_dir: Path, prompt: str, prompt_path: Path, strategy: Any):
        self.config = config
        self.agent = agent
        self.task_dir = task_dir
        self.prompt = prompt
        self.prompt_path = prompt_path
        self.strategy = strategy


def main(argv: list[str] | None = None) -> int:
    return execute(argv)


def execute(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except PRDTemplateCreated as exc:
        print(str(exc))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-adapter", description="Standalone AI CLI adapter")
    sub = parser.add_subparsers(required=True)

    status = sub.add_parser("status", help="show config, PRD and rendered CLI")
    add_common_args(status)
    status.set_defaults(func=cmd_status)

    dry = sub.add_parser("dry-run", help="create prompt and invocation files without calling AI")
    add_common_args(dry)
    dry.set_defaults(func=cmd_dry_run)

    run = sub.add_parser("run", help="call AI CLI and print stdout/stderr")
    add_common_args(run)
    run.set_defaults(func=cmd_run)
    return parser


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default=None, help="ai_adapter.toml path or AI_ADAPTER_CONFIG")
    parser.add_argument("--agent", default=None, help="agent key or name from ai_adapter.toml; defaults to [ai].default_agent")
    parser.add_argument("--project-dir", default=None, help="project 目录；覆盖 ai_adapter.toml 中的默认 project_dir")
    parser.add_argument("--ai-config-dir", default=None, help="ai_config 目录；覆盖 ai_adapter.toml 中的默认 ai_config.dir")
    parser.add_argument("--prd-name", default=None, help="PRD 别名；从 [prd.refs] 中解析，覆盖 [prd].default")
    parser.add_argument("--prd-path", default=None, help="PRD 文件完整路径；优先级高于 --prd-name")
    cleanup_group = parser.add_mutually_exclusive_group()
    cleanup_group.add_argument("--cleanup-ai-config-artifacts", dest="cleanup_ai_config_artifacts", action="store_true", help="run 完成后自动删除 ai_config.dir 下的 logs、session-state 和 config.json")
    cleanup_group.add_argument("--no-cleanup-ai-config-artifacts", dest="cleanup_ai_config_artifacts", action="store_false", help="run 完成后保留 ai_config.dir 下的 logs、session-state 和 config.json")
    parser.set_defaults(cleanup_ai_config_artifacts=None)


def cmd_status(args: argparse.Namespace) -> int:
    config = load_app_config(args)
    agent = resolve_agent(args, config)
    prd = load_prd(config.prd_path, config.project_dir)
    ai_config = config.ai_for_agent(agent)
    invocation = create_strategy(ai_config).invocation("status preview", config.project_dir)
    print(
        json.dumps(
            {
                "config": str(config.config_path),
                "project_dir": str(config.project_dir),
                "target_dir": str(config.target_dir),
                "ai_config_dir": str(config.ai_config_dir),
                "cleanup_ai_config_artifacts": config.cleanup_ai_config_artifacts,
                "runtime": str(config.runtime_path),
                "prd": {
                    "name": config.prd_name,
                    "path": str(config.prd_path),
                    "title": prd.title,
                    "doc": prd.doc,
                    "level": prd.level,
                },
                "agent": agent,
                "ai": {
                    "provider": ai_config.provider,
                    "strategy": ai_config.strategy,
                    "logical_command": invocation.logical_command,
                    "process_command": invocation.process_command,
                    "replay_command": invocation.replay_command,
                    "prompt_mode": ai_config.prompt_mode,
                    "launch_mode": ai_config.launch_mode,
                    "timeout_seconds": ai_config.timeout_seconds,
                    "yolo": ai_config.yolo,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    task = build_task(args)
    print(f"dry-run task: {task.task_dir}")
    print(f"invocation: {task.task_dir / 'ai-invocation.md'}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    task = build_task(args)
    stdout_path = task.task_dir / "ai-stdout.txt"
    stderr_path = task.task_dir / "ai-stderr.txt"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    print(f"task: {task.task_dir}")
    print(f"AI invocation: {task.task_dir / 'ai-invocation.md'}")
    try:
        result = task.strategy.run(task.prompt, cwd=task.config.project_dir, prompt_path=task.prompt_path, stdout_path=stdout_path, stderr_path=stderr_path)
        print(f"returncode: {result.returncode}")
        return 0 if result.returncode == 0 else 2
    finally:
        if task.config.cleanup_ai_config_artifacts:
            cleanup_ai_config_artifacts(task.config.ai_config_dir)


def build_task(args: argparse.Namespace) -> PreparedTask:
    config = load_app_config(args)
    agent = resolve_agent(args, config)
    prd = load_prd(config.prd_path, config.project_dir)
    config.runtime_path.mkdir(parents=True, exist_ok=True)
    task_dir = next_task_dir(config.runtime_path, agent)
    task_dir.mkdir(parents=True, exist_ok=False)

    prompt = build_prompt(agent, prd.to_prompt_text())
    prompt_path = task_dir / "ai-prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    ai_config = config.ai_for_agent(agent)
    strategy = create_strategy(ai_config)
    invocation = strategy.invocation(prompt, config.project_dir, prompt_path=prompt_path)
    write_invocation(task_dir, invocation)
    return PreparedTask(config=config, agent=agent, task_dir=task_dir, prompt=prompt, prompt_path=prompt_path, strategy=strategy)


def build_prompt(agent: str, prd_text: str) -> str:
    return "\n".join(
        [
            "# AI Adapter Task",
            "",
            f"Agent: `{agent}`",
            "",
            "## PRD",
            "",
            prd_text.strip(),
            "",
            "## Output Requirements",
            "",
            "- Follow the configured agent instructions if the CLI loads one.",
            "- Keep outputs grounded in the PRD.",
            "- If writing files, write only under the project_dir.",
            "",
        ]
    )


def next_task_dir(runtime_path: Path, agent: str) -> Path:
    runs = runtime_path / "ai-runs"
    runs.mkdir(parents=True, exist_ok=True)
    safe_agent = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in agent)
    stamp = (
        now_iso()
        .replace(":", "")
        .replace("+", "_")
        .replace("-", "")
        .replace("T", "_")
    )
    return runs / f"run-{stamp}-{safe_agent}"


def resolve_agent(args: argparse.Namespace, config: Any) -> str:
    return str(args.agent or config.ai.default_agent)


def load_app_config(args: argparse.Namespace) -> AppConfig:
    return load_config(
        args.config,
        project_dir_override=args.project_dir,
        ai_config_dir_override=args.ai_config_dir,
        cleanup_ai_config_artifacts_override=args.cleanup_ai_config_artifacts,
        prd_name_override=args.prd_name,
        prd_path_override=args.prd_path,
    )


def write_invocation(task_dir: Path, invocation: AIInvocation) -> None:
    (task_dir / "ai-invocation.md").write_text(
        "\n".join(
            [
                "# AI CLI Invocation",
                "",
                f"- provider: `{invocation.provider}`",
                f"- strategy: `{invocation.strategy}`",
                f"- cwd: `{invocation.cwd}`",
                f"- prompt: `{task_dir / 'ai-prompt.md'}`",
                f"- prompt_mode: `{invocation.prompt_mode}`",
                f"- launch_mode: `{invocation.launch_mode}`",
                "",
                "## Logical CLI",
                "",
                "```powershell",
                invocation.logical_command,
                "```",
                "",
                "## Actual Subprocess Command",
                "",
                "```powershell",
                invocation.process_command,
                "```",
                "",
                "## Replay Command",
                "",
                "```powershell",
                invocation.replay_command,
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def cleanup_ai_config_artifacts(ai_config_dir: Path) -> None:
    # Responsibility: Remove transient AI runtime artifacts after each run completes.
    for name in ("logs", "session-state", "config.json"):
        path = ai_config_dir / name
        if not path.exists():
            continue
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
        except FileNotFoundError:
            continue
