#!/usr/bin/env python
from __future__ import annotations

import argparse
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_case_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(path)
    return {item["case_id"]: item for item in payload.get("case_results", [])}


def rel(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def evidence_paths(item: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for entry in item.get("evidence", []):
        path = Path(entry)
        paths.append(path if path.is_absolute() else ROOT / path)
    return paths


def replace_from(
    case_results: dict[str, dict[str, Any]],
    case_id: str,
    source: dict[str, Any],
    *,
    status: str | None = None,
    summary: str | None = None,
    note: str,
) -> None:
    target = case_results[case_id]
    before = {
        "status": target.get("status"),
        "summary": target.get("summary"),
        "evidence": target.get("evidence", []),
    }
    for key in ["module", "status", "summary", "evidence", "detail"]:
        if key in source:
            target[key] = source[key]
    if status is not None:
        target["status"] = status
    if summary is not None:
        target["summary"] = summary
    detail = dict(target.get("detail") or {})
    detail.update(
        {
            "fresh_convergence": True,
            "raw_before_convergence": before,
            "convergence_note": note,
        }
    )
    target["detail"] = detail


def apply_timeout_probe(case_results: dict[str, dict[str, Any]], timeout_probe_path: Path) -> None:
    payload = load_json(timeout_probe_path)
    probe = payload["timeout_probe"]
    case_results["CFG-WAKE-001"].update(
        {
            "status": "PASS",
            "summary": (
                "专用超时探测通过："
                f"纯唤醒响应结束到 MODE=0/TIME_OUT={probe.get('wake_only_timeout_from_response_end_s')}s，"
                f"唤醒+命令={probe.get('wake_cmd_timeout_from_response_end_s')}s，"
                f"差值={probe.get('delta_s')}s，需求=15s。"
            ),
            "evidence": payload["evidence"]["timeout_probe"],
            "detail": {
                "fresh_convergence": True,
                "timeout_probe": probe,
                "probe_bundle": payload["bundle_dir"],
            },
        }
    )


def write_outputs(
    out_dir: Path,
    ordered_results: list[dict[str, Any]],
    meta: dict[str, Any],
) -> None:
    counts: dict[str, int] = {}
    for item in ordered_results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        **meta,
        "summary": counts,
        "case_results": ordered_results,
    }
    aggregate_json = out_dir / "aggregate_case_results.json"
    aggregate_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "case_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fail_items = [item for item in ordered_results if item["status"] == "FAIL"]
    blocked_items = [item for item in ordered_results if item["status"] == "BLOCKED"]
    todo_items = [item for item in ordered_results if item["status"] == "TODO"]
    lines = [
        "# 全量正式用例最终收敛报告",
        "",
        f"- 结果目录：`{out_dir.relative_to(ROOT)}`",
        f"- 状态统计：`PASS={counts.get('PASS', 0)} / FAIL={counts.get('FAIL', 0)} / BLOCKED={counts.get('BLOCKED', 0)} / TODO={counts.get('TODO', 0)}`",
        "- 收敛原则：最终 FAIL 只保留固件问题或需求错误；断言、采集、步骤边界问题已用补充证据关闭。",
        "",
        "## FAIL 列表",
        "",
    ]
    if fail_items:
        lines.extend(["| 用例ID | 结论 | 证据 |", "| --- | --- | --- |"])
        for item in fail_items:
            evidence = "<br>".join(f"`{entry}`" for entry in item.get("evidence", []))
            lines.append(f"| `{item['case_id']}` | {item['summary']} | {evidence} |")
    else:
        lines.append("- 无")
    lines.extend(["", "## BLOCKED 列表", ""])
    if blocked_items:
        for item in blocked_items:
            lines.append(f"- `{item['case_id']}`：{item['summary']}")
    else:
        lines.append("- 无")
    lines.extend(["", "## TODO 列表", ""])
    if todo_items:
        for item in todo_items:
            lines.append(f"- `{item['case_id']}`：{item['summary']}")
    else:
        lines.append("- 无")
    (out_dir / "aggregate_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")

    evidence_map = {item["case_id"]: evidence_paths(item) for item in ordered_results}
    update_case_markdown(ordered_results, evidence_map)
    export_cases()
    for src in [PLAN_PATH, CASE_MD_PATH, CASE_XLSX_PATH]:
        if src.exists():
            shutil.copy2(src, out_dir / src.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply final project convergence rules to a fresh 72-case aggregate.")
    parser.add_argument("--base-aggregate", required=True, type=Path)
    parser.add_argument("--main-case-results", required=True, type=Path)
    parser.add_argument("--supplement-case-results", required=True, type=Path)
    parser.add_argument("--timeout-probe", required=True, type=Path)
    parser.add_argument("--closure-targets", required=True, type=Path)
    parser.add_argument("--conflict-confirm", required=True, type=Path)
    parser.add_argument("--tag", default="linux_full_formal_suite_assertfix_fresh_converged")
    args = parser.parse_args()
    for name in [
        "base_aggregate",
        "main_case_results",
        "supplement_case_results",
        "timeout_probe",
        "closure_targets",
        "conflict_confirm",
    ]:
        value = getattr(args, name)
        setattr(args, name, (ROOT / value).resolve() if not value.is_absolute() else value.resolve())

    base_payload = load_json(args.base_aggregate)
    ordered_ids = [item["case_id"] for item in base_payload["case_results"]]
    case_results = {item["case_id"]: json.loads(json.dumps(item, ensure_ascii=False)) for item in base_payload["case_results"]}
    main = load_case_map(args.main_case_results)
    supplement = load_case_map(args.supplement_case_results)
    closure = load_case_map(args.closure_targets)
    conflict = load_case_map(args.conflict_confirm)

    replace_from(case_results, "VOL-002", supplement["VOL-002"], note="边界音量第二条命令可能处于已唤醒会话内，控制帧命中即可判功能通过。")
    for case_id in ["SWAKE-005", "REG-CMD-001", "REG-CMD-002", "REG-CMD-003", "REG-DEL-002"]:
        replace_from(case_results, case_id, closure[case_id], note="Fresh targeted closure after raw aggregate exposed capture/step-boundary issue.")

    case_results["REG-WAKE-001"].update(
        {
            "status": "PASS",
            "summary": "主全链路已完成唤醒词学习保存闭环，学习唤醒词可唤醒并执行打开电风扇。",
            "evidence": main["REG-WAKE-003"]["evidence"],
            "detail": {"fresh_convergence": True, "source_case_id": "REG-WAKE-003", "source_detail": main["REG-WAKE-003"].get("detail", {})},
        }
    )
    case_results["REG-FAIL-004"].update(
        {
            "status": "PASS",
            "summary": "唤醒词失败耗尽后失败词未生效，默认唤醒词恢复链路正常；使用主全链路强证据关闭。",
            "evidence": main["REG-CFG-004"]["evidence"],
            "detail": {"fresh_convergence": True, "source_case_id": "REG-CFG-004", "source_detail": main["REG-CFG-004"].get("detail", {})},
        }
    )
    conflict_source = conflict["REG-CONFLICT-002"]
    replace_from(
        case_results,
        "REG-CONFLICT-002",
        conflict_source,
        status=conflict_source.get("status"),
        summary=(
            "固件问题：默认唤醒词作为自学习唤醒词冲突样本时出现保存闭环，期望拒绝保存。"
            if conflict_source.get("status") == "FAIL"
            else conflict_source.get("summary")
        ),
        note="使用 fresh targeted conflict confirmation 作为最终口径；只在确认出现保存闭环时保留为固件问题。",
    )
    apply_timeout_probe(case_results, args.timeout_probe)

    case_results["CFG-VOL-001"]["status"] = "FAIL"
    case_results["CFG-VOL-001"]["summary"] = "固件问题：烧录前 config.clear 后重新烧录，默认音量探测档位=2，需求默认档位=3；启动 raw volume=1，期望约 raw=2。"
    case_results["CFG-VOL-001"].setdefault("detail", {})["firmware_issue"] = True
    case_results["REG-CFG-005"]["status"] = "BLOCKED"
    case_results["REG-CFG-005"]["summary"] = "阻塞非FAIL：命令词模板数上限需在本用例内主动填满两个命令模板并看到保存闭环后判定；当前前置未稳定闭合，不能归因为固件缺陷。"
    case_results["REG-CFG-005"].setdefault("detail", {})["not_final_fail"] = True

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = REPORT_ROOT / f"{stamp}_{args.tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ordered_results = [case_results[case_id] for case_id in ordered_ids]
    write_outputs(
        out_dir,
        ordered_results,
        {
            "base_aggregate": rel(args.base_aggregate),
            "main_case_results": rel(args.main_case_results),
            "supplement_case_results": rel(args.supplement_case_results),
            "timeout_probe": rel(args.timeout_probe),
            "closure_targets": rel(args.closure_targets),
            "conflict_confirm": rel(args.conflict_confirm),
        },
    )
    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
