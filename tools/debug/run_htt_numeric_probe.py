#!/usr/bin/env python
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
AUDIO_DIR = ROOT / "tools" / "audio"
if str(AUDIO_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIO_DIR))

from fan_validation_helper import ensure_cached_tts  # noqa: E402
from listenai_play_repo import resolve_listenai_play  # noqa: E402


DELIVERABLE_ROOT = ROOT / "deliverables" / "csk3022_htt_clothes_airer"
RESULT_ROOT = ROOT / "result" / "csk3022_htt_clothes_airer"
HANDSHAKE_SCRIPT = ROOT / "tools" / "serial" / "fan_proto_handshake_probe.py"

def env_text(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


DEVICE_KEY = env_text("TRISOLARIS_DEVICE_KEY", "VID_8765&PID_5678:8_804B35B_1_0000")
CTRL_PORT = env_text("TRISOLARIS_CTRL_PORT", "COM39")
LOG_PORT = env_text("TRISOLARIS_LOG_PORT", "COM38")
PROTO_PORT = env_text("TRISOLARIS_PROTO_PORT", "COM36")
CTRL_BAUD = 115200
LOG_BAUD = 115200
PROTO_BAUD = 9600

RESET_FRAME_HEX = "A5 FA 81 00 6C 8C FB"
BRAND_QUERY_HEX = "A5 FA 7F 01 02 21 FB"
BRAND_REPLY_HEX = "A5 FA 81 00 20 40 FB"
MODULE_HEARTBEAT_HEX = "A5 FA 7F 5A 5A D2 FB"
MODULE_HEARTBEAT_REPLY_HEX = "A5 FA 83 5A 5A D6 FB"
MCU_PING_HEX = "A5 FA 83 A5 A5 6C FB"

WAKE_WORD = 0x0001
VOL_UP_WORD = 0x0041
VOL_DOWN_WORD = 0x0042

BASELINE_READY_WAIT_S = 33.0
NORMAL_READY_WAIT_S = 18.0
BETWEEN_TEXT_WAIT_S = 1.6
POST_PLAY_GUARD_S = 12.0
TIMEOUT_CAPTURE_S = 80.0
NORMAL_VOICE_CAPTURE_S = 54.0
BOOT_OBSERVE_CAPTURE_S = 18.0
RESET_CAPTURE_S = 18.0
TIMEOUT_TOLERANCE_S = 1.5
EXPECTED_TIMEOUT_S = 25.0
EXPECTED_VOLUME_STEPS = 5
EXPECTED_DEFAULT_VOLUME_RANK = 3
MAX_VOICE_ATTEMPTS = 2
MAX_BOOT_ATTEMPTS = 2
MAX_RESET_ATTEMPTS = 2
MAX_VOLUME_PROBE_STEPS = EXPECTED_VOLUME_STEPS + 4
SUITE_REVISION = "r3"


def active_frame_hex(data_word: int) -> str:
    hi = (data_word >> 8) & 0xFF
    lo = data_word & 0xFF
    checksum = (0xA5 + 0xFA + 0x7F + hi + lo) & 0xFF
    return f"A5 FA 7F {hi:02X} {lo:02X} {checksum:02X} FB"


def passive_frame_hex(data_word: int) -> str:
    hi = (data_word >> 8) & 0xFF
    lo = data_word & 0xFF
    checksum = (0xA5 + 0xFA + 0x81 + hi + lo) & 0xFF
    return f"A5 FA 81 {hi:02X} {lo:02X} {checksum:02X} FB"


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def parse_boot_config(log_text: str) -> dict[str, int | str]:
    config: dict[str, int | str] = {}
    in_block = False
    for raw_line in log_text.splitlines():
        line = raw_line.replace("\x1b", "")
        if "Running Config" in line:
            in_block = True
            continue
        if not in_block:
            continue
        if "==========================" in line:
            if config:
                break
            continue
        match = re.match(r"\s*([A-Za-z][A-Za-z0-9 ]*[A-Za-z0-9])\s*:\s*([^\s]+)", line)
        if not match:
            continue
        key = match.group(1).replace(" ", "_").strip()
        value = match.group(2)
        config[key] = int(value) if value.isdigit() else value
    return config


def extract_refresh_config_values(log_text: str) -> list[int]:
    return [int(item) for item in re.findall(r"refresh config volume=(\d+)", log_text)]


def extract_runtime_volume_levels(log_text: str) -> list[int]:
    return [int(item) for item in re.findall(r"mini player set vol\s*:\s*(\d+)", log_text)]


def ordered_unique(values: list[int]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def read_timed_lines(step_dir: Path) -> list[dict[str, Any]]:
    payload = json.loads((step_dir / "com38_timed_lines.json").read_text(encoding="utf-8"))
    return payload.get("lines", [])


def parse_proto_frames(step_dir: Path) -> list[dict[str, Any]]:
    frames_path = step_dir / "com36_frames.txt"
    if not frames_path.exists():
        return []
    frames: list[dict[str, Any]] = []
    for raw_line in frames_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\[\s*([0-9.]+)\]\s+(.+)$", raw_line.strip())
        if not match:
            continue
        frame_hex = match.group(2).strip().upper()
        data_match = re.match(r"A5 FA [0-9A-F]{2} ([0-9A-F]{2}) ([0-9A-F]{2}) [0-9A-F]{2} FB", frame_hex)
        data_word = None
        if data_match:
            data_word = (int(data_match.group(1), 16) << 8) | int(data_match.group(2), 16)
        frames.append(
            {
                "t_s": round(float(match.group(1)), 3),
                "frame_hex": frame_hex,
                "data_word": data_word,
            }
        )
    return frames


def find_first_marker_time(lines: list[dict[str, Any]], patterns: list[str], after_s: float = 0.0) -> float | None:
    for item in lines:
        t_s = float(item.get("t_s", 0.0))
        if t_s < after_s:
            continue
        text = str(item.get("text", ""))
        if any(pattern in text for pattern in patterns):
            return round(t_s, 3)
    return None


def find_last_marker_time(lines: list[dict[str, Any]], patterns: list[str], before_s: float | None = None) -> float | None:
    found: float | None = None
    for item in lines:
        t_s = float(item.get("t_s", 0.0))
        if before_s is not None and t_s > before_s:
            break
        text = str(item.get("text", ""))
        if any(pattern in text for pattern in patterns):
            found = round(t_s, 3)
    return found


def find_first_data_word_time(frames: list[dict[str, Any]], data_word: int, after_s: float = 0.0) -> float | None:
    for item in frames:
        t_s = float(item.get("t_s", 0.0))
        if t_s < after_s:
            continue
        if item.get("data_word") == data_word:
            return round(t_s, 3)
    return None


def collect_data_words(frames: list[dict[str, Any]]) -> list[int]:
    return [int(item["data_word"]) for item in frames if isinstance(item.get("data_word"), int)]


def contains_words_in_order(words: list[int], expected: list[int]) -> bool:
    if not expected:
        return True
    index = 0
    for word in words:
        if word == expected[index]:
            index += 1
            if index >= len(expected):
                return True
    return False


def build_probe_command(
    result_dir: Path,
    capture_s: float,
    timed_sends: list[tuple[float, str]] | None = None,
    extra_respond_rules: list[tuple[str, str]] | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(HANDSHAKE_SCRIPT),
        "--result-dir",
        str(result_dir),
        "--proto-port",
        PROTO_PORT,
        "--proto-baudrate",
        str(PROTO_BAUD),
        "--log-port",
        LOG_PORT,
        "--log-baudrate",
        str(LOG_BAUD),
        "--ctrl-port",
        CTRL_PORT,
        "--ctrl-baudrate",
        str(CTRL_BAUD),
        "--command-preset",
        "normal",
        "--capture-s",
        str(capture_s),
        "--loglevel4-at-s",
        "4.5",
        "--respond",
        f"{BRAND_QUERY_HEX}={BRAND_REPLY_HEX}",
        "--respond",
        f"{MODULE_HEARTBEAT_HEX}={MODULE_HEARTBEAT_REPLY_HEX}",
        "--periodic",
        f"{MCU_PING_HEX}@4.0",
    ]
    for match_hex, reply_hex in extra_respond_rules or []:
        command.extend(["--respond", f"{match_hex}={reply_hex}"])
    for at_s, payload_hex in timed_sends or []:
        command.extend(["--inject-once", f"{payload_hex}@{at_s}"])
    return command


def play_audio(play_script: Path, text: str, label: str, out_path: Path) -> dict[str, Any]:
    audio_path, cached = ensure_cached_tts(text=text, voice="Microsoft Huihui Desktop", rate=0, label=label)
    completed = subprocess.run(
        [
            sys.executable,
            str(play_script),
            "play",
            "--audio-file",
            str(audio_path),
            "--device-key",
            DEVICE_KEY,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out_path.write_text(completed.stdout, encoding="utf-8")
    return {
        "text": text,
        "label": label,
        "audio_file": str(audio_path),
        "cached": cached,
        "exit_code": completed.returncode,
        "output_file": str(out_path),
    }


def run_capture_step(
    step_dir: Path,
    play_script: Path,
    capture_s: float,
    texts: list[str],
    initial_wait_s: float,
    gaps_s: list[float] | None = None,
    timed_sends: list[tuple[float, str]] | None = None,
    extra_respond_rules: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    step_dir.mkdir(parents=True, exist_ok=True)
    probe_stdout = step_dir / "probe_stdout.txt"
    probe_stderr = step_dir / "probe_stderr.txt"
    command = build_probe_command(
        step_dir,
        capture_s=capture_s,
        timed_sends=timed_sends,
        extra_respond_rules=extra_respond_rules,
    )
    playback_records: list[dict[str, Any]] = []

    with probe_stdout.open("w", encoding="utf-8") as stdout_handle, probe_stderr.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(command, stdout=stdout_handle, stderr=stderr_handle)
        probe_started = time.perf_counter()
        try:
            time.sleep(initial_wait_s)
            for index, text in enumerate(texts):
                play_started_at_s = round(time.perf_counter() - probe_started, 3)
                record = play_audio(
                    play_script=play_script,
                    text=text,
                    label=f"{step_dir.name}_{index + 1}",
                    out_path=step_dir / f"play_{index + 1:02d}.txt",
                )
                record["play_started_at_s"] = play_started_at_s
                playback_records.append(record)
                if index < len(texts) - 1:
                    gap_s = gaps_s[index] if gaps_s and index < len(gaps_s) else BETWEEN_TEXT_WAIT_S
                    time.sleep(gap_s)
            process.wait(timeout=capture_s + 20.0)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5.0)

    log_text = (step_dir / "com38_utf8.txt").read_text(encoding="utf-8", errors="replace")
    timed_lines = read_timed_lines(step_dir)
    proto_frames = parse_proto_frames(step_dir)
    boot_config = parse_boot_config(log_text)
    refresh_values = extract_refresh_config_values(log_text)
    runtime_levels = extract_runtime_volume_levels(log_text)
    words = collect_data_words(proto_frames)
    meta = {
        "step_dir": str(step_dir),
        "capture_s": capture_s,
        "initial_wait_s": initial_wait_s,
        "texts": texts,
        "gaps_s": gaps_s or [],
        "timed_sends": [{"at_s": at_s, "payload_hex": payload_hex} for at_s, payload_hex in (timed_sends or [])],
        "playback_records": playback_records,
        "boot_config": boot_config,
        "refresh_config_values": refresh_values,
        "runtime_volume_levels": runtime_levels,
        "timed_log_lines": len(timed_lines),
        "proto_frames_count": len(proto_frames),
        "observed_words": [f"0x{word:04X}" for word in words],
        "audio_play_starts_s": [item.get("play_started_at_s") for item in playback_records],
    }
    (step_dir / "analysis.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "step_dir": step_dir,
        "log_text": log_text,
        "timed_lines": timed_lines,
        "proto_frames": proto_frames,
        "observed_words": words,
        "boot_config": boot_config,
        "refresh_config_values": refresh_values,
        "runtime_volume_levels": runtime_levels,
        "meta": meta,
    }


def run_boot_observe_with_retry(bundle_dir: Path, play_script: Path, base_name: str) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    last_capture: dict[str, Any] | None = None
    for attempt in range(1, MAX_BOOT_ATTEMPTS + 1):
        capture = run_capture_step(
            step_dir=bundle_dir / "steps" / f"{base_name}_try{attempt}",
            play_script=play_script,
            capture_s=BOOT_OBSERVE_CAPTURE_S,
            texts=[],
            initial_wait_s=0.0,
            timed_sends=[],
        )
        boot_volume = capture["boot_config"].get("volume")
        attempt_row = {
            "attempt": attempt,
            "step_dir": str(capture["step_dir"]),
            "boot_config": capture["boot_config"],
            "boot_volume": boot_volume,
        }
        attempts.append(attempt_row)
        last_capture = capture
        if isinstance(boot_volume, int):
            return {
                "success": True,
                "capture": capture,
                "attempts": attempts,
                "boot_volume": boot_volume,
            }
    return {
        "success": False,
        "capture": last_capture,
        "attempts": attempts,
        "boot_volume": None,
    }


def run_voice_step_with_retry(
    bundle_dir: Path,
    play_script: Path,
    base_name: str,
    texts: list[str],
    expected_words: list[int],
    initial_wait_s: float,
    capture_s: float,
    timed_sends: list[tuple[float, str]] | None = None,
    gaps_s: list[float] | None = None,
    extra_respond_rules: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    last_capture: dict[str, Any] | None = None
    for attempt in range(1, MAX_VOICE_ATTEMPTS + 1):
        capture = run_capture_step(
            step_dir=bundle_dir / "steps" / f"{base_name}_try{attempt}",
            play_script=play_script,
            capture_s=capture_s,
            texts=texts,
            initial_wait_s=initial_wait_s,
            gaps_s=gaps_s,
            timed_sends=timed_sends,
            extra_respond_rules=extra_respond_rules,
        )
        observed_words = capture["observed_words"]
        attempt_ok = contains_words_in_order(observed_words, expected_words)
        attempts.append(
            {
                "attempt": attempt,
                "step_dir": str(capture["step_dir"]),
                "expected_words": [f"0x{word:04X}" for word in expected_words],
                "observed_words": [f"0x{word:04X}" for word in observed_words],
                "success": attempt_ok,
            }
        )
        last_capture = capture
        if attempt_ok:
            return {
                "success": True,
                "capture": capture,
                "attempts": attempts,
            }
    return {
        "success": False,
        "capture": last_capture,
        "attempts": attempts,
    }


def run_restore_default_with_retry(bundle_dir: Path, play_script: Path, base_name: str) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    last_reset: dict[str, Any] | None = None
    last_boot: dict[str, Any] | None = None
    for attempt in range(1, MAX_RESET_ATTEMPTS + 1):
        reset_capture = run_capture_step(
            step_dir=bundle_dir / "steps" / f"{base_name}_reset_try{attempt}",
            play_script=play_script,
            capture_s=RESET_CAPTURE_S,
            texts=[],
            initial_wait_s=0.0,
            timed_sends=[(6.0, RESET_FRAME_HEX)],
        )
        boot_result = run_boot_observe_with_retry(bundle_dir, play_script, f"{base_name}_boot_try{attempt}")
        boot_volume = boot_result.get("boot_volume")
        reset_ok = "restore factory response" in reset_capture["log_text"] and bool(reset_capture["refresh_config_values"])
        attempts.append(
            {
                "attempt": attempt,
                "reset_step_dir": str(reset_capture["step_dir"]),
                "boot_attempts": boot_result["attempts"],
                "reset_refresh_config_values": reset_capture["refresh_config_values"],
                "reset_runtime_levels": reset_capture["runtime_volume_levels"],
                "reset_ok": reset_ok,
                "boot_volume": boot_volume,
            }
        )
        last_reset = reset_capture
        last_boot = boot_result["capture"]
        if reset_ok and isinstance(boot_volume, int):
            return {
                "success": True,
                "attempts": attempts,
                "reset_capture": reset_capture,
                "boot_capture": boot_result["capture"],
                "boot_volume": boot_volume,
            }
    return {
        "success": False,
        "attempts": attempts,
        "reset_capture": last_reset,
        "boot_capture": last_boot,
        "boot_volume": None,
    }


def extract_timeout_markers(capture: dict[str, Any]) -> dict[str, Any]:
    lines = capture["timed_lines"]
    frames = capture["proto_frames"]
    playback_records = capture["meta"].get("playback_records", [])
    last_audio_play_at_s = None
    if playback_records:
        last_audio_play_at_s = max(
            float(item.get("play_started_at_s", 0.0))
            for item in playback_records
            if item.get("play_started_at_s") is not None
        )
    wake_frame_s = find_first_data_word_time(frames, WAKE_WORD)
    wakeup_line_s = find_first_marker_time(lines, ["Wakeup:"])
    wake_keyword_s = find_first_marker_time(lines, ["keyword:xiao hao xiao hao"])
    wake_response_play_start_s = (
        find_first_marker_time(lines, ["play start"], after_s=last_audio_play_at_s or 0.0)
        if last_audio_play_at_s is not None
        else None
    )
    wake_response_play_id_s = (
        find_first_marker_time(lines, ["play id :"], after_s=last_audio_play_at_s or 0.0)
        if last_audio_play_at_s is not None
        else None
    )
    mode_one_s = find_first_marker_time(lines, ["MODE=1"])
    wake_marker_s = (
        wake_frame_s
        or wake_keyword_s
        or wakeup_line_s
        or wake_response_play_start_s
        or wake_response_play_id_s
        or mode_one_s
    )
    timeout_s = find_first_marker_time(lines, ["TIME_OUT"], after_s=wake_marker_s or 0.0)
    mode_zero_s = find_first_marker_time(lines, ["MODE=0"], after_s=wake_marker_s or 0.0)
    play_stop_before_timeout_s = find_last_marker_time(lines, ["play stop"], before_s=timeout_s)
    wake_to_timeout_s = round(timeout_s - wake_marker_s, 3) if wake_marker_s is not None and timeout_s is not None else None
    wake_to_mode_zero_s = round(mode_zero_s - wake_marker_s, 3) if wake_marker_s is not None and mode_zero_s is not None else None
    response_end_to_timeout_s = (
        round(timeout_s - play_stop_before_timeout_s, 3)
        if timeout_s is not None and play_stop_before_timeout_s is not None
        else None
    )
    return {
        "wake_marker_s": wake_marker_s,
        "wake_frame_s": wake_frame_s,
        "wakeup_line_s": wakeup_line_s,
        "wake_keyword_s": wake_keyword_s,
        "wake_response_play_start_s": wake_response_play_start_s,
        "wake_response_play_id_s": wake_response_play_id_s,
        "mode_one_s": mode_one_s,
        "timeout_s": timeout_s,
        "mode_zero_s": mode_zero_s,
        "play_stop_before_timeout_s": play_stop_before_timeout_s,
        "wake_to_timeout_s": wake_to_timeout_s,
        "wake_to_mode_zero_s": wake_to_mode_zero_s,
        "response_end_to_timeout_s": response_end_to_timeout_s,
    }


def run_timeout_probe(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    final_capture: dict[str, Any] | None = None
    final_markers: dict[str, Any] | None = None
    for attempt in range(1, MAX_VOICE_ATTEMPTS + 1):
        capture = run_capture_step(
            step_dir=bundle_dir / "steps" / f"timeout_probe_try{attempt}",
            play_script=play_script,
            capture_s=TIMEOUT_CAPTURE_S,
            texts=["小好小好"],
            initial_wait_s=BASELINE_READY_WAIT_S,
            timed_sends=[(6.0, RESET_FRAME_HEX)],
        )
        markers = extract_timeout_markers(capture)
        attempts.append(
            {
                "attempt": attempt,
                "step_dir": str(capture["step_dir"]),
                **markers,
            }
        )
        final_capture = capture
        final_markers = markers
        if markers["wake_marker_s"] is not None and markers["timeout_s"] is not None and markers["mode_zero_s"] is not None:
            break

    timeout_status = (
        "PASS"
        if final_markers
        and isinstance(final_markers.get("wake_to_timeout_s"), float)
        and isinstance(final_markers.get("wake_to_mode_zero_s"), float)
        and abs(final_markers["wake_to_timeout_s"] - EXPECTED_TIMEOUT_S) <= TIMEOUT_TOLERANCE_S
        and abs(final_markers["wake_to_mode_zero_s"] - EXPECTED_TIMEOUT_S) <= TIMEOUT_TOLERANCE_S
        else "FAIL"
    )
    return {
        "status": timeout_status,
        "expected_timeout_s": EXPECTED_TIMEOUT_S,
        "attempts": attempts,
        "selected_step_dir": str(final_capture["step_dir"]) if final_capture else None,
        **(final_markers or {}),
    }


def run_volume_branch(
    bundle_dir: Path,
    play_script: Path,
    branch_name: str,
    command_text: str,
    expected_word: int,
) -> dict[str, Any]:
    restore_result = run_restore_default_with_retry(bundle_dir, play_script, f"volume_{branch_name}_default")
    default_boot_volume = restore_result.get("boot_volume")
    rows: list[dict[str, Any]] = []
    changed_codes: list[int] = []
    plateau_reached = False
    current_code = default_boot_volume if isinstance(default_boot_volume, int) else None
    boundary_code = current_code
    failure_reason: str | None = None

    if not restore_result["success"] or not isinstance(current_code, int):
        failure_reason = "恢复出厂后未拿到稳定默认音量启动值"
        return {
            "status": "FAIL",
            "restore_default": {
                "success": restore_result["success"],
                "attempts": restore_result["attempts"],
                "default_boot_volume": default_boot_volume,
            },
            "rows": rows,
            "changed_codes": changed_codes,
            "changes_to_boundary": 0,
            "plateau_reached": plateau_reached,
            "boundary_code": boundary_code,
            "failure_reason": failure_reason,
        }

    for index in range(1, MAX_VOLUME_PROBE_STEPS + 1):
        voice_result = run_voice_step_with_retry(
            bundle_dir=bundle_dir,
            play_script=play_script,
            base_name=f"volume_{branch_name}_step_{index}",
            texts=["小好小好", command_text],
            expected_words=[WAKE_WORD, expected_word],
            initial_wait_s=NORMAL_READY_WAIT_S,
            capture_s=NORMAL_VOICE_CAPTURE_S,
            extra_respond_rules=[(active_frame_hex(expected_word), passive_frame_hex(expected_word))],
        )
        boot_result = run_boot_observe_with_retry(bundle_dir, play_script, f"volume_{branch_name}_step_{index}_boot")
        next_code = boot_result.get("boot_volume")
        row = {
            "index": index,
            "voice_success": voice_result["success"],
            "voice_attempts": voice_result["attempts"],
            "voice_step_dir": str(voice_result["capture"]["step_dir"]) if voice_result.get("capture") else None,
            "boot_success": boot_result["success"],
            "boot_attempts": boot_result["attempts"],
            "boot_step_dir": str(boot_result["capture"]["step_dir"]) if boot_result.get("capture") else None,
            "before_boot_volume": current_code,
            "after_boot_volume": next_code,
        }
        rows.append(row)
        if not voice_result["success"]:
            failure_reason = f"{command_text} 第 {index} 次未形成稳定语音闭环"
            break
        if not isinstance(next_code, int):
            failure_reason = f"{command_text} 第 {index} 次后未读到启动 volume"
            break
        if next_code == current_code:
            plateau_reached = True
            boundary_code = next_code
            break
        changed_codes.append(next_code)
        current_code = next_code
        boundary_code = next_code
    else:
        failure_reason = f"{command_text} 超过 {MAX_VOLUME_PROBE_STEPS} 次仍未碰到边界"

    status = "PASS" if plateau_reached and failure_reason is None else "FAIL"
    return {
        "status": status,
        "restore_default": {
            "success": restore_result["success"],
            "attempts": restore_result["attempts"],
            "default_boot_volume": default_boot_volume,
            "reset_refresh_config_values": restore_result["reset_capture"]["refresh_config_values"] if restore_result.get("reset_capture") else [],
            "reset_runtime_levels": restore_result["reset_capture"]["runtime_volume_levels"] if restore_result.get("reset_capture") else [],
            "reset_step_dir": str(restore_result["reset_capture"]["step_dir"]) if restore_result.get("reset_capture") else None,
            "boot_step_dir": str(restore_result["boot_capture"]["step_dir"]) if restore_result.get("boot_capture") else None,
        },
        "rows": rows,
        "changed_codes": changed_codes,
        "changes_to_boundary": len(changed_codes),
        "plateau_reached": plateau_reached,
        "boundary_code": boundary_code,
        "failure_reason": failure_reason,
    }


def run_volume_probe(bundle_dir: Path, play_script: Path) -> dict[str, Any]:
    up_branch = run_volume_branch(
        bundle_dir=bundle_dir,
        play_script=play_script,
        branch_name="up",
        command_text="调大音量",
        expected_word=VOL_UP_WORD,
    )
    down_branch = run_volume_branch(
        bundle_dir=bundle_dir,
        play_script=play_script,
        branch_name="down",
        command_text="调小音量",
        expected_word=VOL_DOWN_WORD,
    )

    up_default = up_branch["restore_default"].get("default_boot_volume")
    down_default = down_branch["restore_default"].get("default_boot_volume")
    default_code_consistent = isinstance(up_default, int) and up_default == down_default
    default_code = up_default if default_code_consistent else None
    up_changes = up_branch.get("changes_to_boundary", 0)
    down_changes = down_branch.get("changes_to_boundary", 0)
    total_steps = up_changes + down_changes + 1 if default_code_consistent else None
    default_rank = down_changes + 1 if default_code_consistent else None
    inferred_sequence: list[int] = []
    if default_code_consistent and isinstance(default_code, int):
        inferred_sequence = list(reversed(down_branch.get("changed_codes", []))) + [default_code] + up_branch.get("changed_codes", [])

    step_count_status = (
        "PASS"
        if up_branch["status"] == "PASS"
        and down_branch["status"] == "PASS"
        and default_code_consistent
        and total_steps == EXPECTED_VOLUME_STEPS
        else "FAIL"
    )
    default_status = (
        "PASS"
        if up_branch["status"] == "PASS"
        and down_branch["status"] == "PASS"
        and default_code_consistent
        and default_rank == EXPECTED_DEFAULT_VOLUME_RANK
        else "FAIL"
    )

    return {
        "up_branch": up_branch,
        "down_branch": down_branch,
        "volume_steps": {
            "status": step_count_status,
            "default_code_consistent": default_code_consistent,
            "default_boot_volume": default_code,
            "changes_to_upper_boundary": up_changes,
            "changes_to_lower_boundary": down_changes,
            "upper_boundary_code": up_branch.get("boundary_code"),
            "lower_boundary_code": down_branch.get("boundary_code"),
            "measured_total_steps": total_steps,
            "expected_steps": EXPECTED_VOLUME_STEPS,
            "inferred_sequence": inferred_sequence,
        },
        "default_volume": {
            "status": default_status,
            "default_code_consistent": default_code_consistent,
            "default_boot_volume": default_code,
            "default_rank": default_rank,
            "expected_rank": EXPECTED_DEFAULT_VOLUME_RANK,
            "changes_to_upper_boundary": up_changes,
            "changes_to_lower_boundary": down_changes,
        },
    }


def write_summary_md(path: Path, bundle_dir: Path, timeout_result: dict[str, Any], volume_result: dict[str, Any]) -> None:
    volume_steps = volume_result["volume_steps"]
    default_volume = volume_result["default_volume"]
    up_branch = volume_result["up_branch"]
    down_branch = volume_result["down_branch"]
    lines = [
        "# 好太太数值专项验证报告",
        "",
        f"- 原始结果目录：`{bundle_dir}`",
        "- 口径说明：本轮仍是握手仿真夹具口径，但数值项全部按“先拿固件真实测量值，再与需求值比对”执行。",
        "- 音量相关主方法：先恢复出厂，再分别从默认位连续“调大音量 / 调小音量”探到上、下边界；夹具对主动调音量协议回同码 MCU 被动协议后，再用真实边界步数反推默认档位，并计算总档位数。",
        "",
        "## 1. 唤醒超时 `25s`",
        "",
        f"- 判定：`{timeout_result['status']}`",
        f"- 实测起点（优先取主动协议 `0x0001`）：`{timeout_result.get('wake_marker_s')}`s",
        f"- `TIME_OUT` 时间：`{timeout_result.get('timeout_s')}`s",
        f"- `MODE=0` 时间：`{timeout_result.get('mode_zero_s')}`s",
        f"- 实测 `唤醒响应 -> TIME_OUT`：`{timeout_result.get('wake_to_timeout_s')}`s",
        f"- 实测 `唤醒响应 -> MODE=0`：`{timeout_result.get('wake_to_mode_zero_s')}`s",
        f"- 旁证 `最后一次 play stop -> TIME_OUT`：`{timeout_result.get('response_end_to_timeout_s')}`s",
        f"- 需求：`{timeout_result.get('expected_timeout_s')}`s",
        f"- 最终证据：`{timeout_result.get('selected_step_dir')}`",
        f"- 重试记录：`{len(timeout_result.get('attempts', []))}` 次",
        "",
        "## 2. 恢复出厂默认音量 `3档`",
        "",
        f"- 判定：`{default_volume['status']}`",
        f"- 向上分支恢复出厂后的默认启动 `volume`：`{up_branch['restore_default'].get('default_boot_volume')}`",
        f"- 向下分支恢复出厂后的默认启动 `volume`：`{down_branch['restore_default'].get('default_boot_volume')}`",
        f"- 默认位到上边界的有效变化次数：`{default_volume.get('changes_to_upper_boundary')}`",
        f"- 默认位到下边界的有效变化次数：`{default_volume.get('changes_to_lower_boundary')}`",
        f"- 按“下边界变化次数 + 1”推得默认档位：`{default_volume.get('default_rank')}`档",
        f"- 需求默认档位：`{default_volume.get('expected_rank')}`档",
        f"- 向上分支证据：`{up_branch['restore_default'].get('reset_step_dir')}`、`{up_branch['restore_default'].get('boot_step_dir')}`",
        f"- 向下分支证据：`{down_branch['restore_default'].get('reset_step_dir')}`、`{down_branch['restore_default'].get('boot_step_dir')}`",
        "",
        "## 3. 音量总档位数 `5档`",
        "",
        f"- 判定：`{volume_steps['status']}`",
        f"- 向上试探变化次数：`{volume_steps.get('changes_to_upper_boundary')}`",
        f"- 向下试探变化次数：`{volume_steps.get('changes_to_lower_boundary')}`",
        f"- 实测总档位数（上边界变化次数 + 下边界变化次数 + 默认位 1）：`{volume_steps.get('measured_total_steps')}`",
        f"- 实测完整序列（按启动 `volume` 编码推得）：`{volume_steps.get('inferred_sequence')}`",
        f"- 下边界编码：`{volume_steps.get('lower_boundary_code')}`；上边界编码：`{volume_steps.get('upper_boundary_code')}`",
        f"- 需求档位数：`{volume_steps.get('expected_steps')}`",
        "",
        "## 4. 结论",
        "",
        "- 唤醒超时使用 `0x0001 / Wakeup -> TIME_OUT / MODE=0` 的真实时间差做结论，不再拿需求 `25s` 反推等待窗口。",
        "- 默认音量与总档位数使用“恢复出厂后的默认位 -> 连续调大 / 调小直到边界”的真实边界步数做结论，不直接拿需求档位倒推。",
        f"- 向上分支失败原因：`{up_branch.get('failure_reason')}`",
        f"- 向下分支失败原因：`{down_branch.get('failure_reason')}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_name = f"{timestamp}_htt_numeric_probe_{SUITE_REVISION}"
    bundle_dir = RESULT_ROOT / suite_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "steps").mkdir(parents=True, exist_ok=True)

    play_script = resolve_listenai_play(update=False)
    timeout_result = run_timeout_probe(bundle_dir, play_script)
    volume_result = run_volume_probe(bundle_dir, play_script)

    summary = {
        "suite_name": suite_name,
        "bundle_dir": str(bundle_dir),
        "timeout_result": timeout_result,
        "volume_result": volume_result,
    }
    (bundle_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report_dir = DELIVERABLE_ROOT / "reports" / suite_name
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "summary.md"
    write_summary_md(report_path, bundle_dir, timeout_result, volume_result)

    print(
        json.dumps(
            {
                "suite_name": suite_name,
                "bundle_dir": str(bundle_dir),
                "report_path": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
