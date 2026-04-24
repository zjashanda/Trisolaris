#!/usr/bin/env python
from __future__ import annotations

import json
import re
import sys
from dataclasses import replace
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
PASSIVE_008C_HEX = formal.passive_frame_hex(0x008C)

WAKE_TEXT = "\u5c0f\u597d\u5c0f\u597d"
OPEN_LIGHT_TEXT = "\u6253\u5f00\u7167\u660e"
MAX_VOL_TEXT = "\u6700\u5927\u97f3\u91cf"
REPORT_OFF_TEXT = "\u5173\u95ed\u64ad\u62a5\u529f\u80fd"
VOICE_OFF_TEXT = "\u8bed\u97f3\u529f\u80fd\u5173\u95ed"

REFRESH_RE = re.compile(
    r"refresh config volume=(?P<volume>\d+) voice=(?P<voice>\d+) wakeup=(?P<wakeup>\d+) play_mode=(?P<play_mode>\d+)"
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def last_refresh_state(log_text: str) -> dict[str, int] | None:
    last: dict[str, int] | None = None
    for match in REFRESH_RE.finditer(log_text):
        last = {key: int(value) for key, value in match.groupdict().items()}
    return last


def boot_observe(step_dir: Path, play_script: Path) -> dict[str, Any]:
    return numeric.run_capture_step(
        step_dir=step_dir,
        play_script=play_script,
        capture_s=numeric.BOOT_OBSERVE_CAPTURE_S,
        texts=[],
        initial_wait_s=0.0,
        timed_sends=[],
    )


def run_state_persist_check(
    bundle_dir: Path,
    play_script: Path,
    name: str,
    texts: list[str],
    expected_words: list[int],
    state_key: str,
    timed_sends: list[tuple[float, str]],
    initial_wait_s: float,
    capture_s: float,
    required_markers: list[str] | None = None,
    require_change_from: int | None = None,
) -> dict[str, Any]:
    set_capture = numeric.run_capture_step(
        step_dir=bundle_dir / "steps" / f"{name}_set",
        play_script=play_script,
        capture_s=capture_s,
        texts=texts,
        initial_wait_s=initial_wait_s,
        timed_sends=timed_sends,
    )
    refresh_state = last_refresh_state(set_capture["log_text"])
    target_value = refresh_state.get(state_key) if refresh_state else None
    words_ok = True if not expected_words else formal.contains_in_order(set_capture["observed_words"], expected_words)
    markers_ok = True if not required_markers else all(marker in set_capture["log_text"] for marker in required_markers)
    changed_ok = True if require_change_from is None else target_value != require_change_from
    set_success = (
        words_ok
        and markers_ok
        and "save config success" in set_capture["log_text"]
        and refresh_state is not None
        and state_key in refresh_state
        and changed_ok
    )
    reboot_capture = boot_observe(bundle_dir / "steps" / f"{name}_reboot", play_script)
    boot_value = reboot_capture["boot_config"].get(state_key)
    status = "PASS" if set_success and target_value == boot_value else "FAIL"
    return {
        "status": status,
        "state_key": state_key,
        "target_value": target_value,
        "boot_value": boot_value,
        "refresh_state": refresh_state,
        "set_step_dir": str(set_capture["step_dir"]),
        "reboot_step_dir": str(reboot_capture["step_dir"]),
        "observed_words": [f"0x{word:04X}" for word in set_capture["observed_words"]],
        "boot_config": reboot_capture["boot_config"],
        "save_config_success": "save config success" in set_capture["log_text"],
        "required_markers": required_markers or [],
    }


def run_voice_off_function_check(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, 3):
        capture = numeric.run_capture_step(
            step_dir=bundle_dir / "steps" / f"voice_persist_postboot_func_try{attempt}",
            play_script=play_script,
            capture_s=42.0,
            texts=[WAKE_TEXT, OPEN_LIGHT_TEXT],
            initial_wait_s=numeric.NORMAL_READY_WAIT_S,
            timed_sends=[],
        )
        words = capture["observed_words"]
        ok = (
            formal.contains_in_order(words, [0x0001])
            and 0x0009 not in words
            and "MCU is not ready!" not in capture["log_text"]
        )
        attempts.append(
            {
                "attempt": attempt,
                "status": "PASS" if ok else "FAIL",
                "step_dir": str(capture["step_dir"]),
                "observed_words": [f"0x{word:04X}" for word in words],
            }
        )
        if ok:
            break
    overall = "PASS" if any(item["status"] == "PASS" for item in attempts) else "FAIL"
    return {"status": overall, "attempts": attempts}


def run_passive_008c_check(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    capture = numeric.run_capture_step(
        step_dir=bundle_dir / "steps" / "passive_008c_no_broadcast",
        play_script=play_script,
        capture_s=18.0,
        texts=[],
        initial_wait_s=0.0,
        timed_sends=[(6.0, RESET_HEX), (10.0, PASSIVE_008C_HEX)],
    )
    log_text = capture["log_text"]
    play_ids = formal.parse_play_ids(log_text)
    status = "PASS" if (
        f"receive msg:: {RESET_HEX}" in log_text
        and f"receive msg:: {PASSIVE_008C_HEX}" in log_text
        and play_ids == [103]
        and log_text.count("play start") == 1
        and log_text.count("play id : ") == 1
        and "MCU is not ready!" not in log_text
    ) else "FAIL"
    return {
        "status": status,
        "step_dir": str(capture["step_dir"]),
        "play_ids": play_ids,
        "play_start_count": log_text.count("play start"),
        "play_id_count": log_text.count("play id : "),
    }


def run_passive_voice_on_recheck(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    template = next(case for case in formal.CASES if case.case_id == "PASSIVE-VOICE-ON-001")
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, 3):
        case = replace(template, case_id=f"PASSIVE-VOICE-ON-001-R{attempt:02d}")
        record = formal.run_case(case, bundle_dir, play_script)
        attempts.append(record)
    pass_count = sum(1 for item in attempts if item["status"] == "PASS")
    fail_count = sum(1 for item in attempts if item["status"] == "FAIL")
    blocked_count = sum(1 for item in attempts if item["status"] == "BLOCKED")
    status = "PASS" if fail_count == 0 and blocked_count == 0 else "FAIL"
    return {
        "status": status,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "blocked_count": blocked_count,
        "attempts": attempts,
    }


def write_report(path: Path, bundle_dir: Path, summary: dict[str, Any]) -> None:
    volume = summary["volume_persist"]
    report_mode = summary["report_mode_persist"]
    voice = summary["voice_persist"]
    voice_func = summary["voice_persist_postboot_function"]
    passive_008c = summary["passive_008c"]
    voice_on = summary["passive_voice_on_recheck"]
    lines = [
        "# \u597d\u592a\u592a follow-up \u68c0\u67e5\u62a5\u544a",
        "",
        f"- \u539f\u59cb\u7ed3\u679c\u76ee\u5f55\uff1a`{bundle_dir}`",
        f"- \u97f3\u91cf\u6389\u7535\u4fdd\u5b58\uff1a`{volume['status']}`\uff0c\u5b9e\u9645\u8bbe\u7f6e\u503c=`{volume['target_value']}`\uff0c\u91cd\u542f\u540e=`{volume['boot_value']}`",
        f"- \u64ad\u62a5\u5f00\u5173\u6389\u7535\u4fdd\u5b58\uff1a`{report_mode['status']}`\uff0c\u5b9e\u9645\u8bbe\u7f6e\u503c=`{report_mode['target_value']}`\uff0c\u91cd\u542f\u540e=`{report_mode['boot_value']}`",
        f"- \u8bed\u97f3\u5f00\u5173\u6389\u7535\u4fdd\u5b58\uff1a`{voice['status']}`\uff0c\u5b9e\u9645\u8bbe\u7f6e\u503c=`{voice['target_value']}`\uff0c\u91cd\u542f\u540e=`{voice['boot_value']}`",
        f"- \u8bed\u97f3\u5173\u95ed\u91cd\u542f\u540e\u529f\u80fd\u53d7\u9650\u5192\u70df\uff1a`{voice_func['status']}`",
        f"- \u88ab\u52a8 `0x008C`\uff1a`{passive_008c['status']}`\uff0cplay ids=`{passive_008c['play_ids']}`",
        f"- `PASSIVE-VOICE-ON-001` \u590d\u68c0\uff1a`{voice_on['status']}`\uff0cPASS=`{voice_on['pass_count']}` FAIL=`{voice_on['fail_count']}` BLOCKED=`{voice_on['blocked_count']}`",
        "",
        "## \u8bc1\u636e",
        "",
        f"- \u97f3\u91cf\u8bbe\u7f6e\u6b65\u9aa4\uff1a`{volume['set_step_dir']}`",
        f"- \u97f3\u91cf\u91cd\u542f\u89c2\u5bdf\uff1a`{volume['reboot_step_dir']}`",
        f"- \u64ad\u62a5\u5173\u95ed\u8bbe\u7f6e\u6b65\u9aa4\uff1a`{report_mode['set_step_dir']}`",
        f"- \u64ad\u62a5\u5173\u95ed\u91cd\u542f\u89c2\u5bdf\uff1a`{report_mode['reboot_step_dir']}`",
        f"- \u8bed\u97f3\u5173\u95ed\u8bbe\u7f6e\u6b65\u9aa4\uff1a`{voice['set_step_dir']}`",
        f"- \u8bed\u97f3\u5173\u95ed\u91cd\u542f\u89c2\u5bdf\uff1a`{voice['reboot_step_dir']}`",
        f"- \u8bed\u97f3\u5173\u95ed\u91cd\u542f\u540e\u529f\u80fd\u5192\u70df\uff1a`{voice_func['attempts'][0]['step_dir']}`",
        f"- \u88ab\u52a8 `0x008C` \u68c0\u67e5\uff1a`{passive_008c['step_dir']}`",
        f"- `PASSIVE-VOICE-ON-001` \u590d\u68c0\u7b2c 1 \u6b21\uff1a`{voice_on['attempts'][0]['result_dir']}`",
        f"- `PASSIVE-VOICE-ON-001` \u590d\u68c0\u7b2c 2 \u6b21\uff1a`{voice_on['attempts'][1]['result_dir']}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    play_script = formal.resolve_listenai_play(update=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_name = f"{timestamp}_htt_followup_checks_r1"
    bundle_dir = RESULT_ROOT / suite_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "steps").mkdir(parents=True, exist_ok=True)

    volume_persist = run_state_persist_check(
        bundle_dir=bundle_dir,
        play_script=play_script,
        name="volume_persist_max",
        texts=[],
        expected_words=[],
        state_key="volume",
        timed_sends=[
            (formal.BASELINE_RESET_AT_S, RESET_HEX),
            (10.0, formal.passive_frame_hex(0x0043)),
        ],
        initial_wait_s=0.0,
        capture_s=18.0,
        required_markers=[f"receive msg:: {formal.passive_frame_hex(0x0043)}"],
        require_change_from=2,
    )
    report_mode_persist = run_state_persist_check(
        bundle_dir=bundle_dir,
        play_script=play_script,
        name="report_mode_persist_off",
        texts=[WAKE_TEXT, REPORT_OFF_TEXT],
        expected_words=[0x0001, 0x0046],
        state_key="play_mode",
        timed_sends=[(formal.BASELINE_RESET_AT_S, RESET_HEX)],
        initial_wait_s=formal.BASELINE_READY_WAIT_S,
        capture_s=60.0,
        require_change_from=0,
    )
    voice_persist = run_state_persist_check(
        bundle_dir=bundle_dir,
        play_script=play_script,
        name="voice_persist_off",
        texts=[],
        expected_words=[],
        state_key="voice",
        timed_sends=[
            (formal.BASELINE_RESET_AT_S, RESET_HEX),
            (10.0, formal.passive_frame_hex(0x0012)),
        ],
        initial_wait_s=0.0,
        capture_s=18.0,
        required_markers=[f"receive msg:: {formal.passive_frame_hex(0x0012)}"],
        require_change_from=1,
    )
    voice_persist_postboot_function = run_voice_off_function_check(bundle_dir, play_script)
    if voice_persist["status"] == "PASS" and voice_persist_postboot_function["status"] == "FAIL":
        voice_persist["status"] = "FAIL"

    passive_008c = run_passive_008c_check(bundle_dir, play_script)
    passive_voice_on_recheck = run_passive_voice_on_recheck(bundle_dir, play_script)

    summary = {
        "suite_name": suite_name,
        "bundle_dir": str(bundle_dir),
        "volume_persist": volume_persist,
        "report_mode_persist": report_mode_persist,
        "voice_persist": voice_persist,
        "voice_persist_postboot_function": voice_persist_postboot_function,
        "passive_008c": passive_008c,
        "passive_voice_on_recheck": passive_voice_on_recheck,
    }
    write_json(bundle_dir / "summary.json", summary)

    report_dir = DELIVERABLE_ROOT / "reports" / suite_name
    report_dir.mkdir(parents=True, exist_ok=True)
    write_report(report_dir / "summary.md", bundle_dir, summary)

    print(json.dumps({"suite_name": suite_name, "bundle_dir": str(bundle_dir), "report_path": str(report_dir / "summary.md")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
