from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .config import load_config, resolve_config_path
from .jsonio import now_iso
from .prd import PRDTemplateCreated, load_prd
from .runner import AIInvocation, create_strategy


class PreparedTask:
    def __init__(self, config: Any, agent: str, task_dir: Path, prompt: str, strategy: Any):
        self.config = config
        self.agent = agent
        self.task_dir = task_dir
        self.prompt = prompt
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


def cmd_status(args: argparse.Namespace) -> int:
    config = load_config(resolve_config_path(args.config))
    agent = resolve_agent(args, config)
    prd = load_prd(config.target_dir)
    ai_config = config.ai_for_agent(agent)
    invocation = create_strategy(ai_config).invocation("status preview", config.target_dir)
    print(
        json.dumps(
            {
                "config": str(config.config_path),
                "target_dir": str(config.target_dir),
                "runtime": str(config.runtime_path),
                "prd": {"path": str(config.prd_path), "title": prd.title, "doc": prd.doc, "level": prd.level},
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
    result = task.strategy.run(task.prompt, cwd=task.config.target_dir, stdout_path=stdout_path, stderr_path=stderr_path)
    print(f"returncode: {result.returncode}")
    return 0 if result.returncode == 0 else 2


def build_task(args: argparse.Namespace) -> PreparedTask:
    config = load_config(resolve_config_path(args.config))
    agent = resolve_agent(args, config)
    prd = load_prd(config.target_dir)
    config.runtime_path.mkdir(parents=True, exist_ok=True)
    task_dir = next_task_dir(config.runtime_path, agent)
    task_dir.mkdir(parents=True, exist_ok=False)

    prompt = build_prompt(agent, prd.to_prompt_text())
    prompt_path = task_dir / "ai-prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    ai_config = config.ai_for_agent(agent)
    strategy = create_strategy(ai_config)
    invocation = strategy.invocation(prompt, config.target_dir)
    write_invocation(task_dir, invocation)
    return PreparedTask(config=config, agent=agent, task_dir=task_dir, prompt=prompt, strategy=strategy)


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
            "- If writing files, write only under the target_dir.",
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
