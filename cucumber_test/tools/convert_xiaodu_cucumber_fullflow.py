#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def scenario_counts(behave_json: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    payload = load_json(behave_json)
    for feature in payload:
        for element in feature.get("elements", []):
            if element.get("type") != "scenario":
                continue
            statuses = [(step.get("result") or {}).get("status", "untested") for step in element.get("steps", [])]
            if any(status in {"failed", "error"} for status in statuses):
                counts["failed"] += 1
            elif any(status in {"skipped", "untested"} for status in statuses):
                counts["blocked"] += 1
            else:
                counts["passed"] += 1
    counts["total"] = counts["passed"] + counts["failed"] + counts["blocked"]
    return counts


def convert(behave_json: Path, meta_path: Path, out_dir: Path) -> None:
    meta = load_json(meta_path)
    aggregate_case_results = ROOT / meta["aggregate_case_results"]
    aggregate_payload = load_json(aggregate_case_results)
    case_results = aggregate_payload.get("case_results", [])
    counts = Counter(item.get("status", "UNKNOWN") for item in case_results)
    counts["TOTAL"] = len(case_results)
    cuke_counts = scenario_counts(behave_json)

    out_dir.mkdir(parents=True, exist_ok=True)
    output_payload = {
        "case_results": case_results,
        "counts": dict(counts),
        "cucumber_scenario_counts": dict(cuke_counts),
        "formal_meta": meta,
    }
    (out_dir / "case_results.json").write_text(json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    nonpass = [item for item in case_results if item.get("status") != "PASS"]
    lines = [
        "# 小度 Cucumber 正式全链路报告",
        "",
        f"- Behave JSON：`{rel(behave_json)}`",
        f"- Formal meta：`{rel(meta_path)}`",
        f"- Inner suite：`{meta.get('inner_suite_dir')}`",
        f"- 聚合结果：`{meta.get('aggregate_case_results')}`",
        f"- 正式用例统计：`PASS={counts.get('PASS', 0)} / FAIL={counts.get('FAIL', 0)} / TODO={counts.get('TODO', 0)} / BLOCKED={counts.get('BLOCKED', 0)} / TOTAL={counts.get('TOTAL', 0)}`",
        f"- Cucumber 场景统计：`passed={cuke_counts.get('passed', 0)} / failed={cuke_counts.get('failed', 0)} / blocked={cuke_counts.get('blocked', 0)} / total={cuke_counts.get('total', 0)}`",
        "",
        "## 非 PASS 项",
        "",
    ]
    if nonpass:
        lines.extend(["| 用例 | 状态 | 结论 | 证据 |", "| --- | --- | --- | --- |"])
        for item in nonpass:
            evidence = item.get("evidence", [])
            if isinstance(evidence, list):
                evidence_text = "<br>".join(f"`{entry}`" for entry in evidence[:5])
            else:
                evidence_text = f"`{evidence}`"
            lines.append(f"| `{item.get('case_id')}` | `{item.get('status')}` | {item.get('summary')} | {evidence_text} |")
    else:
        lines.append("- 无")
    lines.extend([
        "",
        "## 说明",
        "",
        "- 本报告由 Cucumber Feature 驱动执行；正式功能动作仍复用 Trisolaris 已收敛的项目 runner/adapter。",
        "- 新增或删除正式用例时，优先调整 `xiaodu_formal_fullflow.feature` 的 Examples 或重新生成该 Feature；step 执行逻辑无需改动。",
        "- Cucumber 场景失败代表实际状态与需求期望不一致；最终 FAIL 仍按 Trisolaris 规则归因到固件问题或需求问题。",
    ])
    (out_dir / "suite_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Xiaodu formal Cucumber run outputs into Trisolaris result files.")
    parser.add_argument("--behave-json", type=Path, required=True)
    parser.add_argument("--formal-meta", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    convert(args.behave_json, args.formal_meta, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
