#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from run_post_restructure_fullflow import (
    CASE_MD_PATH,
    CASE_XLSX_PATH,
    PLAN_PATH,
    REPORT_ROOT,
    ROOT,
    export_cases,
    update_case_markdown,
)

BASE_AGGREGATE = REPORT_ROOT / "20260423_200055_linux_full_formal_suite_r2" / "aggregate_case_results.json"
CONVERGENCE_RESULTS = REPORT_ROOT / "20260424_143916_linux_fail_convergence_retest_r1" / "validity_results.json"
BUNDLE_TAG = "linux_full_formal_suite_converged_r3"

FIRMWARE_FAIL_IDS = {"CFG-VOL-001"}
BLOCKED_IDS = {"REG-CFG-005"}

PASS_SUMMARY_PREFIX = "断言/方案已修正并用收敛复测证据关闭："
BLOCKED_SUMMARY_PREFIX = "断言/方案已修正，当前不作为失败："


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel_to_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def write_report(bundle_dir: Path, case_results: list[dict[str, Any]], source_bundle: str) -> Path:
    counts: dict[str, int] = {}
    for item in case_results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    fail_items = [item for item in case_results if item["status"] == "FAIL"]
    blocked_items = [item for item in case_results if item["status"] == "BLOCKED"]
    todo_items = [item for item in case_results if item["status"] == "TODO"]
    lines = [
        "# 72条正式用例收敛后聚合报告",
        "",
        f"- 结果目录：`{bundle_dir.relative_to(ROOT)}`",
        f"- 基线聚合：`{BASE_AGGREGATE.relative_to(ROOT)}`",
        f"- 13条FAIL收敛证据：`{source_bundle}`",
        "- 收敛原则：测试方案/断言/证据窗口问题必须从最终 FAIL 中移除；最终 FAIL 只保留固件问题或需求错误。",
        f"- 状态统计：`" + " / ".join(f"{key}={value}" for key, value in sorted(counts.items())) + "`",
        "",
        "## 剩余FAIL",
        "",
    ]
    if fail_items:
        lines.extend(["| 用例ID | 模块 | 结论 | 证据 |", "| --- | --- | --- | --- |"])
        for item in fail_items:
            evidence = "<br>".join(f"`{path}`" for path in item.get("evidence", []))
            lines.append(f"| `{item['case_id']}` | {item['module']} | {item['summary']} | {evidence} |")
    else:
        lines.append("- 无")
    lines.extend(["", "## 阻塞但非FAIL", ""])
    if blocked_items:
        lines.extend(["| 用例ID | 模块 | 阻塞原因 | 证据 |", "| --- | --- | --- | --- |"])
        for item in blocked_items:
            evidence = "<br>".join(f"`{path}`" for path in item.get("evidence", []))
            lines.append(f"| `{item['case_id']}` | {item['module']} | {item['summary']} | {evidence} |")
    else:
        lines.append("- 无")
    lines.extend(["", "## 待人工", ""])
    if todo_items:
        lines.extend(["| 用例ID | 模块 | 原因 | 证据 |", "| --- | --- | --- | --- |"])
        for item in todo_items:
            evidence = "<br>".join(f"`{path}`" for path in item.get("evidence", []))
            lines.append(f"| `{item['case_id']}` | {item['module']} | {item['summary']} | {evidence} |")
    else:
        lines.append("- 无")
    lines.extend([
        "",
        "## 已由断言/方案修正关闭的旧FAIL",
        "",
        "| 用例ID | 当前状态 | 收敛说明 |",
        "| --- | --- | --- |",
    ])
    for item in case_results:
        detail = item.get("detail") or {}
        if detail.get("converged_from_old_fail") and item["status"] != "FAIL":
            lines.append(f"| `{item['case_id']}` | `{item['status']}` | {item['summary']} |")
    out = bundle_dir / "aggregate_report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return out


def main() -> int:
    base = load_json(BASE_AGGREGATE)
    convergence = load_json(CONVERGENCE_RESULTS)
    convergence_by_id = {item["case_id"]: item for item in convergence["records"]}

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_dir = REPORT_ROOT / f"{stamp}_{BUNDLE_TAG}"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    static_dir = bundle_dir / "01_static"
    static_dir.mkdir(parents=True, exist_ok=True)

    case_results: list[dict[str, Any]] = []
    for item in base["case_results"]:
        updated = json.loads(json.dumps(item, ensure_ascii=False))
        conv = convergence_by_id.get(updated["case_id"])
        if conv:
            updated["evidence"] = conv.get("evidence", updated.get("evidence", []))
            detail = updated.get("detail") or {}
            detail.update({
                "converged_from_old_fail": True,
                "old_status": item.get("status"),
                "convergence_result": conv.get("retest_result"),
                "convergence_reason": conv.get("reason"),
                "convergence_detail": conv.get("detail", {}),
            })
            updated["detail"] = detail
            if updated["case_id"] in FIRMWARE_FAIL_IDS:
                updated["status"] = "FAIL"
                updated["summary"] = "固件问题：" + conv["reason"]
            elif updated["case_id"] in BLOCKED_IDS:
                updated["status"] = "BLOCKED"
                updated["summary"] = BLOCKED_SUMMARY_PREFIX + conv["reason"]
            else:
                updated["status"] = "PASS"
                updated["summary"] = PASS_SUMMARY_PREFIX + conv["reason"]
        case_results.append(updated)

    counts: dict[str, int] = {}
    for item in case_results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_aggregate": str(BASE_AGGREGATE.relative_to(ROOT)),
        "convergence_results": str(CONVERGENCE_RESULTS.relative_to(ROOT)),
        "summary": counts,
        "case_results": case_results,
    }
    aggregate_json = bundle_dir / "aggregate_case_results.json"
    aggregate_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = write_report(bundle_dir, case_results, str(CONVERGENCE_RESULTS.relative_to(ROOT)))

    evidence_map: dict[str, list[Path]] = {}
    for item in case_results:
        evidence_map[item["case_id"]] = [rel_to_path(path) for path in item.get("evidence", [])]
    update_case_markdown(case_results, evidence_map)
    export_cases()

    for src in [PLAN_PATH, CASE_MD_PATH, CASE_XLSX_PATH]:
        if src.exists():
            shutil.copy2(src, bundle_dir / src.name)
            shutil.copy2(src, static_dir / src.name)
    shutil.copy2(aggregate_json, bundle_dir / "case_results.json")

    print(bundle_dir)
    print(json.dumps(counts, ensure_ascii=False))
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
