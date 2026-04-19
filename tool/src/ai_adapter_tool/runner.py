from __future__ import annotations

import shlex
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from .config import AIConfig


@dataclass(frozen=True)
class AIInvocation:
    provider: str
    strategy: str
    logical_command: str
    process_command: str
    replay_command: str
    cwd: Path
    prompt_mode: str
    launch_mode: str


@dataclass(frozen=True)
class AIResult:
    stdout: str
    stderr: str
    returncode: int


class CliStrategy:
    def __init__(self, config: AIConfig):
        self.config = config

    def invocation(self, prompt: str, cwd: Path) -> AIInvocation:
        cmd = self._build_command(prompt)
        return AIInvocation(
            provider=self.config.provider,
            strategy=self.config.strategy,
            logical_command=command_preview(self.config),
            process_command=subprocess.list2cmdline(cmd),
            replay_command=replay_command(self.config),
            cwd=cwd,
            prompt_mode=self.config.prompt_mode,
            launch_mode=self.config.launch_mode,
        )

    def run(self, prompt: str, cwd: Path, *, stdout_path: Path | None = None, stderr_path: Path | None = None) -> AIResult:
        cmd = self._build_command(prompt)
        input_text: str | None = prompt
        if "{{prompt}}" in self.config.command:
            input_text = None
        if self.config.prompt_mode == "arg" and self.config.launch_mode == "direct" and "{{prompt}}" not in self.config.command:
            cmd.append(prompt)
            input_text = None
        elif self.config.prompt_mode == "arg":
            input_text = None
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if input_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cwd),
            bufsize=1,
        )
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        threads: list[threading.Thread] = []
        if input_text is not None and proc.stdin is not None:
            proc.stdin.write(input_text)
            proc.stdin.close()
        if proc.stdout is not None:
            stdout_handle = stdout_path.open("a", encoding="utf-8") if stdout_path else None
            threads.append(threading.Thread(target=_tee_stream, args=(proc.stdout, sys.stdout, stdout_chunks, stdout_handle), daemon=True))
        if proc.stderr is not None:
            stderr_handle = stderr_path.open("a", encoding="utf-8") if stderr_path else None
            threads.append(threading.Thread(target=_tee_stream, args=(proc.stderr, sys.stderr, stderr_chunks, stderr_handle), daemon=True))
        for thread in threads:
            thread.start()
        try:
            returncode = proc.wait(timeout=self.config.timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            returncode = proc.wait()
        for thread in threads:
            thread.join()
        return AIResult("".join(stdout_chunks), "".join(stderr_chunks), returncode)

    def _build_command(self, prompt: str) -> list[str]:
        has_prompt = "{{prompt}}" in self.config.command
        command = self.config.command.replace("{{prompt}}", prompt)
        base = split_command(command)
        if self.config.launch_mode == "direct":
            return base
        if self.config.launch_mode == "powershell":
            quoted = " ".join(quote_powershell_arg(item) for item in base)
            if self.config.prompt_mode == "stdin" and not has_prompt:
                expression = "$inputText = [Console]::In.ReadToEnd(); " + f"$inputText | {quoted}"
            else:
                expression = quoted if has_prompt else f"{quoted} {quote_powershell_arg(prompt)}"
            return ["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", expression]
        if self.config.launch_mode == "bash":
            if self.config.prompt_mode == "stdin" and not has_prompt:
                return ["bash", "-lc", f"cat | {shlex.join(base)}"]
            return ["bash", "-lc", shlex.join(base if has_prompt else [*base, prompt])]
        raise ValueError(f"不支持的 launch_mode：{self.config.launch_mode}")


def create_strategy(config: AIConfig) -> CliStrategy:
    if config.strategy == "cli":
        return CliStrategy(config)
    raise ValueError(f"不支持的 ai strategy：{config.strategy}")


def split_command(command: str) -> list[str]:
    return shlex.split(command, posix=True)


def command_preview(config: AIConfig) -> str:
    command = config.command.replace("{{prompt}}", "<prompt>")
    return " ".join(quote_display_arg(item) for item in split_command(command))


def replay_command(config: AIConfig, prompt_file: str = "ai-prompt.md") -> str:
    base = command_preview(config)
    if "{{prompt}}" in config.command:
        return base.replace("<prompt>", f"(Get-Content -LiteralPath {prompt_file} -Raw)")
    if config.prompt_mode == "stdin":
        return f"Get-Content -LiteralPath {prompt_file} -Raw | {base}"
    return f"{base} (Get-Content -LiteralPath {prompt_file} -Raw)"


def quote_powershell_arg(value: str) -> str:
    if value == "":
        return "''"
    if all(ch.isalnum() or ch in "-_./:\\" for ch in value):
        return value
    return "'" + value.replace("'", "''") + "'"


def quote_display_arg(value: str) -> str:
    if value == "":
        return '""'
    if all(ch.isalnum() or ch in "-_./:\\" for ch in value):
        return value
    return '"' + value.replace('"', '\\"') + '"'


def _tee_stream(stream, sink, chunks: list[str], mirror=None) -> None:
    for line in iter(stream.readline, ""):
        chunks.append(line)
        sink.write(line)
        sink.flush()
        if mirror is not None:
            mirror.write(line)
            mirror.flush()
    stream.close()
    if mirror is not None:
        mirror.close()
