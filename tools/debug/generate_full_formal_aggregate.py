#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from run_post_restructure_fullflow import (
    CASE_MD_PATH,
    REPORT_ROOT,
    ROOT,
    export_cases,
    proto_frames_from_hex,
    update_case_markdown,
)


@dataclass
class StepRecord:
    label: str
    status: str
    path: Path | None
    detail: dict[str, Any]
    log_text: str
    proto_hex: str
    proto_frames: list[str]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_formal_case_ids() -> list[str]:
    ids: list[str] = []
    for line in CASE_MD_PATH.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\|\s*`([A-Z0-9-]+)`\s*\|", line)
        if match:
            ids.append(match.group(1))
    return ids


def build_step_records(summary_path: Path) -> dict[str, StepRecord]:
    payload = load_json(summary_path)
    records: dict[str, StepRecord] = {}
    for item in payload.get("items", []):
        label = item["label"]
        rel = item.get("result_dir")
        step_path = ROOT / rel if rel else None
        log_text = ""
        proto_hex = ""
        if step_path:
            for name in ["log_utf8.txt", "serial_utf8.txt", "boot_log_utf8.txt"]:
                candidate = step_path / name
                if candidate.exists():
                    log_text = candidate.read_text(encoding="utf-8", errors="replace")
                    break
            for name in ["proto_hex.txt", "com36_hex.txt"]:
                candidate = step_path / name
                if candidate.exists():
                    proto_hex = candidate.read_text(encoding="utf-8", errors="replace").strip()
                    break
        records[label] = StepRecord(
            label=label,
            status=item.get("status", ""),
            path=step_path,
            detail=item.get("detail") or {},
            log_text=log_text,
            proto_hex=proto_hex,
            proto_frames=proto_frames_from_hex(proto_hex),
        )
    return records


def step_ok(step: StepRecord | None) -> bool:
    return bool(step and step.status == "ok" and step.path and step.path.exists())


def has_playback(step: StepRecord | None) -> bool:
    return bool(step and any(marker in step.log_text for marker in ["play start", "play id :", "play stop"]))


def has_no_playback(step: StepRecord | None) -> bool:
    return not has_playback(step)


def has_control(step: StepRecord | None) -> bool:
    if not step:
        return False
    return any(frame.startswith("A5 FA") and frame not in {"A5 FA 01 BB", "A5 FA 02 BB"} for frame in step.proto_frames)


def has_frame(step: StepRecord | None, frame: str) -> bool:
    return bool(step and frame in step.proto_frames)


def add_eval(
    results: list[dict[str, Any]],
    evidence_map: dict[str, list[Path]],
    case_id: str,
    module: str,
    status: str,
    summary: str,
    evidence: list[Path],
    detail: dict[str, Any] | None = None,
) -> None:
    payload = {
        "case_id": case_id,
        "module": module,
        "status": status,
        "summary": summary,
        "evidence": [str(path.relative_to(ROOT)) for path in evidence],
        "detail": detail or {},
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    results.append(payload)
    evidence_map[case_id] = evidence


def source_case_results(case_results_path: Path) -> tuple[list[dict[str, Any]], dict[str, list[Path]]]:
    payload = load_json(case_results_path)
    results: list[dict[str, Any]] = []
    evidence_map: dict[str, list[Path]] = {}
    for item in payload.get("case_results", []):
        evidence = [ROOT / entry for entry in item.get("evidence", [])]
        results.append(item)
        evidence_map[item["case_id"]] = evidence
    return results, evidence_map


def evaluate_voice_reg_cases(summary_path: Path) -> tuple[list[dict[str, Any]], dict[str, list[Path]]]:
    records = build_step_records(summary_path)
    results: list[dict[str, Any]] = []
    evidence_map: dict[str, list[Path]] = {}

    open_proto = "A5 FA 04 BB"
    close_proto = "A5 FA 05 BB"

    def get(*labels: str) -> list[StepRecord]:
        return [records[label] for label in labels if label in records]

    def evidence(*labels: str) -> list[Path]:
        return [records[label].path for label in labels if label in records and records[label].path]  # type: ignore[list-item]

    cmd_learn = records.get("reg_tc_learn_cmd_close_sequence")
    cmd_save_closure = records.get("reg_tc_learn_cmd_close_save_closure")
    cmd_alias = records.get("reg_tc_learn_cmd_close_alias_recheck")
    cmd_reboot = records.get("reg_tc_learn_cmd_close_persist_reboot")
    cmd_alias_after = records.get("reg_tc_learn_cmd_close_after_reboot_alias")
    cmd_save_text = (cmd_learn.log_text if cmd_learn else "") + "\n" + (cmd_save_closure.log_text if cmd_save_closure else "")
    cmd_save_ok = any(marker in cmd_save_text for marker in ["save new voice.bin", "reg cmd over success", "save config success"])
    add_eval(
        results,
        evidence_map,
        "REG-CMD-001",
        "语音注册-命令词",
        "PASS" if step_ok(cmd_learn) and cmd_save_ok and has_frame(cmd_alias, close_proto) else "FAIL",
        "学习命令词保存闭环后，别名可触发目标功能",
        evidence("reg_tc_learn_cmd_close_sequence", "reg_tc_learn_cmd_close_save_closure", "reg_tc_learn_cmd_close_persist_reboot", "reg_tc_learn_cmd_close_alias_recheck"),
    )
    add_eval(
        results,
        evidence_map,
        "REG-CMD-002",
        "语音注册-命令词",
        "PASS" if step_ok(cmd_reboot) and has_frame(cmd_alias_after, close_proto) else "FAIL",
        "学习命令词重启后仍可触发目标功能",
        evidence("reg_tc_learn_cmd_close_sequence", "reg_tc_learn_cmd_close_save_closure", "reg_tc_learn_cmd_close_persist_reboot", "reg_tc_learn_cmd_close_after_reboot_alias"),
    )

    wake_learn = records.get("reg_voice002_learn_wakeup_sequence")
    wake_recheck = records.get("reg_voice002_learned_wake_recheck_open")
    wake_default = records.get("reg_voice002_default_wake_still_open_ok")
    add_eval(
        results,
        evidence_map,
        "REG-WAKE-001",
        "语音注册-唤醒词",
        "PASS" if step_ok(wake_learn) and "save config success" in wake_learn.log_text and has_frame(wake_recheck, open_proto) else "FAIL",
        "学习唤醒词后现场可继续执行打开电风扇",
        evidence("reg_voice002_learn_wakeup_sequence", "reg_voice002_learned_wake_recheck_open"),
    )
    add_eval(
        results,
        evidence_map,
        "REG-WAKE-002",
        "语音注册-唤醒词",
        "PASS" if has_frame(wake_default, open_proto) else "FAIL",
        "学习唤醒词后默认唤醒词仍可用",
        evidence("reg_voice002_learn_wakeup_sequence", "reg_voice002_default_wake_still_open_ok"),
    )

    flow_prev = records.get("reg_tc_learn_prev_boundary")
    flow_next = records.get("reg_tc_learn_next_boundary_full")
    flow_ok = (
        step_ok(flow_prev)
        and step_ok(flow_next)
        and ("xue xi xia yi ge" in flow_next.log_text or "reg auto next!" in flow_next.log_text or "reg over!" in flow_next.log_text)
    )
    add_eval(
        results,
        evidence_map,
        "REG-FLOW-001",
        "语音注册-流程",
        "PASS" if flow_ok else "FAIL",
        "连续学习流程边界已执行并看到流程推进日志",
        evidence("reg_tc_learn_prev_boundary", "reg_tc_learn_next_boundary_full"),
    )

    save_wake = records.get("reg_tc_learn003_learn_wakeup_sequence")
    save_cmd = records.get("reg_tc_learn003_learn_cmd_full_sequence")
    save_pre = records.get("reg_tc_learn003_pre_powercycle_recheck")
    save_boot = records.get("reg_tc_learn003_powercycle_boot")
    save_post = records.get("reg_tc_learn003_post_powercycle_recheck")
    save_ok = (
        step_ok(save_wake)
        and step_ok(save_cmd)
        and has_frame(save_pre, open_proto)
        and has_frame(save_post, open_proto)
        and has_control(save_post)
        and step_ok(save_boot)
    )
    add_eval(
        results,
        evidence_map,
        "REG-SAVE-001",
        "语音注册-保持",
        "PASS" if save_ok else "FAIL",
        "学习结果掉电前后复测链路完整",
        evidence(
            "reg_tc_learn003_learn_wakeup_sequence",
            "reg_tc_learn003_learn_cmd_full_sequence",
            "reg_tc_learn003_pre_powercycle_recheck",
            "reg_tc_learn003_powercycle_boot",
            "reg_tc_learn003_post_powercycle_recheck",
        ),
    )

    fail_cmd_recover = records.get("reg_voice003_cmd_retry_recover_sequence")
    fail_cmd_recover_alias = records.get("reg_voice003_cmd_retry_recover_alias_recheck")
    add_eval(
        results,
        evidence_map,
        "REG-FAIL-001",
        "语音注册-失败恢复",
        "PASS"
        if step_ok(fail_cmd_recover)
        and "reg simila error!" in fail_cmd_recover.log_text
        and "reg again!" in fail_cmd_recover.log_text
        and has_control(fail_cmd_recover_alias)
        else "FAIL",
        "命令词失败重试后恢复成功",
        evidence("reg_voice003_cmd_retry_recover_sequence", "reg_voice003_cmd_retry_recover_alias_recheck"),
    )

    fail_wake_recover = records.get("reg_voice004_wakeup_retry_recover_sequence")
    fail_wake_recover_open = records.get("reg_voice004_wakeup_retry_recover_recheck_open")
    fail_wake_recover_default = records.get("reg_voice004_wakeup_retry_recover_default_wake_ok")
    add_eval(
        results,
        evidence_map,
        "REG-FAIL-002",
        "语音注册-失败恢复",
        "PASS"
        if step_ok(fail_wake_recover)
        and "reg simila error!" in fail_wake_recover.log_text
        and has_frame(fail_wake_recover_open, open_proto)
        and has_frame(fail_wake_recover_default, open_proto)
        else "FAIL",
        "唤醒词失败重试后恢复成功",
        evidence(
            "reg_voice004_wakeup_retry_recover_sequence",
            "reg_voice004_wakeup_retry_recover_recheck_open",
            "reg_voice004_wakeup_retry_recover_default_wake_ok",
        ),
    )

    fail_cmd_exhaust = records.get("reg_voice005_cmd_retry_exhaust_sequence")
    fail_cmd_exhaust_probe = records.get("reg_voice005_cmd_retry_exhaust_failed_alias_probe")
    fail_cmd_text = (fail_cmd_exhaust.log_text if fail_cmd_exhaust else "") + "\n" + (fail_cmd_exhaust_probe.log_text if fail_cmd_exhaust_probe else "")
    fail_cmd_closed = "reg failed!" in fail_cmd_text or "error cnt >" in fail_cmd_text
    add_eval(
        results,
        evidence_map,
        "REG-FAIL-003",
        "语音注册-失败耗尽",
        "PASS" if step_ok(fail_cmd_exhaust) and fail_cmd_closed and not has_control(fail_cmd_exhaust_probe) else "FAIL",
        "命令词失败耗尽后学习别名未生效",
        evidence("reg_voice005_cmd_retry_exhaust_sequence", "reg_voice005_cmd_retry_exhaust_failed_alias_probe"),
    )

    fail_wake_exhaust = records.get("reg_voice006_wakeup_retry_exhaust_sequence")
    fail_wake_exhaust_probe = records.get("reg_voice006_wakeup_retry_exhaust_failed_wake_probe")
    fail_wake_exhaust_default = records.get("reg_voice006_wakeup_retry_exhaust_default_wake_ok")
    add_eval(
        results,
        evidence_map,
        "REG-FAIL-004",
        "语音注册-失败耗尽",
        "PASS"
        if step_ok(fail_wake_exhaust)
        and "reg simila error!" in fail_wake_exhaust.log_text
        and not has_control(fail_wake_exhaust_probe)
        and has_frame(fail_wake_exhaust_default, open_proto)
        else "FAIL",
        "唤醒词失败耗尽后默认唤醒链路仍正常",
        evidence(
            "reg_voice006_wakeup_retry_exhaust_sequence",
            "reg_voice006_wakeup_retry_exhaust_failed_wake_probe",
            "reg_voice006_wakeup_retry_exhaust_default_wake_ok",
        ),
    )

    conflict_default = records.get("reg_voice008_wakeup_conflict_default_xiaodu")
    add_eval(
        results,
        evidence_map,
        "REG-CONFLICT-002",
        "语音注册-冲突词",
        "PASS" if step_ok(conflict_default) and "save config success" not in conflict_default.log_text else "FAIL",
        "默认唤醒词学习冲突未被保存",
        evidence("reg_voice008_wakeup_conflict_default_xiaodu"),
    )

    conflict_reserved_cmd = records.get("reg_voice009_cmd_reserved_learn_wakeup_word")
    add_eval(
        results,
        evidence_map,
        "REG-CONFLICT-003",
        "语音注册-冲突词",
        "PASS" if step_ok(conflict_reserved_cmd) and "save config success" not in conflict_reserved_cmd.log_text else "FAIL",
        "保留入口词学习成命令词时未被保存",
        evidence("reg_voice009_cmd_reserved_learn_wakeup_word"),
    )

    conflict_reserved_wake = records.get("reg_voice010_wakeup_reserved_learn_cmd_word")
    add_eval(
        results,
        evidence_map,
        "REG-CONFLICT-004",
        "语音注册-冲突词",
        "PASS" if step_ok(conflict_reserved_wake) and "save config success" not in conflict_reserved_wake.log_text else "FAIL",
        "保留入口词学习成唤醒词时未被保存",
        evidence("reg_voice010_wakeup_reserved_learn_cmd_word"),
    )

    del_cmd_exit = records.get("reg_delete_cmd_exit_keep")
    del_cmd_exit_alias = records.get("reg_delete_cmd_exit_keep_alias_recheck")
    add_eval(
        results,
        evidence_map,
        "REG-DEL-002",
        "语音注册-删除",
        "PASS" if step_ok(del_cmd_exit) and has_control(del_cmd_exit_alias) else "FAIL",
        "退出删除命令词后学习结果仍保留",
        evidence("reg_delete_cmd_exit_keep", "reg_delete_cmd_exit_keep_alias_recheck"),
    )

    del_cmd_confirm = records.get("reg_delete_cmd_confirm_sequence")
    del_cmd_blocked = records.get("reg_delete_cmd_confirm_alias_blocked")
    del_cmd_default = records.get("reg_delete_cmd_confirm_default_close_ok")
    add_eval(
        results,
        evidence_map,
        "REG-DEL-001",
        "语音注册-删除",
        "PASS" if step_ok(del_cmd_confirm) and not has_control(del_cmd_blocked) and has_frame(del_cmd_default, close_proto) else "FAIL",
        "删除命令词后学习别名失效，默认命令恢复",
        evidence("reg_delete_cmd_confirm_sequence", "reg_delete_cmd_confirm_alias_blocked", "reg_delete_cmd_confirm_default_close_ok"),
    )

    del_wake_exit = records.get("reg_voice014_delete_wakeup_exit_keep")
    del_wake_exit_recheck = records.get("reg_voice014_delete_wakeup_exit_keep_recheck")
    add_eval(
        results,
        evidence_map,
        "REG-DEL-004",
        "语音注册-删除",
        "PASS" if step_ok(del_wake_exit) and has_frame(del_wake_exit_recheck, open_proto) else "FAIL",
        "退出删除唤醒词后学习结果仍保留",
        evidence("reg_voice014_delete_wakeup_exit_keep", "reg_voice014_delete_wakeup_exit_keep_recheck"),
    )

    del_wake_confirm = records.get("reg_voice013_delete_wakeup_confirm_sequence")
    del_wake_blocked = records.get("reg_voice013_delete_wakeup_confirm_learned_wake_blocked")
    del_wake_reboot = records.get("reg_voice013_delete_wakeup_confirm_reboot_after_delete")
    del_wake_default = records.get("reg_voice013_delete_wakeup_confirm_default_wake_ok")
    add_eval(
        results,
        evidence_map,
        "REG-DEL-003",
        "语音注册-删除",
        "PASS" if step_ok(del_wake_confirm) and step_ok(del_wake_reboot) and not has_control(del_wake_blocked) and has_frame(del_wake_default, open_proto) else "FAIL",
        "删除唤醒词后学习唤醒词失效，默认唤醒词恢复",
        evidence(
            "reg_voice013_delete_wakeup_confirm_sequence",
            "reg_voice013_delete_wakeup_confirm_reboot_after_delete",
            "reg_voice013_delete_wakeup_confirm_learned_wake_blocked",
            "reg_voice013_delete_wakeup_confirm_default_wake_ok",
        ),
    )

    return results, evidence_map


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-case-results", required=True, type=Path)
    parser.add_argument("--supplement-case-results", required=True, type=Path)
    parser.add_argument("--voice-summary", required=True, type=Path)
    parser.add_argument("--tag", default="linux_full_formal_suite")
    args = parser.parse_args()
    args.main_case_results = (ROOT / args.main_case_results).resolve() if not args.main_case_results.is_absolute() else args.main_case_results.resolve()
    args.supplement_case_results = (ROOT / args.supplement_case_results).resolve() if not args.supplement_case_results.is_absolute() else args.supplement_case_results.resolve()
    args.voice_summary = (ROOT / args.voice_summary).resolve() if not args.voice_summary.is_absolute() else args.voice_summary.resolve()

    formal_ids = extract_formal_case_ids()
    main_results, main_evidence = source_case_results(args.main_case_results)
    supplement_results, supplement_evidence = source_case_results(args.supplement_case_results)
    voice_results, voice_evidence = evaluate_voice_reg_cases(args.voice_summary)

    merged: dict[str, dict[str, Any]] = {}
    evidence_map: dict[str, list[Path]] = {}
    for items, local_evidence in [
        (main_results, main_evidence),
        (supplement_results, supplement_evidence),
        (voice_results, voice_evidence),
    ]:
        for item in items:
            case_id = item["case_id"]
            if case_id not in formal_ids:
                continue
            merged[case_id] = item
            if case_id in local_evidence:
                evidence_map[case_id] = local_evidence[case_id]

    missing = [case_id for case_id in formal_ids if case_id not in merged]
    for case_id in missing:
        merged[case_id] = {
            "case_id": case_id,
            "module": "未归档",
            "status": "TODO",
            "summary": "本轮聚合时缺少结果，请回查对应执行链路",
            "evidence": [],
            "detail": {},
            "at": datetime.now().isoformat(timespec="seconds"),
        }
        evidence_map[case_id] = []

    ordered_results = [merged[case_id] for case_id in formal_ids]

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = REPORT_ROOT / f"{stamp}_{args.tag}"
    out_dir.mkdir(parents=True, exist_ok=True)

    case_results_path = out_dir / "aggregate_case_results.json"
    case_results_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "main_case_results": str(args.main_case_results.relative_to(ROOT)),
                "supplement_case_results": str(args.supplement_case_results.relative_to(ROOT)),
                "voice_summary": str(args.voice_summary.relative_to(ROOT)),
                "case_results": ordered_results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    pass_count = sum(1 for item in ordered_results if item["status"] == "PASS")
    fail_items = [item for item in ordered_results if item["status"] == "FAIL"]
    todo_items = [item for item in ordered_results if item["status"] == "TODO"]
    blocked_items = [item for item in ordered_results if item["status"] == "BLOCKED"]

    lines = [
        "# 全量正式用例聚合报告",
        "",
        f"- 聚合目录：`{out_dir.relative_to(ROOT)}`",
        f"- 主全链路结果：`{args.main_case_results.relative_to(ROOT)}`",
        f"- 缺失非注册补充结果：`{args.supplement_case_results.relative_to(ROOT)}`",
        f"- 语音注册补充结果：`{args.voice_summary.relative_to(ROOT)}`",
        f"- 本轮正式用例统计：`PASS={pass_count}`、`FAIL={len(fail_items)}`、`TODO={len(todo_items)}`、`BLOCKED={len(blocked_items)}`",
        "",
        "## FAIL 列表",
        "",
    ]
    if fail_items:
        for item in fail_items:
            evidence = item.get("evidence") or []
            evidence_text = evidence[0] if evidence else "见聚合 JSON"
            lines.append(f"- `{item['case_id']}`：{item['summary']}；证据：`{evidence_text}`")
    else:
        lines.append("- 无")

    if todo_items:
        lines.extend(["", "## TODO 列表", ""])
        for item in todo_items:
            lines.append(f"- `{item['case_id']}`：{item['summary']}")

    if blocked_items:
        lines.extend(["", "## BLOCKED 列表", ""])
        for item in blocked_items:
            lines.append(f"- `{item['case_id']}`：{item['summary']}")

    (out_dir / "aggregate_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "aggregate_meta.json").write_text(
        json.dumps(
            {
                "main_case_results": str(args.main_case_results.relative_to(ROOT)),
                "supplement_case_results": str(args.supplement_case_results.relative_to(ROOT)),
                "voice_summary": str(args.voice_summary.relative_to(ROOT)),
                "counts": {
                    "PASS": pass_count,
                    "FAIL": len(fail_items),
                    "TODO": len(todo_items),
                    "BLOCKED": len(blocked_items),
                },
                "missing_formal_ids": missing,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    update_case_markdown(ordered_results, evidence_map)
    export_cases()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
