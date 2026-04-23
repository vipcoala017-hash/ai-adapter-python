from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = "ai_adapter.toml"
DEFAULT_PROJECT_DIR = "../project"
DEFAULT_AI_CONFIG_DIR = "../ai_config"
DEFAULT_RUNTIME_DIR = "runtime"
DEFAULT_PRD_NAME = "default"
DEFAULT_PRD_REFS = {DEFAULT_PRD_NAME: "PRD.toml"}


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
    project_dir: Path
    runtime_dir: Path
    ai_config_dir: Path
    cleanup_ai_config_artifacts: bool
    prd_name: str
    prd_path: Path
    ai: AIConfig
    agents: dict[str, AgentConfig]
    provider_templates: dict[str, str]

    @property
    def target_dir(self) -> Path:
        return self.project_dir

    @property
    def runtime_path(self) -> Path:
        return self.project_dir / self.runtime_dir

    def ai_for_agent(
        self,
        agent_name: str,
        *,
        ai_config_dir_override: Path | None = None,
        project_dir_override: Path | None = None,
        prd_path_override: Path | None = None,
    ) -> AIConfig:
        template = self.provider_templates.get(self.ai.provider)
        if not template:
            raise ValueError(f"未配置 providers.{self.ai.provider}")
        effective_ai_config_dir = ai_config_dir_override or self.ai_config_dir
        effective_project_dir = project_dir_override or self.project_dir
        effective_prd_path = prd_path_override or self.prd_path
        agent = self.agents.get(agent_name) or AgentConfig(
            name=agent_name,
            model={self.ai.provider: ""},
        )
        return AIConfig(
            provider=self.ai.provider,
            strategy=self.ai.strategy,
            default_agent=self.ai.default_agent,
            command=render_cli_template(
                template,
                agent,
                self.ai.provider,
                self.ai.yolo,
                ai_config_dir=effective_ai_config_dir,
                project_dir=effective_project_dir,
                prd_path=effective_prd_path,
            ),
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


def load_config(
    config_path: str | Path | None,
    *,
    project_dir_override: str | Path | None = None,
    ai_config_dir_override: str | Path | None = None,
    cleanup_ai_config_artifacts_override: bool | None = None,
    prd_name_override: str | None = None,
    prd_path_override: str | Path | None = None,
) -> AppConfig:
    path = resolve_config_path(str(config_path) if config_path else None)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if "common" not in raw:
        raise ValueError("ai_adapter.toml 必须使用 [common]、[ai]、[providers.*]、[agents.*] 结构")

    common = raw["common"]
    project_dir_value = project_dir_override if project_dir_override is not None else common.get("project_dir") or common.get("target_dir") or DEFAULT_PROJECT_DIR
    project_dir_base = Path.cwd() if project_dir_override is not None else path.parent
    project_dir = _resolve_path(project_dir_base, project_dir_value)

    runtime_dir = Path(str(common.get("runtime_dir", DEFAULT_RUNTIME_DIR)))
    if runtime_dir.is_absolute():
        raise ValueError("common.runtime_dir 必须是相对路径")

    ai_config_raw = raw.get("ai_config", {})
    ai_config_dir_value = ai_config_dir_override if ai_config_dir_override is not None else ai_config_raw.get("dir", DEFAULT_AI_CONFIG_DIR)
    ai_config_dir_base = Path.cwd() if ai_config_dir_override is not None else path.parent
    ai_config_dir = _resolve_path(ai_config_dir_base, ai_config_dir_value)
    cleanup_ai_config_artifacts = (
        cleanup_ai_config_artifacts_override
        if cleanup_ai_config_artifacts_override is not None
        else bool(ai_config_raw.get("cleanup_generated_artifacts", True))
    )

    prd_raw = raw.get("prd", {})
    prd_refs = _load_prd_refs(prd_raw.get("refs", {}))
    if not prd_refs:
        prd_refs = DEFAULT_PRD_REFS.copy()
    prd_name = str(prd_name_override or prd_raw.get("default", DEFAULT_PRD_NAME)).strip() or DEFAULT_PRD_NAME
    prd_path = _resolve_prd_path(
        project_dir=project_dir,
        prd_refs=prd_refs,
        prd_name=prd_name,
        prd_path_override=prd_path_override,
    )

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
    return AppConfig(
        config_path=path.resolve(),
        project_dir=project_dir,
        runtime_dir=runtime_dir,
        ai_config_dir=ai_config_dir,
        cleanup_ai_config_artifacts=cleanup_ai_config_artifacts,
        prd_name=prd_name,
        prd_path=prd_path,
        ai=ai,
        agents=agents,
        provider_templates=provider_templates,
    )


def render_cli_template(
    template: str,
    agent: AgentConfig,
    provider: str,
    yolo: bool,
    *,
    ai_config_dir: Path,
    project_dir: Path,
    prd_path: Path,
) -> str:
    command = template
    replacements = {
        "{{agent.name}}": agent.name,
        f"{{{{agent.model.{provider}}}}}": agent.model.get(provider, ""),
        "{{ai_config_dir}}": _template_path(ai_config_dir),
        "{{project_dir}}": _template_path(project_dir),
        "{{prd_path}}": _template_path(prd_path),
        "{{agent_file}}": _template_path(ai_config_dir / "agents" / f"{agent.name}.md"),
        "{{yolo:--yolo}}": "--yolo" if yolo else "",
    }
    for old, new in replacements.items():
        command = command.replace(old, new)
    return " ".join(command.split())


def _resolve_path(base: Path, value: Any) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    return path.resolve()


def _resolve_prd_path(
    *,
    project_dir: Path,
    prd_refs: dict[str, str],
    prd_name: str,
    prd_path_override: str | Path | None,
) -> Path:
    if prd_path_override is not None:
        return _resolve_path(Path.cwd(), prd_path_override)
    ref = prd_refs.get(prd_name)
    if not ref:
        available = ", ".join(sorted(prd_refs))
        raise ValueError(f"未配置 prd.refs.{prd_name}；可用别名：{available}")
    return _resolve_path(project_dir, ref)


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


def _load_prd_refs(raw_refs: Any) -> dict[str, str]:
    if not isinstance(raw_refs, dict):
        return {}
    refs: dict[str, str] = {}
    for key, value in raw_refs.items():
        text = str(value).strip()
        if text:
            refs[str(key)] = text
    return refs


def _template_path(path: Path) -> str:
    return path.as_posix()
