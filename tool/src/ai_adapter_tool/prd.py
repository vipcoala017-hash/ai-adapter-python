from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PRD:
    title: str
    doc: str
    level: str
    doc_text: str

    def to_prompt_text(self) -> str:
        parts = [
            f"# {self.title}" if self.title else "# Untitled Task",
            "",
            f"PRD level: {self.level}",
        ]
        if self.doc:
            parts.append(f"PRD doc: {self.doc}")
        if self.doc_text:
            parts.extend(["", self.doc_text])
        return "\n".join(parts).strip() + "\n"


class PRDTemplateCreated(RuntimeError):
    pass


def load_prd(target_dir: Path) -> PRD:
    path = target_dir / "PRD.toml"
    if not path.exists():
        create_prd_template(path)
        raise PRDTemplateCreated(f"已创建 PRD.toml 模板，请填写后重新执行：{path}")
    raw = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    prd = raw.get("prd", {})
    title = str(prd.get("title", "")).strip()
    doc = str(prd.get("doc", "")).strip()
    level = str(prd.get("level", "task")).strip()

    doc_text = ""
    if doc:
        doc_path = (target_dir / doc).resolve()
        doc_path.relative_to(target_dir.resolve())
        if not doc_path.exists():
            raise FileNotFoundError(f"PRD doc 不存在：{doc_path}")
        doc_text = doc_path.read_text(encoding="utf-8-sig").strip()
    return PRD(title=title, doc=doc, level=level, doc_text=doc_text)


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
