from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = "ai_adapter.toml"


@dataclass(frozen=True)
class AgentConfig:
    name: str
    model: dict[str, str]


@dataclass(frozen=True)
class AIConfig:
    provider: str
    strategy: str
    default_agent: str
    command: str
    prompt_mode: str
    timeout_seconds: int
    launch_mode: str
    yolo: bool


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    target_dir: Path
    runtime_dir: Path
    ai: AIConfig
    agents: dict[str, AgentConfig]
    provider_templates: dict[str, str]

    @property
    def runtime_path(self) -> Path:
        return self.target_dir / self.runtime_dir

    @property
    def prd_path(self) -> Path:
        return self.target_dir / "PRD.toml"

    def ai_for_agent(self, agent_name: str) -> AIConfig:
        template = self.provider_templates.get(self.ai.provider)
        if not template:
            raise ValueError(f"未配置 providers.{self.ai.provider}")
        agent = self.agents.get(agent_name) or AgentConfig(
            name=agent_name,
            model={self.ai.provider: ""},
        )
        return AIConfig(
            provider=self.ai.provider,
            strategy=self.ai.strategy,
            default_agent=self.ai.default_agent,
            command=render_cli_template(template, agent, self.ai.provider, self.ai.yolo),
            prompt_mode=self.ai.prompt_mode,
            timeout_seconds=self.ai.timeout_seconds,
            launch_mode=self.ai.launch_mode,
            yolo=self.ai.yolo,
        )


def resolve_config_path(value: str | None) -> Path:
    if value:
        return Path(value)
    env_value = os.environ.get("AI_ADAPTER_CONFIG")
    if env_value:
        return Path(env_value)
    candidates = [
        Path.cwd() / DEFAULT_CONFIG,
        Path.cwd().parent / DEFAULT_CONFIG,
        Path.cwd().parent.parent / DEFAULT_CONFIG,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(DEFAULT_CONFIG)


def load_config(config_path: Path | None) -> AppConfig:
    path = resolve_config_path(str(config_path) if config_path else None)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if "common" not in raw:
        raise ValueError("ai_adapter.toml 必须使用 [common]、[ai]、[providers.*]、[agents.*] 结构")

    common = raw["common"]
    target_dir = _resolve_path(path.parent, common["target_dir"])
    runtime_dir = Path(str(common.get("runtime_dir", "runtime")))
    if runtime_dir.is_absolute():
        raise ValueError("common.runtime_dir 必须是相对路径")

    ai_raw = raw.get("ai", {})
    prompt_mode = str(ai_raw.get("prompt_mode", "stdin"))
    launch_mode = str(ai_raw.get("launch_mode", "powershell"))
    if prompt_mode not in {"stdin", "arg"}:
        raise ValueError("ai.prompt_mode 只支持 stdin 或 arg")
    if launch_mode not in {"direct", "powershell", "bash"}:
        raise ValueError("ai.launch_mode 只支持 direct、powershell 或 bash")

    provider = str(ai_raw.get("ai_provider", "codex"))
    provider_templates = _load_provider_templates(raw.get("providers", {}))
    if provider not in provider_templates:
        raise ValueError(f"ai.ai_provider 指定的 provider 未在 [providers.{provider}] 中定义: {provider}")

    agents = _load_agents(raw.get("agents", {}))
    ai = AIConfig(
        provider=provider,
        strategy="cli",
        default_agent=str(ai_raw.get("default_agent", "general-senior-dev-agent")),
        command=provider_templates[provider],
        prompt_mode=prompt_mode,
        timeout_seconds=int(ai_raw.get("timeout_seconds", 600)),
        launch_mode=launch_mode,
        yolo=bool(ai_raw.get("yolo", False)),
    )
    return AppConfig(path.resolve(), target_dir, runtime_dir, ai, agents, provider_templates)


def render_cli_template(template: str, agent: AgentConfig, provider: str, yolo: bool) -> str:
    command = template
    command = command.replace("{{agent.name}}", agent.name)
    command = command.replace(f"{{{{agent.model.{provider}}}}}", agent.model.get(provider, ""))
    command = command.replace("{{yolo:--yolo}}", "--yolo" if yolo else "")
    return " ".join(command.split())


def _resolve_path(base: Path, value: Any) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    return path.resolve()


def _load_provider_templates(raw_providers: dict[str, Any]) -> dict[str, str]:
    providers: dict[str, str] = {}
    for key, value in raw_providers.items():
        if not isinstance(value, dict):
            continue
        cli = str(value.get("cli", "")).strip()
        if cli:
            providers[str(key)] = cli
    return providers


def _load_agents(raw_agents: dict[str, Any]) -> dict[str, AgentConfig]:
    agents: dict[str, AgentConfig] = {}
    for key, value in raw_agents.items():
        if not isinstance(value, dict):
            continue
        name = str(value.get("name", key))
        model_raw = value.get("model", {})
        model = {str(k): str(v) for k, v in model_raw.items()} if isinstance(model_raw, dict) else {}
        config = AgentConfig(name=name, model=model)
        agents[key] = config
        agents[name] = config
    return agents
