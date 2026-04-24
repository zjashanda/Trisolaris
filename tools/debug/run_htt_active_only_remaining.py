#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import run_htt_active_passive_playid_sweep as sweep


RESULT_ROOT = sweep.RESULT_ROOT
DELIVERABLE_ROOT = sweep.DELIVERABLE_ROOT

WAKE = "小好小好"
DEFAULT_NOTES = "当前需求无固定 MCU -> CSK 被动回包定义，本轮只收敛到“唤醒 -> 识别 -> 主动协议”。"


def active_only_case(case_id: str, title: str, text: str, active_word: int, notes: str = "") -> sweep.SweepCase:
    return sweep.SweepCase(
        case_id=case_id,
        title=title,
        group="active-only",
        texts=[WAKE, text],
        expected_active_words=[0x0001, active_word],
        capture_s=22.0,
        initial_wait_s=18.0,
        between_wait_s=1.8,
        # This suite often runs after persistence / voice-state checks, so each
        # case restores a known voice-on baseline before probing the command.
        baseline_reset=True,
        require_response_play=False,
        notes=notes or DEFAULT_NOTES,
    )


CASES: list[sweep.SweepCase] = [
    active_only_case("ACTIVE-CLOTHES-GEAR-ON-001", "打开晾晒档主动侧", "打开晾晒档", 0x0070),
    active_only_case("ACTIVE-CLOTHES-GEAR-OFF-001", "关闭晾晒档主动侧", "关闭晾晒档", 0x0071),
    active_only_case("ACTIVE-TOP-001", "上升到顶部主动侧", "上升到顶部", 0x0073),
    active_only_case("ACTIVE-HIDE-001", "晾杆隐藏主动侧", "晾杆隐藏", 0x0072),
    active_only_case("ACTIVE-BOTTOM-001", "下降到底部主动侧", "下降到底部", 0x0082),
    active_only_case("ACTIVE-UP-SMALL-001", "上升一点主动侧", "上升一点", 0x0080),
    active_only_case("ACTIVE-DOWN-SMALL-001", "下降一点主动侧", "下降一点", 0x0081),
    active_only_case("ACTIVE-SENSOR-ON-001", "打开感应主动侧", "打开感应", 0x0074),
    active_only_case("ACTIVE-SENSOR-OFF-001", "关闭感应主动侧", "关闭感应", 0x0075),
    active_only_case("ACTIVE-SCENE-CLOSE-CLOTHES-001", "关闭晾衣模式主动侧", "关闭晾衣模式", 0x0067),
    active_only_case("ACTIVE-SCENE-CLOSE-LEISURE-001", "关闭休闲模式主动侧", "关闭休闲模式", 0x0068),
    active_only_case("ACTIVE-SCENE-CLOSE-GARDEN-001", "关闭园艺模式主动侧", "关闭园艺模式", 0x006A),
    active_only_case("ACTIVE-AMBIENT-ON-001", "打开氛围灯主动侧", "打开氛围灯", 0x0030),
    active_only_case("ACTIVE-AMBIENT-OFF-001", "关闭氛围灯主动侧", "关闭氛围灯", 0x0031),
    active_only_case("ACTIVE-SKY-001", "打开晴空模式主动侧", "打开晴空模式", 0x0032),
    active_only_case("ACTIVE-SUNSET-001", "打开日落模式主动侧", "打开日落模式", 0x0033),
    active_only_case("ACTIVE-DOPAMINE-001", "打开多巴胺模式主动侧", "打开多巴胺模式", 0x0034),
    active_only_case("ACTIVE-FLOWER-001", "打开花海模式主动侧", "打开花海模式", 0x0035),
    active_only_case("ACTIVE-TIPSY-001", "打开微醺模式主动侧", "打开微醺模式", 0x0036, notes="迭代新增别名，要求逻辑同彩虹模式。"),
    active_only_case("ACTIVE-RAINBOW-001", "打开彩虹模式主动侧", "打开彩虹模式", 0x0036, notes="与“打开微醺模式”同协议，用于补齐旧词条别名。"),
    active_only_case("ACTIVE-AURORA-001", "打开极光模式主动侧", "打开极光模式", 0x0037),
]


def write_cases_md(path: Path, selected_cases: list[sweep.SweepCase]) -> None:
    lines = [
        "# 好太太晾衣机剩余 active-only 命令用例",
        "",
        "| 用例ID | 标题 | 语音输入 | 期望主动协议 | 备注 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in selected_cases:
        expected = " / ".join(sweep.base.active_frame_hex(word) for word in case.expected_active_words)
        lines.append(f"| `{case.case_id}` | {case.title} | {' / '.join(case.texts)} | {expected} | {case.notes or '-'} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_report_md(path: Path, suite_name: str, suite_dir: Path, results: list[dict[str, Any]]) -> None:
    pass_count = sum(1 for item in results if item["status"] == "PASS")
    fail_count = sum(1 for item in results if item["status"] == "FAIL")
    blocked_count = sum(1 for item in results if item["status"] == "BLOCKED")
    lines = [
        "# 好太太晾衣机剩余 active-only 命令报告",
        "",
        f"- 套件名称：`{suite_name}`",
        f"- 原始结果目录：`{suite_dir}`",
        "- 口径说明：这些功能当前没有固定 MCU -> CSK 被动回包定义，因此本轮只收敛到“唤醒 -> 识别 -> CSK 主动协议”。",
        f"- 总计：`{len(results)}` 条；PASS=`{pass_count}`，FAIL=`{fail_count}`，BLOCKED=`{blocked_count}`",
        "",
        "## 明细",
        "",
    ]
    for item in results:
        lines.append(f"### {item['case_id']} {item['title']}")
        lines.append(f"- 结果：`{item['status']}`")
        lines.append(f"- 结果目录：`{item['result_dir']}`")
        if item["status"] == "BLOCKED":
            lines.append(f"- 原因：{item.get('reason', '')}")
        else:
            lines.append(f"- 期望主动协议：{', '.join(item.get('expected_active_words', [])) or '无'}")
            lines.append(f"- 观测主动协议：{', '.join(item.get('observed_active_words', [])) or '无'}")
            if item.get("missing_markers"):
                lines.append(f"- 缺失日志标记：{', '.join(item['missing_markers'])}")
            if item.get("forbidden_marker_hits"):
                lines.append(f"- 命中禁止日志：{', '.join(item['forbidden_marker_hits'])}")
        if item.get("notes"):
            lines.append(f"- 备注：{item['notes']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HTT active-only remaining command cases.")
    parser.add_argument("--case-id", dest="case_ids", action="append", help="Run only the specified case id.")
    parser.add_argument("--suite-tag", default="", help="Optional suffix appended to the suite directory name.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected_cases = CASES
    if args.case_ids:
        wanted_ids = {item.strip().upper() for item in args.case_ids if item.strip()}
        selected_cases = [case for case in selected_cases if case.case_id.upper() in wanted_ids]
        missing = sorted(wanted_ids - {case.case_id.upper() for case in selected_cases})
        if missing:
            raise SystemExit(f"Unknown case id(s): {', '.join(missing)}")
    if not selected_cases:
        raise SystemExit("No cases selected.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_name = f"{timestamp}_htt_active_only_remaining_r1"
    if args.suite_tag:
        suite_name = f"{suite_name}_{args.suite_tag}"
    suite_dir = RESULT_ROOT / suite_name
    suite_dir.mkdir(parents=True, exist_ok=True)

    play_script = sweep.base.resolve_listenai_play(update=False)
    results: list[dict[str, Any]] = []
    for case in selected_cases:
        results.append(sweep.run_case(case, suite_dir, play_script))

    summary = {
        "suite_name": suite_name,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "device_key": sweep.base.DEVICE_KEY,
        "ctrl_port": sweep.base.CTRL_PORT,
        "log_port": sweep.base.LOG_PORT,
        "proto_port": sweep.base.PROTO_PORT,
        "selected_case_ids": [case.case_id for case in selected_cases],
        "results": results,
    }
    (suite_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    (DELIVERABLE_ROOT / "cases").mkdir(parents=True, exist_ok=True)
    (DELIVERABLE_ROOT / "reports").mkdir(parents=True, exist_ok=True)
    cases_path = DELIVERABLE_ROOT / "cases" / "20260423_剩余active_only命令_v1.md"
    report_dir = DELIVERABLE_ROOT / "reports" / suite_name
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "summary.md"

    write_cases_md(cases_path, selected_cases)
    write_report_md(report_path, suite_name, suite_dir, results)
    print(json.dumps({"suite_name": suite_name, "suite_dir": str(suite_dir), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
