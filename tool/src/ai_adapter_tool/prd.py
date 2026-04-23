from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PRD:
    title: str
    doc: str
    doc_path: Path | None
    level: str
    doc_text: str

    def to_prompt_text(self) -> str:
        parts = [
            f"# {self.title}" if self.title else "# Untitled Task",
            "",
            f"PRD level: {self.level}",
        ]
        if self.doc_path:
            parts.append(f"PRD doc: {self.doc_path}")
        elif self.doc:
            parts.append(f"PRD doc: {self.doc}")
        if self.doc_text:
            parts.extend(["", self.doc_text])
        return "\n".join(parts).strip() + "\n"


class PRDTemplateCreated(RuntimeError):
    pass


def load_prd(prd_path: Path, project_dir: Path) -> PRD:
    path = prd_path.resolve()
    if not path.exists():
        create_prd_template(path)
        raise PRDTemplateCreated(f"已创建 PRD.toml 模板，请填写后重新执行：{path}")
    raw = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    prd = raw.get("prd", {})
    title = str(prd.get("title", "")).strip()
    doc = str(prd.get("doc", "")).strip()
    level = str(prd.get("level", "task")).strip()

    doc_path: Path | None = None
    doc_text = ""
    if doc:
        doc_path = _resolve_prd_doc_path(doc, path.parent, project_dir)
        if not doc_path.exists():
            raise FileNotFoundError(f"PRD doc 不存在：{doc_path}")
        doc_text = doc_path.read_text(encoding="utf-8-sig").strip()
    return PRD(title=title, doc=doc, doc_path=doc_path, level=level, doc_text=doc_text)


def create_prd_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "[prd]",
                'title = ""',
                'doc = ""',
                'level = ""',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _resolve_prd_doc_path(value: str, prd_dir: Path, project_dir: Path) -> Path:
    raw = Path(str(value)).expanduser()
    if raw.is_absolute():
        candidate = raw.resolve()
    else:
        candidate = (prd_dir / raw).resolve()
        if not candidate.exists():
            legacy_candidate = (project_dir / raw).resolve()
            if legacy_candidate.exists():
                candidate = legacy_candidate
    try:
        candidate.relative_to(project_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"PRD doc 必须位于 project_dir 内：{candidate}") from exc
    return candidate
