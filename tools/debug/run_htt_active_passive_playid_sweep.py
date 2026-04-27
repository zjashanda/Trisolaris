#!/usr/bin/env python
import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_htt_handshake_formal_suite as base  # noqa: E402


DELIVERABLE_ROOT = base.DELIVERABLE_ROOT
RESULT_ROOT = base.RESULT_ROOT


@dataclass
class SweepCase:
    case_id: str
    title: str
    group: str
    texts: list[str]
    expected_active_words: list[int]
    required_log_markers: list[str] = field(default_factory=list)
    extra_respond_rules: list[tuple[str, str]] = field(default_factory=list)
    timed_sends: list[tuple[float, str]] = field(default_factory=list)
    capture_s: float = 24.0
    between_wait_s: float = base.BETWEEN_TEXT_WAIT_S
    gaps_s: list[float] = field(default_factory=list)
    initial_wait_s: float = base.BOOT_READY_WAIT_S
    baseline_reset: bool = False
    require_response_play: bool = True
    min_response_play_ids: int = 1
    forbidden_log_markers: list[str] = field(default_factory=lambda: ["MCU is not ready!"])
    notes: str = ""


def full_chain_case(
    case_id: str,
    title: str,
    group: str,
    command_text: str,
    active_word: int,
    passive_word: int,
    notes: str = "",
) -> SweepCase:
    passive_hex = base.passive_frame_hex(passive_word)
    return SweepCase(
        case_id=case_id,
        title=title,
        group=group,
        texts=["小好小好", command_text],
        expected_active_words=[0x0001, active_word],
        required_log_markers=[f"receive msg:: {passive_hex}"],
        extra_respond_rules=[(base.active_frame_hex(active_word), passive_hex)],
        baseline_reset=True,
        notes=notes,
    )


CASES: list[SweepCase] = [
    full_chain_case("FULL-LIGHT-ON-001", "打开照明全链路", "fixed-passive", "打开照明", 0x0009, 0x0009),
    full_chain_case("FULL-LIGHT-OFF-001", "关闭照明全链路", "fixed-passive", "关闭照明", 0x000A, 0x000A),
    full_chain_case("FULL-POWER-OFF-001", "关机全链路", "fixed-passive", "关机", 0x0005, 0x0005),
    full_chain_case("FULL-UP-001", "上升全链路", "fixed-passive", "晾杆上升", 0x0006, 0x0006),
    full_chain_case("FULL-DOWN-001", "下降全链路", "fixed-passive", "晾杆下降", 0x0007, 0x0007),
    full_chain_case("FULL-STOP-001", "停止全链路", "fixed-passive", "停止升降", 0x0008, 0x0008),
    full_chain_case("FULL-STERILIZE-ON-001", "打开消毒全链路", "fixed-passive", "打开消毒", 0x000B, 0x000B),
    full_chain_case("FULL-STERILIZE-OFF-001", "关闭消毒全链路", "fixed-passive", "关闭消毒", 0x000D, 0x000D),
    full_chain_case("FULL-VOL-UP-001", "调大音量全链路", "fixed-passive", "调大音量", 0x0041, 0x0041),
    full_chain_case("FULL-VOL-DOWN-001", "调小音量全链路", "fixed-passive", "调小音量", 0x0042, 0x0042),
    full_chain_case("FULL-VOL-MAX-001", "最大音量全链路", "fixed-passive", "最大音量", 0x0043, 0x0043),
    full_chain_case("FULL-VOL-MIN-001", "最小音量全链路", "fixed-passive", "最小音量", 0x0044, 0x0044),
    full_chain_case("FULL-BRIGHT-UP-001", "调亮全链路", "fixed-passive", "亮度调高一点", 0x005B, 0x0046),
    full_chain_case("FULL-BRIGHT-DOWN-001", "调暗全链路", "fixed-passive", "调暗一点", 0x005C, 0x0047),
    full_chain_case("FULL-BRIGHT-MAX-001", "最亮全链路", "fixed-passive", "调到最亮", 0x0057, 0x0048),
    full_chain_case("FULL-BRIGHT-MIN-001", "最暗全链路", "fixed-passive", "调到最暗", 0x0058, 0x0049),
    full_chain_case("FULL-COLD-UP-001", "调冷全链路", "fixed-passive", "增加冷光", 0x005D, 0x004A),
    full_chain_case("FULL-WARM-UP-001", "调暖全链路", "fixed-passive", "增加暖光", 0x005E, 0x004B),
    full_chain_case("FULL-COLD-MAX-001", "最冷全链路", "fixed-passive", "打开冷光模式", 0x0059, 0x004C),
    full_chain_case("FULL-WARM-MAX-001", "最暖全链路", "fixed-passive", "打开暖光模式", 0x005A, 0x004D),
    full_chain_case("FULL-NIGHT-ON-001", "打开夜灯全链路", "fixed-passive", "打开夜灯", 0x0061, 0x004E),
    full_chain_case("FULL-NIGHT-OFF-001", "关闭夜灯全链路", "fixed-passive", "关闭夜灯", 0x0062, 0x004F),
    full_chain_case("FULL-SCENE-CLOTHES-001", "打开晾衣模式全链路", "fixed-passive", "打开晾衣模式", 0x0063, 0x0050),
    full_chain_case("FULL-SCENE-LEISURE-001", "打开休闲模式全链路", "fixed-passive", "打开休闲模式", 0x0064, 0x0051),
    full_chain_case("FULL-SCENE-READ-001", "打开阅读模式全链路", "fixed-passive", "打开阅读模式", 0x0065, 0x0052),
    full_chain_case("FULL-SCENE-GARDEN-001", "打开园艺模式全链路", "fixed-passive", "打开园艺模式", 0x0066, 0x0053),
    full_chain_case("FULL-ROD1-UP-001", "杆一上升全链路", "fixed-passive", "杆一上升", 0x0051, 0x0063),
    full_chain_case("FULL-ROD2-UP-001", "杆二上升全链路", "fixed-passive", "杆二上升", 0x0052, 0x0063),
    full_chain_case("FULL-ROD1-DOWN-001", "杆一下降全链路", "fixed-passive", "降低杆一", 0x0053, 0x0064),
    full_chain_case("FULL-ROD2-DOWN-001", "杆二下降全链路", "fixed-passive", "杆二下降", 0x0054, 0x0064),
    full_chain_case("FULL-ROD1-STOP-001", "杆一停止全链路", "fixed-passive", "第一根杆停止", 0x0055, 0x0065),
    full_chain_case("FULL-ROD2-STOP-001", "杆二停止全链路", "fixed-passive", "杆二停止", 0x0056, 0x0065),
    full_chain_case("FULL-COLLECT-SET-OK-001", "设为收衣位成功", "fixed-passive", "设为收衣位", 0x0077, 0x0073),
    full_chain_case("FULL-COLLECT-SET-FAIL-001", "设为收衣位失败", "fixed-passive", "设为收衣位", 0x0077, 0x0074),
    full_chain_case("FULL-COLLECT-CANCEL-001", "取消收衣位", "fixed-passive", "取消收衣位", 0x0078, 0x007B),
    full_chain_case("FULL-DRY-SET-OK-001", "设为晒衣位成功", "fixed-passive", "设为晒衣位", 0x0079, 0x0075),
    full_chain_case("FULL-DRY-SET-FAIL-001", "设为晒衣位失败", "fixed-passive", "设为晒衣位", 0x0079, 0x0076),
    full_chain_case("FULL-DRY-CANCEL-001", "取消晒衣位", "fixed-passive", "取消晒衣位", 0x007A, 0x007C),
    SweepCase(
        case_id="FULL-PAIR-SUCCESS-001",
        title="开始配网成功链路",
        group="fixed-passive",
        texts=["小好小好", "开始配网"],
        expected_active_words=[0x0001, 0x0020],
        required_log_markers=[
            f"receive msg:: {base.passive_frame_hex(0x0004)}",
            f"receive msg:: {base.passive_frame_hex(0x001C)}",
        ],
        extra_respond_rules=[(base.active_frame_hex(0x0020), base.passive_frame_hex(0x0004))],
        timed_sends=[(14.0, base.passive_frame_hex(0x001C))],
        capture_s=26.0,
        baseline_reset=True,
    ),
    SweepCase(
        case_id="FULL-PAIR-FAIL-001",
        title="开始配网失败链路",
        group="fixed-passive",
        texts=["小好小好", "开始配网"],
        expected_active_words=[0x0001, 0x0020],
        required_log_markers=[
            f"receive msg:: {base.passive_frame_hex(0x0004)}",
            f"receive msg:: {base.passive_frame_hex(0x001D)}",
        ],
        extra_respond_rules=[(base.active_frame_hex(0x0020), base.passive_frame_hex(0x0004))],
        timed_sends=[(14.0, base.passive_frame_hex(0x001D))],
        capture_s=26.0,
        baseline_reset=True,
    ),
]


def effective_initial_wait(case: SweepCase) -> float:
    if case.baseline_reset and case.texts:
        return max(case.initial_wait_s, base.BASELINE_READY_WAIT_S)
    return case.initial_wait_s


def effective_capture_s(case: SweepCase) -> float:
    initial_wait_s = effective_initial_wait(case)
    capture_s = case.capture_s + max(0.0, initial_wait_s - case.initial_wait_s)
    if case.texts:
        capture_s += base.POST_PLAY_GUARD_S
    return capture_s


def build_handshake_cmd(case: SweepCase, result_dir: Path) -> list[str]:
    command = [
        sys.executable,
        str(base.HANDSHAKE_SCRIPT),
        "--result-dir",
        str(result_dir),
        "--proto-port",
        base.PROTO_PORT,
        "--proto-baudrate",
        str(base.PROTO_BAUD),
        "--log-port",
        base.LOG_PORT,
        "--log-baudrate",
        str(base.LOG_BAUD),
        "--ctrl-port",
        base.CTRL_PORT,
        "--ctrl-baudrate",
        str(base.CTRL_BAUD),
        "--command-preset",
        "normal",
        "--capture-s",
        str(effective_capture_s(case)),
        "--loglevel4-at-s",
        "4.5",
        "--respond",
        "A5 FA 7F 01 02 21 FB=A5 FA 81 00 20 40 FB",
        "--respond",
        "A5 FA 7F 5A 5A D2 FB=A5 FA 83 5A 5A D6 FB",
        "--periodic",
        "A5 FA 83 A5 A5 6C FB@4.0",
    ]
    if case.baseline_reset:
        command.extend(["--inject-once", f"{base.passive_frame_hex(base.BASELINE_RESET_WORD)}@{base.BASELINE_RESET_AT_S}"])
    for match_hex, reply_hex in case.extra_respond_rules:
        command.extend(["--respond", f"{match_hex}={reply_hex}"])
    for at_s, payload_hex in case.timed_sends:
        command.extend(["--inject-once", f"{payload_hex}@{at_s}"])
    return command


def evaluate_case(case: SweepCase, case_dir: Path) -> dict[str, Any]:
    com36_text = (case_dir / "com36_frames.txt").read_text(encoding="utf-8", errors="replace")
    com38_text = (case_dir / "com38_utf8.txt").read_text(encoding="utf-8", errors="replace")
    active_words = base.parse_data_words(com36_text)
    play_ids = base.parse_play_ids(com38_text)
    response_play_ids = list(play_ids)
    if case.baseline_reset and response_play_ids and response_play_ids[0] == 103:
        response_play_ids = response_play_ids[1:]

    expected_ok = base.contains_in_order(active_words, case.expected_active_words)
    missing_markers = [marker for marker in case.required_log_markers if marker not in com38_text]
    forbidden_marker_hits = [marker for marker in case.forbidden_log_markers if marker in com38_text]
    response_play_ok = True
    if case.require_response_play:
        response_play_ok = len(response_play_ids) >= case.min_response_play_ids

    status = "PASS" if expected_ok and not missing_markers and not forbidden_marker_hits and response_play_ok else "FAIL"
    return {
        "case_id": case.case_id,
        "title": case.title,
        "group": case.group,
        "status": status,
        "expected_active_words": [f"0x{word:04X}" for word in case.expected_active_words],
        "observed_active_words": [f"0x{word:04X}" for word in active_words],
        "observed_play_ids_all": play_ids,
        "observed_response_play_ids": response_play_ids,
        "tail_response_play_id": response_play_ids[-1] if response_play_ids else None,
        "missing_markers": missing_markers,
        "forbidden_marker_hits": forbidden_marker_hits,
        "response_play_ok": response_play_ok,
        "notes": case.notes,
    }


def run_case(case: SweepCase, suite_dir: Path, play_script: Path) -> dict[str, Any]:
    case_dir = suite_dir / "steps" / case.case_id.lower()
    case_dir.mkdir(parents=True, exist_ok=True)
    probe_stdout = case_dir / "probe_stdout.txt"
    probe_stderr = case_dir / "probe_stderr.txt"
    handshake_cmd = build_handshake_cmd(case, case_dir)
    initial_wait_s = effective_initial_wait(case)
    capture_s = effective_capture_s(case)

    with probe_stdout.open("w", encoding="utf-8") as stdout_handle, probe_stderr.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(handshake_cmd, stdout=stdout_handle, stderr=stderr_handle)
        playback_records: list[dict[str, Any]] = []
        try:
            time.sleep(initial_wait_s)
            for index, text in enumerate(case.texts):
                audio_file = base.prepare_audio(text)
                playback_records.append(
                    base.play_audio(
                        play_script=play_script,
                        audio_file=audio_file,
                        out_path=case_dir / f"play_{index + 1:02d}.txt",
                    )
                )
                if index < len(case.texts) - 1:
                    gap_s = case.gaps_s[index] if index < len(case.gaps_s) else case.between_wait_s
                    time.sleep(gap_s)
            process.wait(timeout=capture_s + 10.0)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5.0)

    required_files = [
        case_dir / "com36_frames.txt",
        case_dir / "com38_utf8.txt",
        case_dir / "meta.json",
    ]
    missing = [path.name for path in required_files if not path.exists()]
    record: dict[str, Any] = {
        "case_id": case.case_id,
        "title": case.title,
        "group": case.group,
        "texts": case.texts,
        "capture_s": capture_s,
        "initial_wait_s": initial_wait_s,
        "baseline_reset": case.baseline_reset,
        "result_dir": str(case_dir),
        "playback": playback_records,
        "required_log_markers": case.required_log_markers,
    }
    if missing:
        record["status"] = "BLOCKED"
        record["reason"] = f"运行产物缺失: {', '.join(missing)}"
    else:
        record.update(evaluate_case(case, case_dir))
    (case_dir / "analysis.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(1.0)
    return record


def write_cases_md(path: Path, selected_cases: list[SweepCase]) -> None:
    lines = [
        "# 好太太晾衣机主动命令-被动响应-play id sweep 用例",
        "",
        "| 用例ID | 分组 | 标题 | 语音输入 | 期望主动协议 | 期望被动接收日志 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case in selected_cases:
        markers = " / ".join(case.required_log_markers) if case.required_log_markers else "-"
        active_words = " / ".join(base.active_frame_hex(word) for word in case.expected_active_words)
        lines.append(
            f"| `{case.case_id}` | `{case.group}` | {case.title} | {' / '.join(case.texts)} | {active_words} | {markers} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_report_md(path: Path, suite_name: str, suite_dir: Path, results: list[dict[str, Any]]) -> None:
    pass_count = sum(1 for item in results if item["status"] == "PASS")
    fail_count = sum(1 for item in results if item["status"] == "FAIL")
    blocked_count = sum(1 for item in results if item["status"] == "BLOCKED")

    lines = [
        "# 好太太晾衣机主动命令-被动响应-play id sweep 报告",
        "",
        f"- 套件名称：`{suite_name}`",
        f"- 原始结果目录：`{suite_dir}`",
        "- 口径说明：本轮仍建立在协议握手仿真 ready 的 bench 上，重点补齐“唤醒 -> 识别 -> 主动协议 -> 被动响应 -> play id”链路。",
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
            lines.append(f"- 观测全部 play id：{', '.join(str(x) for x in item.get('observed_play_ids_all', [])) or '无'}")
            lines.append(f"- 观测响应 play id：{', '.join(str(x) for x in item.get('observed_response_play_ids', [])) or '无'}")
            lines.append(f"- 响应尾部 play id：{item.get('tail_response_play_id') if item.get('tail_response_play_id') is not None else '无'}")
            if item.get("missing_markers"):
                lines.append(f"- 缺失日志标记：{', '.join(item['missing_markers'])}")
            if item.get("forbidden_marker_hits"):
                lines.append(f"- 命中禁止日志：{', '.join(item['forbidden_marker_hits'])}")
            if not item.get("response_play_ok", True):
                lines.append("- 响应 play id 断言：未达到最少播放次数")
        if item.get("notes"):
            lines.append(f"- 备注：{item['notes']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HTT active->passive->play-id sweep cases.")
    parser.add_argument("--case-id", dest="case_ids", action="append", help="Run only the specified case id.")
    parser.add_argument("--group", dest="groups", action="append", help="Run only the specified group.")
    parser.add_argument("--suite-tag", default="", help="Optional suffix appended to the suite directory name.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected_cases = CASES
    if args.groups:
        wanted_groups = {item.strip() for item in args.groups if item.strip()}
        selected_cases = [case for case in selected_cases if case.group in wanted_groups]
    if args.case_ids:
        wanted_ids = {item.strip().upper() for item in args.case_ids if item.strip()}
        selected_cases = [case for case in selected_cases if case.case_id.upper() in wanted_ids]
        missing = sorted(wanted_ids - {case.case_id.upper() for case in selected_cases})
        if missing:
            raise SystemExit(f"Unknown case id(s): {', '.join(missing)}")
    if not selected_cases:
        raise SystemExit("No cases selected.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_name = f"{timestamp}_htt_active_passive_playid_sweep"
    if args.suite_tag:
        suite_name = f"{suite_name}_{args.suite_tag}"
    suite_dir = RESULT_ROOT / suite_name
    suite_dir.mkdir(parents=True, exist_ok=True)

    play_script = base.resolve_listenai_play(update=False)
    results: list[dict[str, Any]] = []
    for case in selected_cases:
        results.append(run_case(case, suite_dir, play_script))

    summary = {
        "suite_name": suite_name,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "device_key": base.DEVICE_KEY,
        "ctrl_port": base.CTRL_PORT,
        "log_port": base.LOG_PORT,
        "proto_port": base.PROTO_PORT,
        "selected_case_ids": [case.case_id for case in selected_cases],
        "results": results,
    }
    (suite_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    (DELIVERABLE_ROOT / "cases").mkdir(parents=True, exist_ok=True)
    (DELIVERABLE_ROOT / "reports").mkdir(parents=True, exist_ok=True)

    case_path = DELIVERABLE_ROOT / "cases" / "20260423_主动被动响应_playid_sweep_v1.md"
    report_dir = DELIVERABLE_ROOT / "reports" / suite_name
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "summary.md"

    write_cases_md(case_path, selected_cases)
    write_report_md(report_path, suite_name, suite_dir, results)
    print(json.dumps({"suite_name": suite_name, "suite_dir": str(suite_dir), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
