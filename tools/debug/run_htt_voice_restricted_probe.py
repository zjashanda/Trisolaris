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
PASSIVE_VOICE_OFF_HEX = formal.passive_frame_hex(0x0012)

WAKE_TEXT = "小好小好"
OPEN_LIGHT_TEXT = "打开照明"

EXPECTED_RESTRICTED_TIMEOUT_S = 10.0
RESTRICTED_TIMEOUT_TOLERANCE_S = 1.5


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_restricted_timeout_markers(capture: dict[str, Any]) -> dict[str, Any]:
    lines = capture["timed_lines"]
    frames = capture["proto_frames"]
    passive_voice_off_s = numeric.find_first_marker_time(lines, [f"receive msg:: {PASSIVE_VOICE_OFF_HEX}"])
    search_after_s = passive_voice_off_s or 0.0

    wake_frame_s = numeric.find_first_data_word_time(frames, 0x0001, after_s=search_after_s)
    wakeup_line_s = numeric.find_first_marker_time(lines, ["Wakeup:"], after_s=search_after_s)
    wake_keyword_s = numeric.find_first_marker_time(lines, ["keyword:xiao hao xiao hao"], after_s=search_after_s)
    restricted_play_id_s = numeric.find_first_marker_time(lines, ["play id : 77"], after_s=search_after_s)

    wake_marker_s = wake_frame_s or wake_keyword_s or wakeup_line_s or restricted_play_id_s
    restricted_play_start_s = (
        numeric.find_first_marker_time(lines, ["play start"], after_s=wake_marker_s or search_after_s)
        if wake_marker_s is not None
        else None
    )
    restricted_play_stop_s = (
        numeric.find_first_marker_time(lines, ["play stop"], after_s=restricted_play_start_s or wake_marker_s or search_after_s)
        if wake_marker_s is not None
        else None
    )
    timeout_s = numeric.find_first_marker_time(lines, ["TIME_OUT"], after_s=wake_marker_s or search_after_s)
    mode_zero_s = numeric.find_first_marker_time(lines, ["MODE=0"], after_s=wake_marker_s or search_after_s)

    wake_to_timeout_s = round(timeout_s - wake_marker_s, 3) if wake_marker_s is not None and timeout_s is not None else None
    wake_to_mode_zero_s = (
        round(mode_zero_s - wake_marker_s, 3) if wake_marker_s is not None and mode_zero_s is not None else None
    )
    response_end_to_timeout_s = (
        round(timeout_s - restricted_play_stop_s, 3)
        if timeout_s is not None and restricted_play_stop_s is not None
        else None
    )
    response_end_to_mode_zero_s = (
        round(mode_zero_s - restricted_play_stop_s, 3)
        if mode_zero_s is not None and restricted_play_stop_s is not None
        else None
    )

    return {
        "passive_voice_off_s": passive_voice_off_s,
        "wake_marker_s": wake_marker_s,
        "wake_frame_s": wake_frame_s,
        "wakeup_line_s": wakeup_line_s,
        "wake_keyword_s": wake_keyword_s,
        "restricted_play_id_s": restricted_play_id_s,
        "restricted_play_start_s": restricted_play_start_s,
        "restricted_play_stop_s": restricted_play_stop_s,
        "timeout_s": timeout_s,
        "mode_zero_s": mode_zero_s,
        "wake_to_timeout_s": wake_to_timeout_s,
        "wake_to_mode_zero_s": wake_to_mode_zero_s,
        "response_end_to_timeout_s": response_end_to_timeout_s,
        "response_end_to_mode_zero_s": response_end_to_mode_zero_s,
    }


def run_restricted_timeout_probe(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    capture = numeric.run_capture_step(
        step_dir=bundle_dir / "steps" / "restricted_timeout_wake_only",
        play_script=play_script,
        capture_s=60.0,
        texts=[WAKE_TEXT],
        initial_wait_s=14.0,
        timed_sends=[
            (formal.BASELINE_RESET_AT_S, RESET_HEX),
            (10.0, PASSIVE_VOICE_OFF_HEX),
        ],
    )
    markers = extract_restricted_timeout_markers(capture)
    play_ids = formal.parse_play_ids(capture["log_text"])
    words = capture["observed_words"]
    timeout_ok = (
        isinstance(markers["wake_to_timeout_s"], float)
        and isinstance(markers["wake_to_mode_zero_s"], float)
        and abs(markers["wake_to_timeout_s"] - EXPECTED_RESTRICTED_TIMEOUT_S) <= RESTRICTED_TIMEOUT_TOLERANCE_S
        and abs(markers["wake_to_mode_zero_s"] - EXPECTED_RESTRICTED_TIMEOUT_S) <= RESTRICTED_TIMEOUT_TOLERANCE_S
    )
    status = (
        "PASS"
        if 0x0001 in words
        and 65 in play_ids
        and 77 in play_ids
        and timeout_ok
        and "MCU is not ready!" not in capture["log_text"]
        else "FAIL"
    )
    return {
        "status": status,
        "step_dir": str(capture["step_dir"]),
        "observed_words": [f"0x{word:04X}" for word in words],
        "play_ids": play_ids,
        "expected_timeout_s": EXPECTED_RESTRICTED_TIMEOUT_S,
        "tolerance_s": RESTRICTED_TIMEOUT_TOLERANCE_S,
        **markers,
    }


def run_restricted_hint_probe(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    capture = numeric.run_capture_step(
        step_dir=bundle_dir / "steps" / "restricted_hint_open_light",
        play_script=play_script,
        capture_s=42.0,
        texts=[WAKE_TEXT, OPEN_LIGHT_TEXT],
        initial_wait_s=14.0,
        gaps_s=[1.8],
        timed_sends=[
            (formal.BASELINE_RESET_AT_S, RESET_HEX),
            (10.0, PASSIVE_VOICE_OFF_HEX),
        ],
    )
    play_ids = formal.parse_play_ids(capture["log_text"])
    words = capture["observed_words"]
    status = (
        "PASS"
        if formal.contains_in_order(words, [0x0001])
        and 0x0009 not in words
        and formal.contains_in_order(play_ids, [65, 77, 123])
        and "MCU is not ready!" not in capture["log_text"]
        else "FAIL"
    )
    return {
        "status": status,
        "step_dir": str(capture["step_dir"]),
        "observed_words": [f"0x{word:04X}" for word in words],
        "play_ids": play_ids,
        "play_id_65_count": play_ids.count(65),
        "play_id_77_count": play_ids.count(77),
        "play_id_123_count": play_ids.count(123),
    }


def write_report(path: Path, bundle_dir: Path, summary: dict[str, Any]) -> None:
    timeout_probe = summary["restricted_timeout"]
    hint_probe = summary["restricted_hint"]
    lines = [
        "# 好太太关闭语音受限窗口专项探针",
        "",
        f"- 原始结果目录：`{bundle_dir}`",
        f"- 关闭语音后受限窗口：`{timeout_probe['status']}`",
        f"- 受限态提示 play id：`{hint_probe['status']}`",
        "",
        "## 受限窗口实测",
        "",
        f"- 需求值：`{timeout_probe['expected_timeout_s']}s`，允许偏差：`±{timeout_probe['tolerance_s']}s`",
        f"- 被动 `0x0012` 到达：`{timeout_probe['passive_voice_off_s']}`s",
        f"- 受限态唤醒综合起点：`{timeout_probe['wake_marker_s']}`s",
        f"- `0x0001`：`{timeout_probe['wake_frame_s']}`s",
        f"- `Wakeup:`：`{timeout_probe['wakeup_line_s']}`s",
        f"- `keyword:xiao hao xiao hao`：`{timeout_probe['wake_keyword_s']}`s",
        f"- `play id 77`：`{timeout_probe['restricted_play_id_s']}`s",
        f"- `play stop`：`{timeout_probe['restricted_play_stop_s']}`s",
        f"- `TIME_OUT`：`{timeout_probe['timeout_s']}`s",
        f"- `MODE=0`：`{timeout_probe['mode_zero_s']}`s",
        f"- `受限唤醒 -> TIME_OUT`：`{timeout_probe['wake_to_timeout_s']}`s",
        f"- `受限唤醒 -> MODE=0`：`{timeout_probe['wake_to_mode_zero_s']}`s",
        f"- `受限响应结束 -> TIME_OUT`：`{timeout_probe['response_end_to_timeout_s']}`s",
        f"- `受限响应结束 -> MODE=0`：`{timeout_probe['response_end_to_mode_zero_s']}`s",
        "",
        "## 受限态 play id 实测",
        "",
        f"- 阻断普通命令步骤：`{hint_probe['step_dir']}`",
        f"- 实测主动协议：`{', '.join(hint_probe['observed_words'])}`",
        f"- 实测 play id 序列：`{hint_probe['play_ids']}`",
        f"- `play id 65` 次数：`{hint_probe['play_id_65_count']}`",
        f"- `play id 77` 次数：`{hint_probe['play_id_77_count']}`",
        f"- `play id 123` 次数：`{hint_probe['play_id_123_count']}`",
        "",
        "## 证据",
        "",
        f"- 受限窗口步骤：`{timeout_probe['step_dir']}`",
        f"- 受限提示步骤：`{hint_probe['step_dir']}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    play_script = formal.resolve_listenai_play(update=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_name = f"{timestamp}_htt_voice_restricted_probe_r1"
    bundle_dir = RESULT_ROOT / suite_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "steps").mkdir(parents=True, exist_ok=True)

    restricted_timeout = run_restricted_timeout_probe(bundle_dir, play_script)
    restricted_hint = run_restricted_hint_probe(bundle_dir, play_script)

    summary = {
        "suite_name": suite_name,
        "bundle_dir": str(bundle_dir),
        "restricted_timeout": restricted_timeout,
        "restricted_hint": restricted_hint,
    }
    write_json(bundle_dir / "summary.json", summary)

    report_dir = DELIVERABLE_ROOT / "reports" / suite_name
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "summary.md"
    write_report(report_path, bundle_dir, summary)

    print(
        json.dumps(
            {
                "suite_name": suite_name,
                "bundle_dir": str(bundle_dir),
                "report_path": str(report_path),
                "restricted_timeout": restricted_timeout["status"],
                "restricted_hint": restricted_hint["status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
