#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def case_id_from_scenario(scenario: dict[str, Any]) -> str:
    for tag in scenario.get("tags", []):
        if tag.startswith("case_id:"):
            return tag.split(":", 1)[1]
    match = re.search(r"([A-Z0-9]+(?:-[A-Z0-9]+)+)", scenario.get("name", ""))
    return match.group(1) if match else scenario.get("name", "UNKNOWN")


def scenario_status(scenario: dict[str, Any]) -> str:
    statuses = []
    for step in scenario.get("steps", []):
        result = step.get("result") or {}
        statuses.append(result.get("status", "untested"))
    if any(status in {"failed", "error"} for status in statuses):
        return "FAIL"
    if any(status in {"skipped", "untested"} for status in statuses):
        return "BLOCKED"
    return "PASS"


def first_error(scenario: dict[str, Any]) -> str:
    for step in scenario.get("steps", []):
        result = step.get("result") or {}
        if result.get("status") in {"failed", "error"}:
            return result.get("error_message", "")
    return ""


def scenario_evidence_path(evidence_index: list[dict[str, Any]], scenario_name: str) -> str:
    for item in evidence_index:
        if item.get("scenario") == scenario_name:
            return item.get("dir", "")
    return ""


def convert(behave_json: Path, evidence_index_path: Path | None, out_dir: Path) -> dict[str, Any]:
    payload = json.loads(behave_json.read_text(encoding="utf-8"))
    evidence_index = []
    if evidence_index_path and evidence_index_path.exists():
        evidence_index = json.loads(evidence_index_path.read_text(encoding="utf-8"))

    results: list[dict[str, Any]] = []
    for feature in payload:
        for element in feature.get("elements", []):
            if element.get("type") != "scenario":
                continue
            case_id = case_id_from_scenario(element)
            status = scenario_status(element)
            evidence = scenario_evidence_path(evidence_index, element.get("name", ""))
            tags = element.get("tags", [])
            module = "cucumber-minimal"
            if case_id.startswith("NATIVE-") or any(tag in {"native", "module:volume-level"} for tag in tags):
                module = "cucumber-native"
            elif any("wake" in tag for tag in tags):
                module = "wake-session"
            item = {
                "case_id": case_id,
                "module": module,
                "status": status,
                "title": element.get("name", ""),
                "evidence": evidence,
                "raw_status": status,
                "attribution": "pending" if status == "FAIL" else "none",
                "error": first_error(element),
                "tags": tags,
            }
            results.append(item)

    counts = Counter(item["status"] for item in results)
    counts["TOTAL"] = len(results)
    out_dir.mkdir(parents=True, exist_ok=True)
    case_payload = {"case_results": results, "counts": dict(counts)}
    (out_dir / "case_results.json").write_text(json.dumps(case_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 小度 Cucumber 验证报告",
        "",
        f"- Behave JSON：`{rel(behave_json)}`",
        f"- 证据索引：`{rel(evidence_index_path) if evidence_index_path else ''}`",
        f"- 统计：`PASS={counts.get('PASS', 0)} / FAIL={counts.get('FAIL', 0)} / BLOCKED={counts.get('BLOCKED', 0)} / TOTAL={counts.get('TOTAL', 0)}`",
        "",
        "## 用例结果",
        "",
        "| 用例 | 状态 | 标题 | 证据 |",
        "| --- | --- | --- | --- |",
    ]
    for item in results:
        lines.append(f"| `{item['case_id']}` | `{item['status']}` | {item['title']} | `{item['evidence']}` |")
    nonpass = [item for item in results if item["status"] != "PASS"]
    if nonpass:
        lines.extend(["", "## 非 PASS 项", ""])
        for item in nonpass:
            lines.append(f"- `{item['case_id']}`：`{item['status']}`，{item.get('error') or '无错误详情'}")
    (out_dir / "suite_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return case_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--behave-json", type=Path, required=True)
    parser.add_argument("--evidence-index", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    convert(args.behave_json, args.evidence_index, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
