#!/usr/bin/env python
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import run_htt_active_passive_playid_sweep as sweep


RESULT_ROOT = sweep.RESULT_ROOT
DELIVERABLE_ROOT = sweep.DELIVERABLE_ROOT
WAKE = "小好小好"


@dataclass(frozen=True)
class ProbeGroup:
    group_id: str
    title: str
    active_word: int
    phrases: list[str]
    notes: str = ""


PROBE_GROUPS: list[ProbeGroup] = [
    ProbeGroup("PHRASE-CLOTHES-GEAR-ON", "打开晾晒档别名探测", 0x0070, ["打开晾晒档", "开启晾晒档", "晾晒档开启"]),
    ProbeGroup("PHRASE-CLOTHES-GEAR-OFF", "关闭晾晒档别名探测", 0x0071, ["关闭晾晒档", "关掉晾晒档", "关闭两档上升"]),
    ProbeGroup("PHRASE-UP-SMALL", "上升一点别名探测", 0x0080, ["上升一点", "往上一点", "高一点"]),
    ProbeGroup("PHRASE-DOWN-SMALL", "下降一点别名探测", 0x0081, ["下降一点", "往下一点", "低一点"]),
    ProbeGroup("PHRASE-SENSOR-ON", "打开感应别名探测", 0x0074, ["打开感应", "打开感应模式", "打开人体感应"]),
    ProbeGroup("PHRASE-SENSOR-OFF", "关闭感应别名探测", 0x0075, ["关闭感应", "关闭感应模式", "关闭人体感应"]),
    ProbeGroup("PHRASE-CLOSE-CLOTHES", "关闭晾衣模式别名探测", 0x0067, ["关闭晾衣模式", "退出晾衣模式", "晾衣模式关闭"]),
    ProbeGroup("PHRASE-CLOSE-LEISURE", "关闭休闲模式别名探测", 0x0068, ["关闭休闲模式", "退出休闲模式", "关闭休闲照明"]),
    ProbeGroup("PHRASE-CLOSE-GARDEN", "关闭园艺模式别名探测", 0x006A, ["关闭园艺模式", "退出园艺模式", "关闭园艺照明"]),
    ProbeGroup("PHRASE-SUNSET", "打开日落模式别名探测", 0x0033, ["打开日落模式", "打开落日模式"]),
]


def build_cases() -> list[sweep.SweepCase]:
    cases: list[sweep.SweepCase] = []
    for group in PROBE_GROUPS:
        for index, phrase in enumerate(group.phrases, start=1):
            cases.append(
                sweep.SweepCase(
                    case_id=f"{group.group_id}-{index:02d}",
                    title=f"{group.title}-{phrase}",
                    group=group.group_id,
                    texts=[WAKE, phrase],
                    expected_active_words=[0x0001, group.active_word],
                    capture_s=22.0,
                    initial_wait_s=18.0,
                    between_wait_s=1.8,
                    baseline_reset=True,
                    require_response_play=False,
                    notes=group.notes or "多别名词条探测：只验证唤醒 -> 识别 -> 主动协议，不强行虚构被动播报。",
                )
            )
    return cases


def summarize_groups(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        grouped[item["group"]].append(item)

    summary_rows: list[dict[str, Any]] = []
    for group in PROBE_GROUPS:
        items = grouped[group.group_id]
        passed = [item for item in items if item["status"] == "PASS"]
        summary_rows.append(
            {
                "group_id": group.group_id,
                "title": group.title,
                "active_word": f"0x{group.active_word:04X}",
                "phrases": group.phrases,
                "pass_count": len(passed),
                "total_count": len(items),
                "passed_phrases": [item["texts"][-1] for item in passed],
                "status": "PASS" if passed else "FAIL",
                "notes": group.notes,
            }
        )
    return summary_rows


def write_report_md(path: Path, suite_name: str, suite_dir: Path, results: list[dict[str, Any]], group_rows: list[dict[str, Any]]) -> None:
    pass_count = sum(1 for item in results if item["status"] == "PASS")
    fail_count = sum(1 for item in results if item["status"] == "FAIL")
    lines = [
        "# 好太太晾衣机 active-only 多别名词条探测报告",
        "",
        f"- 套件名称：`{suite_name}`",
        f"- 原始结果目录：`{suite_dir}`",
        "- 口径说明：针对 active-only 未闭环命令，选取 Excel 中的多个代表说法/别名做主动侧探测。",
        f"- phrase case 总计：`{len(results)}`；PASS=`{pass_count}`，FAIL=`{fail_count}`",
        f"- group 总计：`{len(group_rows)}`；命中 group=`{sum(1 for row in group_rows if row['status'] == 'PASS')}`，未命中 group=`{sum(1 for row in group_rows if row['status'] == 'FAIL')}`",
        "",
        "## Group 结论",
        "",
    ]
    for row in group_rows:
        lines.append(f"### {row['group_id']} {row['title']}")
        lines.append(f"- 目标主动协议：`0x0001 -> {row['active_word']}`")
        lines.append(f"- 探测短语：{' / '.join(row['phrases'])}")
        lines.append(f"- 结果：`{row['status']}`（命中 `{' / '.join(row['passed_phrases']) if row['passed_phrases'] else '无'}`）")
        if row["notes"]:
            lines.append(f"- 备注：{row['notes']}")
        lines.append("")

    lines.extend(["## Phrase 明细", ""])
    for item in results:
        lines.append(f"### {item['case_id']} {item['title']}")
        lines.append(f"- 结果：`{item['status']}`")
        lines.append(f"- 语音输入：`{' / '.join(item['texts'])}`")
        lines.append(f"- 期望主动协议：`{', '.join(item.get('expected_active_words', []))}`")
        lines.append(f"- 观测主动协议：`{', '.join(item.get('observed_active_words', [])) or '无'}`")
        lines.append(f"- 结果目录：`{item['result_dir']}`")
        if item.get("missing_markers"):
            lines.append(f"- 缺失日志标记：{', '.join(item['missing_markers'])}")
        if item.get("forbidden_marker_hits"):
            lines.append(f"- 命中禁止日志：{', '.join(item['forbidden_marker_hits'])}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> int:
    cases = build_cases()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_name = f"{timestamp}_htt_active_only_phrase_probe_r1"
    suite_dir = RESULT_ROOT / suite_name
    suite_dir.mkdir(parents=True, exist_ok=True)

    play_script = sweep.base.resolve_listenai_play(update=False)
    results: list[dict[str, Any]] = []
    for case in cases:
        results.append(sweep.run_case(case, suite_dir, play_script))

    group_rows = summarize_groups(results)
    summary = {
        "suite_name": suite_name,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "group_rows": group_rows,
        "results": results,
    }
    (suite_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report_dir = DELIVERABLE_ROOT / "reports" / suite_name
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "summary.md"
    write_report_md(report_path, suite_name, suite_dir, results, group_rows)
    print(json.dumps({"suite_name": suite_name, "suite_dir": str(suite_dir), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
