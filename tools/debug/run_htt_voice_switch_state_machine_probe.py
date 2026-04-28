#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_htt_handshake_formal_suite as formal
import run_htt_numeric_probe as numeric

RESULT_ROOT = formal.RESULT_ROOT
DELIVERABLE_ROOT = formal.DELIVERABLE_ROOT

RESET_HEX = formal.passive_frame_hex(formal.BASELINE_RESET_WORD)
VOICE_OFF_HEX = formal.passive_frame_hex(0x0036)
ACTIVE_VOICE_OFF_HEX = formal.active_frame_hex(0x0016)
VOICE_OFF_REPLY_RULE = (ACTIVE_VOICE_OFF_HEX, VOICE_OFF_HEX)
VOICE_ON_HEX = formal.passive_frame_hex(0x0037)
ACTIVE_VOICE_ON_HEX = formal.active_frame_hex(0x0017)
VOICE_ON_REPLY_RULE = (ACTIVE_VOICE_ON_HEX, VOICE_ON_HEX)

WAKE_TEXT = "小好小好"
OPEN_VOICE_TEXT = "语音功能打开"
OPEN_LIGHT_TEXT = "打开照明"

EXPECTED_CURRENT_SESSION_TIMEOUT_S = 25.0
EXPECTED_RESTRICTED_TIMEOUT_S = 10.0
EXPECTED_NORMAL_TIMEOUT_S = 25.0
TOLERANCE_S = 4.0


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def play_ids(log_text: str) -> list[int]:
    return formal.parse_play_ids(log_text)


def words_hex(words: list[int]) -> list[str]:
    return [f"0x{word:04X}" for word in words]


def marker_time(lines: list[dict[str, Any]], patterns: list[str], after_s: float = 0.0) -> float | None:
    return numeric.find_first_marker_time(lines, patterns, after_s=after_s)


def word_time(frames: list[dict[str, Any]], word: int, after_s: float = 0.0) -> float | None:
    return numeric.find_first_data_word_time(frames, word, after_s=after_s)


def last_play_stop_before(lines: list[dict[str, Any]], before_s: float | None = None) -> float | None:
    return numeric.find_last_marker_time(lines, ["play stop"], before_s=before_s)


def first_timeout_after(lines: list[dict[str, Any]], after_s: float) -> tuple[float | None, float | None]:
    return (
        marker_time(lines, ["TIME_OUT"], after_s=after_s),
        marker_time(lines, ["MODE=0"], after_s=after_s),
    )


def passive_voice_off_time(capture: dict[str, Any]) -> float:
    return marker_time(capture["timed_lines"], [f"receive msg:: {VOICE_OFF_HEX}"], after_s=0.0) or 0.0


def wake_start(capture: dict[str, Any], after_s: float) -> dict[str, float | None]:
    lines = capture["timed_lines"]
    frames = capture["proto_frames"]
    wake_frame_s = word_time(frames, 0x0001, after_s=after_s)
    wakeup_s = marker_time(lines, ["Wakeup:"], after_s=after_s)
    keyword_s = marker_time(lines, ["keyword:xiao hao xiao hao"], after_s=after_s)
    play77_s = marker_time(lines, ["play id : 77"], after_s=after_s)
    candidates = [v for v in [wakeup_s, keyword_s, play77_s] if v is not None]
    return {
        "wake_frame_s": wake_frame_s,
        "wakeup_s": wakeup_s,
        "keyword_s": keyword_s,
        "play77_s": play77_s,
        "wake_marker_s": min(candidates) if candidates else None,
    }


def timeout_metrics(capture: dict[str, Any], after_s: float) -> dict[str, Any]:
    lines = capture["timed_lines"]
    wake = wake_start(capture, after_s=after_s)
    wake_marker_s = wake["wake_marker_s"]
    timeout_s, mode0_s = first_timeout_after(lines, after_s=wake_marker_s or after_s)
    play_stop_s = None
    if timeout_s is not None:
        play_stop_s = last_play_stop_before(lines, before_s=timeout_s)
    return {
        **wake,
        "play_stop_s": play_stop_s,
        "timeout_s": timeout_s,
        "mode0_s": mode0_s,
        "wake_to_timeout_s": round(timeout_s - wake_marker_s, 3) if timeout_s is not None and wake_marker_s is not None else None,
        "wake_to_mode0_s": round(mode0_s - wake_marker_s, 3) if mode0_s is not None and wake_marker_s is not None else None,
        "response_end_to_timeout_s": round(timeout_s - play_stop_s, 3) if timeout_s is not None and play_stop_s is not None else None,
        "response_end_to_mode0_s": round(mode0_s - play_stop_s, 3) if mode0_s is not None and play_stop_s is not None else None,
    }


def timeout_metrics_from_anchor(capture: dict[str, Any], anchor_s: float, anchor_name: str) -> dict[str, Any]:
    lines = capture["timed_lines"]
    timeout_s, mode0_s = first_timeout_after(lines, after_s=anchor_s)
    play_stop_s = last_play_stop_before(lines, before_s=timeout_s) if timeout_s is not None else None
    return {
        "wake_frame_s": None,
        "wakeup_s": None,
        "keyword_s": None,
        "play77_s": None,
        "wake_marker_s": anchor_s,
        "wake_marker_source": anchor_name,
        "play_stop_s": play_stop_s,
        "timeout_s": timeout_s,
        "mode0_s": mode0_s,
        "wake_to_timeout_s": round(timeout_s - anchor_s, 3) if timeout_s is not None else None,
        "wake_to_mode0_s": round(mode0_s - anchor_s, 3) if mode0_s is not None else None,
        "response_end_to_timeout_s": round(timeout_s - play_stop_s, 3) if timeout_s is not None and play_stop_s is not None else None,
        "response_end_to_mode0_s": round(mode0_s - play_stop_s, 3) if mode0_s is not None and play_stop_s is not None else None,
    }


def duration_ok(value: Any, expected: float) -> bool:
    return isinstance(value, float) and abs(value - expected) <= TOLERANCE_S


def timeout_ok(metrics: dict[str, Any], expected: float) -> bool:
    wake_ok = duration_ok(metrics.get("wake_to_timeout_s"), expected) and duration_ok(metrics.get("wake_to_mode0_s"), expected)
    response_ok = duration_ok(metrics.get("response_end_to_timeout_s"), expected) and duration_ok(metrics.get("response_end_to_mode0_s"), expected)
    return wake_ok or response_ok


def summarize_capture(capture: dict[str, Any]) -> dict[str, Any]:
    return {
        "step_dir": str(capture["step_dir"]),
        "observed_words": words_hex(capture["observed_words"]),
        "play_ids": play_ids(capture["log_text"]),
        "has_mcu_not_ready": "MCU is not ready!" in capture["log_text"],
        "refresh_config_values": capture.get("refresh_config_values", []),
    }


def run_current_session_25s(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    capture = numeric.run_capture_step(
        step_dir=bundle_dir / "steps" / "voice_off_current_session_25s",
        play_script=play_script,
        capture_s=150.0,
        texts=[WAKE_TEXT, "语音功能关闭", WAKE_TEXT],
        initial_wait_s=45.0,
        gaps_s=[2.0, 3.0],
        timed_sends=[(formal.BASELINE_RESET_AT_S, RESET_HEX)],
        extra_respond_rules=[VOICE_OFF_REPLY_RULE, VOICE_ON_REPLY_RULE],
    )
    off_s = passive_voice_off_time(capture)
    metrics = timeout_metrics(capture, after_s=off_s + 0.5)
    ids = play_ids(capture["log_text"])
    words = capture["observed_words"]
    status = "PASS" if formal.contains_in_order(words, [0x0001, 0x0016, 0x0001]) and 77 in ids and timeout_ok(metrics, EXPECTED_CURRENT_SESSION_TIMEOUT_S) else "FAIL"
    return {
        "case_id": "VOICE-OFF-CURRENT-SESSION-25S",
        "status": status,
        "expected_timeout_s": EXPECTED_CURRENT_SESSION_TIMEOUT_S,
        "tolerance_s": TOLERANCE_S,
        **summarize_capture(capture),
        **metrics,
    }


def run_ding_once(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    capture = numeric.run_capture_step(
        step_dir=bundle_dir / "steps" / "voice_off_ding_once",
        play_script=play_script,
        capture_s=135.0,
        texts=[WAKE_TEXT, "语音功能关闭", WAKE_TEXT, WAKE_TEXT],
        initial_wait_s=45.0,
        gaps_s=[2.0, 3.0, 3.0],
        timed_sends=[(formal.BASELINE_RESET_AT_S, RESET_HEX)],
        extra_respond_rules=[VOICE_OFF_REPLY_RULE],
    )
    ids = play_ids(capture["log_text"])
    words = capture["observed_words"]
    # 24 是关闭语音提示；77 是受限唤醒“咚/提示”口径。连续两次唤醒只允许出现一次 77。
    status = "PASS" if 0x0001 in words and 24 in ids and ids.count(77) == 1 and 0x0009 not in words else "FAIL"
    return {
        "case_id": "VOICE-OFF-DING-ONCE",
        "status": status,
        **summarize_capture(capture),
        "play_id_24_count": ids.count(24),
        "play_id_77_count": ids.count(77),
        "play_id_123_count": ids.count(123),
    }


def run_after_timeout_10s(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    capture = numeric.run_capture_step(
        step_dir=bundle_dir / "steps" / "voice_off_after_timeout_10s",
        play_script=play_script,
        capture_s=170.0,
        texts=[WAKE_TEXT, "语音功能关闭", WAKE_TEXT],
        initial_wait_s=45.0,
        gaps_s=[2.0, 35.0],
        timed_sends=[(formal.BASELINE_RESET_AT_S, RESET_HEX)],
        extra_respond_rules=[VOICE_OFF_REPLY_RULE],
    )
    off_s = passive_voice_off_time(capture)
    metrics = timeout_metrics(capture, after_s=off_s + 25.0)
    ids = play_ids(capture["log_text"])
    words = capture["observed_words"]
    status = "PASS" if 0x0001 in words and 24 in ids and 77 in ids and timeout_ok(metrics, EXPECTED_RESTRICTED_TIMEOUT_S) else "FAIL"
    return {
        "case_id": "VOICE-OFF-AFTER-TIMEOUT-10S",
        "status": status,
        "expected_timeout_s": EXPECTED_RESTRICTED_TIMEOUT_S,
        "tolerance_s": TOLERANCE_S,
        "passive_voice_off_s": off_s,
        **summarize_capture(capture),
        **metrics,
    }


def run_voice_on_recover_25s(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    capture = numeric.run_capture_step(
        step_dir=bundle_dir / "steps" / "voice_on_recover_25s",
        play_script=play_script,
        capture_s=210.0,
        texts=[WAKE_TEXT, "语音功能关闭", WAKE_TEXT, OPEN_VOICE_TEXT, WAKE_TEXT, OPEN_LIGHT_TEXT],
        initial_wait_s=45.0,
        gaps_s=[2.0, 35.0, 2.0, 6.0, 2.0],
        timed_sends=[(formal.BASELINE_RESET_AT_S, RESET_HEX)],
        extra_respond_rules=[VOICE_OFF_REPLY_RULE, VOICE_ON_REPLY_RULE],
    )
    ids = play_ids(capture["log_text"])
    words = capture["observed_words"]
    # 开语音恢复后，超时口径应从最后一次业务交互（这里是 0x0009）开始取下一次 TIME_OUT。
    frames = capture["proto_frames"]
    wake_times = [float(item["t_s"]) for item in frames if item.get("data_word") == 0x0001]
    after_s = wake_times[-1] if wake_times else 45.0
    business_marker_s = marker_time(capture["timed_lines"], [f"send msg:: {formal.active_frame_hex(0x0009)}"], after_s=after_s)
    metrics = (
        timeout_metrics_from_anchor(capture, business_marker_s, "log_active_0x0009")
        if business_marker_s is not None
        else timeout_metrics(capture, after_s=after_s)
    )
    business_ok = formal.contains_in_order(words, [0x0001, 0x0017, 0x0001, 0x0009])
    normal_timeout_ok = timeout_ok(metrics, EXPECTED_NORMAL_TIMEOUT_S)
    status = "PASS" if business_ok and normal_timeout_ok else "FAIL"
    return {
        "case_id": "VOICE-ON-RECOVER-25S",
        "status": status,
        "expected_timeout_s": EXPECTED_NORMAL_TIMEOUT_S,
        "tolerance_s": TOLERANCE_S,
        "business_recovered": business_ok,
        "normal_timeout_ok": normal_timeout_ok,
        **summarize_capture(capture),
        **metrics,
        "play_id_77_count": ids.count(77),
        "play_id_123_count": ids.count(123),
    }


def write_report(report_path: Path, bundle_dir: Path, results: list[dict[str, Any]]) -> None:
    pass_count = sum(1 for item in results if item["status"] == "PASS")
    fail_count = sum(1 for item in results if item["status"] == "FAIL")
    lines = [
        "# 好太太语音开关状态机重测报告",
        "",
        f"- 原始结果目录：`{bundle_dir}`",
        f"- 总计：`{len(results)}` 条；PASS=`{pass_count}`，FAIL=`{fail_count}`",
        "- 口径：区分关闭语音后当前 25s 会话未超时、已超时后再唤醒、打开语音后恢复三种状态。",
        "",
        "## 结果明细",
        "",
        "| 用例 | 结果 | 关键实测 | 证据 |",
        "| --- | --- | --- | --- |",
    ]
    for item in results:
        detail_parts = []
        if "expected_timeout_s" in item:
            detail_parts.append(f"期望 {item['expected_timeout_s']}s")
        if item.get("wake_to_timeout_s") is not None:
            detail_parts.append(f"唤醒->TIME_OUT {item['wake_to_timeout_s']}s")
        if item.get("wake_to_mode0_s") is not None:
            detail_parts.append(f"唤醒->MODE=0 {item['wake_to_mode0_s']}s")
        if item.get("response_end_to_timeout_s") is not None:
            detail_parts.append(f"响应结束->TIME_OUT {item['response_end_to_timeout_s']}s")
        if item.get("response_end_to_mode0_s") is not None:
            detail_parts.append(f"响应结束->MODE=0 {item['response_end_to_mode0_s']}s")
        if "play_id_77_count" in item:
            detail_parts.append(f"77次数 {item['play_id_77_count']}")
        if "business_recovered" in item:
            detail_parts.append(f"业务恢复 {item['business_recovered']}")
        lines.append(
            f"| `{item['case_id']}` | `{item['status']}` | {'；'.join(detail_parts)} | `{item['step_dir']}` |"
        )
    lines.extend(["", "## 原始 JSON", "", f"- `{bundle_dir / 'summary.json'}`"])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    play_script = formal.resolve_listenai_play(update=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_name = f"{timestamp}_htt_voice_switch_state_machine_r1"
    bundle_dir = RESULT_ROOT / suite_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "steps").mkdir(parents=True, exist_ok=True)

    results = [
        run_current_session_25s(bundle_dir, play_script),
        run_ding_once(bundle_dir, play_script),
        run_after_timeout_10s(bundle_dir, play_script),
        run_voice_on_recover_25s(bundle_dir, play_script),
    ]
    summary = {
        "suite_name": suite_name,
        "bundle_dir": str(bundle_dir),
        "started_at": timestamp,
        "results": results,
    }
    write_json(bundle_dir / "summary.json", summary)

    report_dir = DELIVERABLE_ROOT / "reports" / suite_name
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "summary.md"
    write_report(report_path, bundle_dir, results)

    print(json.dumps({"suite_name": suite_name, "report_path": str(report_path), "results": results}, ensure_ascii=False, indent=2))
    return 0 if all(item["status"] == "PASS" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
