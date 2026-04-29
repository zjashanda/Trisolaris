#!/usr/bin/env python3
"""Validate and use the Trisolaris modular validation pool.

This helper intentionally stays lightweight: it validates module documents and
performs keyword-based candidate matching. Final variant selection still belongs
in the project test plan because requirements can be ambiguous.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REQUIRED_SECTIONS = [
    "## 适用需求特征",
    "## 变体维度",
    "## 需求解析字段",
    "## 验证方案模板",
    "## 用例模板",
    "## 断言与证据",
    "## 执行器映射",
    "## 回灌规则",
]

TEXT_EXTS = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".h", ".c", ".cpp", ".py"}


@dataclass
class Module:
    path: Path
    module_id: str
    title: str
    tags: list[str]
    source_projects: list[str]
    text: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def pool_dir(root: Path) -> Path:
    return root / "references" / "validation-pool"


def parse_list(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [item.strip().strip("'\"") for item in value.split(",") if item.strip()]


def parse_frontmatter(path: Path, text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta


def load_modules(root: Path) -> list[Module]:
    modules: list[Module] = []
    for path in sorted(pool_dir(root).glob("*.md")):
        if path.name in {"INDEX.md", "schema.md", "source-project-extraction.md"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        meta = parse_frontmatter(path, text)
        module_id = meta.get("module_id", path.stem)
        title = meta.get("title", path.stem)
        tags = parse_list(meta.get("tags", ""))
        source_projects = parse_list(meta.get("source_projects", ""))
        modules.append(Module(path, module_id, title, tags, source_projects, text))
    return modules


def validate(root: Path) -> int:
    modules = load_modules(root)
    errors: list[str] = []
    seen: dict[str, Path] = {}
    if not (pool_dir(root) / "INDEX.md").exists():
        errors.append("missing references/validation-pool/INDEX.md")
    if not (pool_dir(root) / "schema.md").exists():
        errors.append("missing references/validation-pool/schema.md")
    for mod in modules:
        if not mod.module_id:
            errors.append(f"{mod.path}: missing module_id")
        if mod.module_id in seen:
            errors.append(f"duplicate module_id {mod.module_id}: {seen[mod.module_id]} and {mod.path}")
        seen[mod.module_id] = mod.path
        if not mod.tags:
            errors.append(f"{mod.path}: missing tags")
        for section in REQUIRED_SECTIONS:
            if section not in mod.text:
                errors.append(f"{mod.path}: missing section {section}")
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print(f"validation pool valid: {len(modules)} modules")
    for mod in modules:
        print(f"- {mod.module_id}: {mod.title}")
    return 0


def collect_requirement_text(paths: list[Path]) -> str:
    chunks: list[str] = []
    for raw in paths:
        path = raw.expanduser().resolve()
        if path.is_dir():
            files = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXTS)
        else:
            files = [path]
        for file in files:
            try:
                text = file.read_text(encoding="utf-8-sig", errors="ignore")
            except Exception:
                continue
            chunks.append(f"\n\n## FILE: {file}\n{text}")
    return "\n".join(chunks)


def score_module(mod: Module, requirement_text: str) -> tuple[int, list[str]]:
    hits: list[str] = []
    text_lower = requirement_text.lower()
    for tag in mod.tags:
        if not tag:
            continue
        pattern = re.escape(tag.lower())
        count = len(re.findall(pattern, text_lower))
        if count:
            hits.append(f"{tag}({count})")
    # Keep the score simple and explainable; repeated mentions matter but capped.
    score = sum(min(int(re.search(r"\((\d+)\)", h).group(1)), 5) for h in hits)
    return score, hits


def classify(root: Path, requirement_paths: list[Path], out: Path | None, project_key: str) -> int:
    modules = load_modules(root)
    req_text = collect_requirement_text(requirement_paths)
    if not req_text.strip():
        print("ERROR: no readable requirement text found", file=sys.stderr)
        return 1
    rows: list[tuple[int, Module, list[str]]] = []
    for mod in modules:
        score, hits = score_module(mod, req_text)
        if score:
            rows.append((score, mod, hits))
    rows.sort(key=lambda item: (-item[0], item[1].module_id))

    lines = [
        f"# {project_key} 模块化验证池匹配结果",
        "",
        "## 输入",
        "",
    ]
    for p in requirement_paths:
        lines.append(f"- `{p}`")
    lines.extend([
        "",
        "## 候选模块",
        "",
        "| 模块 | 分数 | 命中关键词 | 处理建议 |",
        "| --- | ---: | --- | --- |",
    ])
    if rows:
        for score, mod, hits in rows:
            advice = "读取模块并选择变体" if score >= 3 else "低分候选，按需求人工确认"
            lines.append(f"| `{mod.module_id}` | {score} | {', '.join(hits)} | {advice} |")
    else:
        lines.append("| 无 | 0 | - | 需要新增验证池模块 |")
    lines.extend([
        "",
        "## 后续动作",
        "",
        "1. 对高分模块读取对应 `references/validation-pool/*.md`。",
        "2. 按当前需求选择变体，禁止直接套旧项目结论。",
        "3. 生成当前项目方案、用例、断言和执行器映射。",
        "4. 执行后将新增通用逻辑回灌验证池。",
        "",
    ])
    output = "\n".join(lines)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output, encoding="utf-8")
        print(out)
    else:
        print(output)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate")

    p_classify = sub.add_parser("classify")
    p_classify.add_argument("--project-key", default="project")
    p_classify.add_argument("--out", type=Path)
    p_classify.add_argument("requirements", nargs="+", type=Path)

    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.cmd == "validate":
        return validate(root)
    if args.cmd == "classify":
        return classify(root, args.requirements, args.out, args.project_key)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
