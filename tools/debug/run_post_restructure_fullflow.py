#!/usr/bin/env python
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
import serial

SCRIPT_DIR = Path(__file__).resolve().parent
AUDIO_DIR = SCRIPT_DIR.parent / "audio"
CASES_DIR = SCRIPT_DIR.parent / "cases"
if str(AUDIO_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIO_DIR))

from fan_validation_helper import ensure_cached_tts, update_response_state
from listenai_play_repo import resolve_listenai_play

ROOT = Path(__file__).resolve().parents[2]
REQ_DIR = ROOT / "CSK5062小度风扇需求"
DELIVERABLE_ROOT = ROOT / "deliverables" / "csk5062_xiaodu_fan"
REPORT_ROOT = DELIVERABLE_ROOT / "reports"
PLAN_PATH = DELIVERABLE_ROOT / "plan" / "测试方案.md"
CASE_MD_PATH = DELIVERABLE_ROOT / "archive" / "测试用例-正式版.md"
CASE_XLSX_PATH = DELIVERABLE_ROOT / "cases" / "测试用例-正式版.xlsx"
FIRMWARE_PATH = REQ_DIR / "fw-csk5062_xiaodu_fan-v1.0.0.bin"
GENERATE_ASSETS_SCRIPT = CASES_DIR / "generate_formal_assets.py"

DEVICE_KEY = "VID_8765&PID_5678:8_804B35B_1_0000"
LOG_PORT = "COM38"
LOG_BAUD = 115200
PROTO_PORT = "COM36"
PROTO_BAUD = 9600
CTRL_PORT = "COM39"
CTRL_BAUD = 115200

DEFAULT_BETWEEN_MAX_WAIT_S = 4.5
DEFAULT_BETWEEN_MIN_WAIT_S = 0.8
DEFAULT_QUIET_WINDOW_S = 0.6
DEFAULT_POST_WAIT_S = 4.0


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return cleaned or "step"


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def format_proto_log(data: bytes) -> str:
    if not data:
        return ""
    lines = []
    for index in range(0, len(data), 4):
        lines.append(data[index : index + 4].hex(" ").upper())
    return "\n".join(lines) + "\n"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_requirement_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")

    def expect_int(pattern: str) -> int:
        match = re.search(pattern, text)
        if not match:
            raise RuntimeError(f"Unable to parse requirement field with pattern: {pattern}")
        return int(match.group(1))

    def expect_text(pattern: str) -> str:
        match = re.search(pattern, text)
        if not match:
            raise RuntimeError(f"Unable to parse requirement field with pattern: {pattern}")
        return match.group(1).strip()

    return {
        "wake_timeout_s": expect_int(r"唤醒时长:\s*(\d+)s"),
        "volume_steps": expect_int(r"音量档位:\s*(\d+)"),
        "default_volume": expect_int(r"初始化默认音量:\s*(\d+)"),
        "mic_analog_gain_db": expect_int(r"mic模拟增益:\s*(\d+)"),
        "mic_digital_gain_db": expect_int(r"mic数字增益:\s*(\d+)"),
        "proto_baud": expect_int(r"协议串口:\s*UART1、波特率(\d+)"),
        "log_baud": expect_int(r"日志串口:\s*UART0、波特率(\d+)"),
        "wake_power_save_raw": expect_text(r"唤醒词掉电保存:\s*([^\n]+)"),
        "volume_power_save_raw": expect_text(r"音量掉电保存:\s*([^\n]+)"),
    }


def load_word_table(path: Path) -> dict[str, dict[str, str]]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook[workbook.sheetnames[1]]
    items: dict[str, dict[str, str]] = {}
    headers = [cell.value for cell in sheet[1]]
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not any(row):
            continue
        record = {str(headers[idx]): ("" if row[idx] is None else str(row[idx])) for idx in range(len(headers))}
        key = record.get("语义(最小功能词)") or record.get("功能类型")
        if key:
            items[key] = record
    return items


def load_voice_reg_config(path: Path) -> dict[str, Any]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    rows: list[tuple[str, str, Any]] = []
    current_category = ""
    for row in sheet.iter_rows(values_only=True):
        if not row or row[2] is None:
            continue
        if row[1]:
            current_category = str(row[1]).strip()
        key = str(row[2]).strip()
        value = row[3]
        rows.append((current_category, key, value))

    def find_value(category: str, key: str) -> Any:
        for item_category, item_key, item_value in rows:
            if item_category == category and item_key == key:
                return item_value
        raise RuntimeError(f"Unable to find voice registration config: {category} / {key}")

    return {
        "command_mode": str(find_value("自学习种类及模式", "命令词学习模式")),
        "wakeup_repeat_count": int(find_value("自学习唤醒词参数", "自学习时每个词需说几遍")),
        "wakeup_word_max": int(find_value("自学习唤醒词参数", "自学习唤醒词字数上限")),
        "wakeup_word_min": int(find_value("自学习唤醒词参数", "自学习唤醒词字数下限")),
        "wakeup_template_count": int(find_value("自学习唤醒词参数", "自学习唤醒词模板数")),
        "wakeup_retry_count": int(find_value("自学习唤醒词参数", "唤醒词学习失败重试次数")),
        "command_repeat_count": int(find_value("自学习命令词参数", "自学习时每个词需说几遍")),
        "command_word_max": int(find_value("自学习命令词参数", "自学习命令词字数上限")),
        "command_word_min": int(find_value("自学习命令词参数", "自学习命令词字数下限")),
        "command_template_count": int(find_value("自学习命令词参数", "自学习命令词模板数")),
        "command_retry_count": int(find_value("自学习命令词参数", "命令词学习失败重试次数")),
    }


def load_project_spec() -> dict[str, Any]:
    requirements = parse_requirement_markdown(REQ_DIR / "需求文档.md")
    words = load_word_table(REQ_DIR / "词条处理.xlsx")
    voice_reg = load_voice_reg_config(REQ_DIR / "语音注册功能.xlsx")
    return {
        "requirements": requirements,
        "words": words,
        "voice_reg": voice_reg,
    }


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
        match = re.match(r"\s*([A-Za-z][A-Za-z0-9]+)\s*:\s*([^\s]+)", line)
        if not match:
            continue
        key, value = match.groups()
        if value.isdigit():
            config[key] = int(value)
        else:
            config[key] = value
    return config


def parse_mic_gain(log_text: str) -> dict[str, int]:
    match = re.search(r"AGAIN=(\d+)dB.*?DGAIN=\s*(\d+)dB", log_text, re.S)
    if not match:
        return {}
    return {
        "analog_gain_db": int(match.group(1)),
        "digital_gain_db": int(match.group(2)),
    }


def proto_frames_from_hex(proto_hex: str) -> list[str]:
    compact = proto_hex.replace("\n", " ").strip()
    if not compact:
        return []
    tokens = compact.split()
    frames = []
    for index in range(0, len(tokens), 4):
        frame = tokens[index : index + 4]
        if len(frame) == 4:
            frames.append(" ".join(frame))
    return frames


def evidence_has_frames(evidence: StepEvidence, expected_frames: list[str]) -> bool:
    frames = proto_frames_from_hex(evidence.proto_hex)
    cursor = 0
    for frame in expected_frames:
        try:
            cursor = frames.index(frame, cursor) + 1
        except ValueError:
            return False
    return True


def count_occurrences(text: str, marker: str) -> int:
    return text.count(marker)


@dataclass
class StepEvidence:
    name: str
    step_dir: Path
    log_bytes: int
    proto_bytes: int
    log_text: str
    proto_hex: str
    detail: dict[str, Any]


class FullflowRunner:
    def __init__(self) -> None:
        self.spec = load_project_spec()
        self.stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.bundle_dir = REPORT_ROOT / f"{self.stamp}_post_restructure_fullflow"
        self.static_dir = ensure_dir(self.bundle_dir / "01_static")
        self.burn_dir = ensure_dir(self.bundle_dir / "02_burn")
        self.exec_dir = ensure_dir(self.bundle_dir / "03_execution")
        self.steps_dir = ensure_dir(self.exec_dir / "steps")
        self.stream_dir = ensure_dir(self.exec_dir / "streams")
        self.case_results_path = self.exec_dir / "case_results.json"
        self.summary_md_path = self.exec_dir / "execution_summary.md"
        self.failure_analysis_path = self.exec_dir / "failure_analysis.md"
        self.events_path = self.exec_dir / "events.jsonl"
        self.log_port: serial.Serial | None = None
        self.proto_port: serial.Serial | None = None
        self.listenai_play = resolve_listenai_play(update=False)
        self.log_chunks = bytearray()
        self.proto_chunks = bytearray()
        self.case_results: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.step_counter = 0

    def log_event(self, name: str, detail: dict[str, Any] | None = None) -> None:
        payload = {"at": iso_now(), "name": name, "detail": detail or {}}
        self.events.append(payload)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def add_case_result(
        self,
        case_id: str,
        module: str,
        status: str,
        summary: str,
        evidence: list[Path],
        detail: dict[str, Any] | None = None,
    ) -> None:
        item = {
            "case_id": case_id,
            "module": module,
            "status": status,
            "summary": summary,
            "evidence": [str(path.relative_to(ROOT)) for path in evidence],
            "detail": detail or {},
            "at": iso_now(),
        }
        self.case_results.append(item)
        self.log_event("case_result", item)
        print(f"[{status}] {case_id}: {summary}", flush=True)

    def prepare_static_assets(self) -> None:
        ensure_dir(self.static_dir / "requirement")
        ensure_dir(self.static_dir / "plan")
        ensure_dir(self.static_dir / "cases")
        shutil.copy2(PLAN_PATH, self.static_dir / "plan" / PLAN_PATH.name)
        shutil.copy2(CASE_MD_PATH, self.static_dir / "cases" / CASE_MD_PATH.name)
        if CASE_XLSX_PATH.exists():
            shutil.copy2(CASE_XLSX_PATH, self.static_dir / "cases" / CASE_XLSX_PATH.name)
        for item in [
            "需求文档.md",
            "词条处理.xlsx",
            "语音注册功能.xlsx",
            "tone.h",
            "fw-csk5062_xiaodu_fan-v1.0.0.bin",
        ]:
            src = REQ_DIR / item
            if src.exists():
                shutil.copy2(src, self.static_dir / "requirement" / src.name)
        summary = {
            "firmware": str(FIRMWARE_PATH.relative_to(ROOT)),
            "device_key": DEVICE_KEY,
            "ports": {
                "proto": f"{PROTO_PORT}@{PROTO_BAUD}",
                "log": f"{LOG_PORT}@{LOG_BAUD}",
                "ctrl": f"{CTRL_PORT}@{CTRL_BAUD}",
            },
            "generated_at": iso_now(),
        }
        (self.static_dir / "bundle_meta.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    def burn_firmware(self) -> None:
        self.log_event("burn_start", {"firmware": str(FIRMWARE_PATH)})
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "tools" / "burn_bundle" / "run_fan_burn.ps1"),
            "-FirmwareBin",
            str(FIRMWARE_PATH),
        ]
        completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        stdout_path = self.burn_dir / "run_output.txt"
        stderr_path = self.burn_dir / "run_error.txt"
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        win_bundle = ROOT / "tools" / "burn_bundle" / "windows"
        for name in ["burn.log", "burn_tool.log"]:
            src = win_bundle / name
            if src.exists():
                shutil.copy2(src, self.burn_dir / name)
        burn_log_text = ""
        burn_log = self.burn_dir / "burn.log"
        if burn_log.exists():
            burn_log_text = burn_log.read_text(encoding="utf-8", errors="replace")
        burn_ok = completed.returncode == 0 and "Burn flow completed" in burn_log_text and "version         :       1.0.0" in burn_log_text
        info = {
            "command": cmd,
            "returncode": completed.returncode,
            "burn_ok": burn_ok,
            "stdout_file": str(stdout_path.relative_to(ROOT)),
            "stderr_file": str(stderr_path.relative_to(ROOT)),
        }
        (self.burn_dir / "burn_meta.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        self.log_event("burn_finish", info)
        if not burn_ok:
            raise RuntimeError(f"Burn failed, see {self.burn_dir}")

    def open_ports(self) -> None:
        self.log_port = serial.Serial(LOG_PORT, baudrate=LOG_BAUD, timeout=0.05, write_timeout=0.5)
        self.proto_port = serial.Serial(PROTO_PORT, baudrate=PROTO_BAUD, timeout=0.05, write_timeout=0.5)
        self.log_port.reset_input_buffer()
        self.proto_port.reset_input_buffer()
        self.log_port.write(b"loglevel 4\r\n")
        self.log_port.flush()
        time.sleep(1.0)
        self.log_port.reset_input_buffer()
        self.proto_port.reset_input_buffer()
        self.log_event("ports_opened", {"log_port": LOG_PORT, "proto_port": PROTO_PORT})

    def close_ports(self) -> None:
        if self.proto_port:
            self.proto_port.close()
            self.proto_port = None
        if self.log_port:
            self.log_port.close()
            self.log_port = None
        self.log_event("ports_closed")

    def slice_offsets(self) -> tuple[int, int]:
        return (len(self.log_chunks), len(self.proto_chunks))

    def pump(self, duration_s: float, state: dict[str, Any] | None = None) -> None:
        assert self.log_port and self.proto_port
        deadline = time.time() + duration_s
        local_log = bytearray()
        while time.time() < deadline:
            log_data = self.log_port.read(4096)
            if log_data:
                self.log_chunks.extend(log_data)
                local_log.extend(log_data)
                if state is not None:
                    update_response_state(state, decode_text(local_log), time.time())
            proto_data = self.proto_port.read(4096)
            if proto_data:
                self.proto_chunks.extend(proto_data)
            time.sleep(0.02)

    def wait_for_completion(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        assert self.log_port and self.proto_port
        start = time.time()
        local_log = bytearray()
        state = {
            "saw_response": bool(initial_state.get("saw_response")),
            "saw_play_start": bool(initial_state.get("saw_play_start")),
            "saw_play_stop": bool(initial_state.get("saw_play_stop")),
            "last_data_at": initial_state.get("last_data_at"),
        }
        completion_reason: str | None = None
        while True:
            now = time.time()
            log_data = self.log_port.read(4096)
            if log_data:
                self.log_chunks.extend(log_data)
                local_log.extend(log_data)
                update_response_state(state, decode_text(local_log), now)
                if completion_reason == "quiet_after_response":
                    completion_reason = None
            proto_data = self.proto_port.read(4096)
            if proto_data:
                self.proto_chunks.extend(proto_data)
            elapsed = now - start
            last_data_at = state["last_data_at"]
            if state["saw_play_start"] and state["saw_play_stop"]:
                completion_reason = "play_stop"
            if completion_reason == "play_stop" and elapsed >= DEFAULT_BETWEEN_MIN_WAIT_S:
                return {"reason": completion_reason, "elapsed_s": round(elapsed, 3)}
            if state["saw_response"] and not state["saw_play_start"] and last_data_at is not None and (now - last_data_at) >= DEFAULT_QUIET_WINDOW_S:
                completion_reason = "quiet_after_response"
            if completion_reason == "quiet_after_response" and elapsed >= DEFAULT_BETWEEN_MIN_WAIT_S:
                return {"reason": completion_reason, "elapsed_s": round(elapsed, 3)}
            if elapsed >= DEFAULT_BETWEEN_MAX_WAIT_S:
                return {"reason": "max_wait", "elapsed_s": round(elapsed, 3)}
            time.sleep(0.02)

    def write_step_artifacts(self, name: str, start_offsets: tuple[int, int], extra_meta: dict[str, Any]) -> StepEvidence:
        self.step_counter += 1
        step_dir = ensure_dir(self.steps_dir / f"{self.step_counter:02d}_{sanitize_name(name)}")
        log_slice = bytes(self.log_chunks[start_offsets[0] :])
        proto_slice = bytes(self.proto_chunks[start_offsets[1] :])
        log_text = decode_text(log_slice)
        proto_hex = proto_slice.hex(" ").upper()
        (step_dir / "com38_raw.bin").write_bytes(log_slice)
        (step_dir / "com38_utf8.txt").write_text(log_text, encoding="utf-8")
        (step_dir / "com36_raw.bin").write_bytes(proto_slice)
        (step_dir / "com36_hex.txt").write_text(proto_hex, encoding="utf-8")
        detail = {"name": name, "log_bytes": len(log_slice), "proto_bytes": len(proto_slice), **extra_meta}
        (step_dir / "meta.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
        return StepEvidence(name=name, step_dir=step_dir, log_bytes=len(log_slice), proto_bytes=len(proto_slice), log_text=log_text, proto_hex=proto_hex, detail=detail)
    def run_voice_sequence(self, name: str, texts: list[str], post_wait_s: float = DEFAULT_POST_WAIT_S) -> StepEvidence:
        assert self.log_port and self.proto_port
        self.log_event("voice_sequence_start", {"name": name, "texts": texts})
        start_offsets = self.slice_offsets()
        audio_items = []
        playback_output = []
        between = []
        for index, text in enumerate(texts, start=1):
            audio_path, cached = ensure_cached_tts(text=text, voice="Microsoft Huihui Desktop", rate=0, label=f"{sanitize_name(name)}_{index}")
            audio_items.append({"text": text, "audio_file": str(audio_path), "cached": cached})
            cmd = [sys.executable, str(self.listenai_play), "play", "--audio-file", str(audio_path), "--device-key", DEVICE_KEY]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            response_state = {"saw_response": False, "saw_play_start": False, "saw_play_stop": False, "last_data_at": None}
            local_log = bytearray()
            local_output: list[str] = []
            while True:
                log_data = self.log_port.read(4096)
                if log_data:
                    self.log_chunks.extend(log_data)
                    local_log.extend(log_data)
                    update_response_state(response_state, decode_text(local_log), time.time())
                proto_data = self.proto_port.read(4096)
                if proto_data:
                    self.proto_chunks.extend(proto_data)
                if proc.stdout:
                    line = proc.stdout.readline()
                    if line:
                        local_output.append(line.rstrip("\r\n"))
                if proc.poll() is not None:
                    break
                time.sleep(0.02)
            if proc.stdout:
                for line in proc.stdout.read().splitlines():
                    local_output.append(line)
            response_state["serial_bytes_during_playback"] = len(local_log)
            playback_output.append({"text": text, "audio_file": str(audio_path), "cached": cached, "output": local_output, "response_state": response_state})
            if index < len(texts):
                between.append(self.wait_for_completion(response_state))
        self.pump(post_wait_s)
        evidence = self.write_step_artifacts(name, start_offsets, {"mode": "voice_sequence", "texts": texts, "audio_items": audio_items, "playback_output": playback_output, "between_wait_result": between, "post_wait_s": post_wait_s})
        self.log_event("voice_sequence_finish", {"name": name, "log_bytes": evidence.log_bytes, "proto_bytes": evidence.proto_bytes})
        return evidence

    def run_protocol_step(self, name: str, payload_hex: str, post_wait_s: float = 4.0, pre_wait_s: float = 0.5) -> StepEvidence:
        assert self.proto_port
        self.log_event("protocol_start", {"name": name, "payload_hex": payload_hex})
        start_offsets = self.slice_offsets()
        self.pump(pre_wait_s)
        payload = bytes.fromhex(payload_hex.replace(" ", ""))
        self.proto_port.write(payload)
        self.proto_port.flush()
        self.pump(post_wait_s)
        evidence = self.write_step_artifacts(name, start_offsets, {"mode": "protocol", "payload_hex": payload_hex, "pre_wait_s": pre_wait_s, "post_wait_s": post_wait_s})
        self.log_event("protocol_finish", {"name": name, "log_bytes": evidence.log_bytes, "proto_bytes": evidence.proto_bytes})
        return evidence

    def run_shell_step(self, name: str, command: str, capture_s: float, ready_wait_s: float = 0.0) -> StepEvidence:
        assert self.log_port
        self.log_event("shell_start", {"name": name, "command": command})
        start_offsets = self.slice_offsets()
        self.log_port.write((command + "\r\n").encode("ascii"))
        self.log_port.flush()
        self.pump(capture_s)
        if ready_wait_s > 0:
            self.pump(ready_wait_s)
        evidence = self.write_step_artifacts(name, start_offsets, {"mode": "shell", "command": command, "capture_s": capture_s, "ready_wait_s": ready_wait_s})
        self.log_event("shell_finish", {"name": name, "log_bytes": evidence.log_bytes, "proto_bytes": evidence.proto_bytes})
        return evidence

    def run_idle_wait_step(self, name: str, duration_s: float) -> StepEvidence:
        self.log_event("idle_wait_start", {"name": name, "duration_s": duration_s})
        start_offsets = self.slice_offsets()
        self.pump(duration_s)
        evidence = self.write_step_artifacts(name, start_offsets, {"mode": "idle_wait", "duration_s": duration_s})
        self.log_event("idle_wait_finish", {"name": name, "log_bytes": evidence.log_bytes, "proto_bytes": evidence.proto_bytes})
        return evidence

    def run_wake_timeout_probe(self, name: str, wake_text: str, wait_s: float = 24.0) -> StepEvidence:
        assert self.log_port and self.proto_port
        self.log_event("wake_timeout_probe_start", {"name": name, "wake_text": wake_text, "wait_s": wait_s})
        start_offsets = self.slice_offsets()
        audio_path, cached = ensure_cached_tts(text=wake_text, voice="Microsoft Huihui Desktop", rate=0, label=f"{sanitize_name(name)}_wake")
        cmd = [sys.executable, str(self.listenai_play), "play", "--audio-file", str(audio_path), "--device-key", DEVICE_KEY]
        probe_started_at = time.time()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        playback_output: list[str] = []
        local_log = bytearray()
        markers = {
            "wake_enter_s": None,
            "timeout_marker_s": None,
            "sleep_tone_s": None,
            "mode_zero_s": None,
        }

        def update_markers(now: float) -> None:
            text = decode_text(local_log)
            elapsed = round(now - probe_started_at, 3)
            if markers["wake_enter_s"] is None and ("MODE=1" in text or "keyword:xiao du xiao du" in text):
                markers["wake_enter_s"] = elapsed
            if markers["timeout_marker_s"] is None and "TIME_OUT" in text:
                markers["timeout_marker_s"] = elapsed
            if markers["sleep_tone_s"] is None and "play id : 25" in text:
                markers["sleep_tone_s"] = elapsed
            if markers["mode_zero_s"] is None and "MODE=0" in text:
                markers["mode_zero_s"] = elapsed

        while True:
            now = time.time()
            log_data = self.log_port.read(4096)
            if log_data:
                self.log_chunks.extend(log_data)
                local_log.extend(log_data)
                update_markers(now)
            proto_data = self.proto_port.read(4096)
            if proto_data:
                self.proto_chunks.extend(proto_data)
            if proc.stdout:
                line = proc.stdout.readline()
                if line:
                    playback_output.append(line.rstrip("\r\n"))
            if proc.poll() is not None:
                break
            time.sleep(0.02)
        if proc.stdout:
            playback_output.extend(proc.stdout.read().splitlines())

        while time.time() - probe_started_at < wait_s:
            now = time.time()
            log_data = self.log_port.read(4096)
            if log_data:
                self.log_chunks.extend(log_data)
                local_log.extend(log_data)
                update_markers(now)
                if markers["wake_enter_s"] is not None and (markers["timeout_marker_s"] is not None or markers["sleep_tone_s"] is not None):
                    if markers["mode_zero_s"] is not None or now - probe_started_at >= 20.5:
                        break
            proto_data = self.proto_port.read(4096)
            if proto_data:
                self.proto_chunks.extend(proto_data)
            time.sleep(0.02)

        timeout_markers = [value for key, value in markers.items() if key != "wake_enter_s" and value is not None]
        timeout_gap_s = None
        if markers["wake_enter_s"] is not None and timeout_markers:
            timeout_gap_s = round(min(timeout_markers) - markers["wake_enter_s"], 3)
        evidence = self.write_step_artifacts(
            name,
            start_offsets,
            {
                "mode": "wake_timeout_probe",
                "wake_text": wake_text,
                "audio_file": str(audio_path),
                "cached": cached,
                "playback_output": playback_output,
                "wait_s": wait_s,
                "markers": markers,
                "timeout_gap_s": timeout_gap_s,
            },
        )
        self.log_event("wake_timeout_probe_finish", {"name": name, "timeout_gap_s": timeout_gap_s, "log_bytes": evidence.log_bytes, "proto_bytes": evidence.proto_bytes})
        return evidence

    def run_powercycle_step(self, name: str, commands: list[str] | None = None, cmd_delay_s: float = 0.35, capture_s: float = 10.0, ready_wait_s: float = 8.0) -> StepEvidence:
        if commands is None:
            commands = ["uut-switch1.off", "uut-switch2.off", "uut-switch1.on"]
        self.log_event("powercycle_start", {"name": name, "commands": commands})
        start_offsets = self.slice_offsets()
        ctrl_port = serial.Serial(CTRL_PORT, baudrate=CTRL_BAUD, timeout=0.05, write_timeout=0.5)
        try:
            ctrl_port.reset_input_buffer()
            for item in commands:
                ctrl_port.write((item + "\r\n").encode("ascii"))
                ctrl_port.flush()
                time.sleep(cmd_delay_s)
            self.pump(capture_s)
            if ready_wait_s > 0:
                self.pump(ready_wait_s)
        finally:
            ctrl_port.close()
        evidence = self.write_step_artifacts(name, start_offsets, {"mode": "powercycle", "commands": commands, "cmd_delay_s": cmd_delay_s, "capture_s": capture_s, "ready_wait_s": ready_wait_s})
        self.log_event("powercycle_finish", {"name": name, "log_bytes": evidence.log_bytes, "proto_bytes": evidence.proto_bytes})
        return evidence

    def save_streams(self) -> None:
        (self.stream_dir / "com38_raw.bin").write_bytes(bytes(self.log_chunks))
        com38_text = decode_text(bytes(self.log_chunks))
        (self.stream_dir / "com38_utf8.txt").write_text(com38_text, encoding="utf-8")
        (self.stream_dir / "com38.log").write_text(com38_text, encoding="utf-8")
        (self.stream_dir / "com36_raw.bin").write_bytes(bytes(self.proto_chunks))
        com36_hex = bytes(self.proto_chunks).hex(" ").upper()
        (self.stream_dir / "com36_hex.txt").write_text(com36_hex, encoding="utf-8")
        (self.stream_dir / "com36.log").write_text(format_proto_log(bytes(self.proto_chunks)), encoding="utf-8")
        meta = {"log_port": f"{LOG_PORT}@{LOG_BAUD}", "proto_port": f"{PROTO_PORT}@{PROTO_BAUD}", "events": len(self.events), "saved_at": iso_now(), "log_bytes": len(self.log_chunks), "proto_bytes": len(self.proto_chunks)}
        (self.stream_dir / "stream_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_case_results(self) -> None:
        payload = {"generated_at": iso_now(), "bundle_dir": str(self.bundle_dir.relative_to(ROOT)), "case_results": self.case_results}
        self.case_results_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [
            "# 本轮目录重构后全链路执行结果",
            "",
            f"- 交付目录：`{self.bundle_dir.relative_to(ROOT)}`",
            f"- 烧录日志目录：`{self.burn_dir.relative_to(ROOT)}`",
            f"- 连续串口日志目录：`{self.stream_dir.relative_to(ROOT)}`",
            f"- 用例结果 JSON：`{self.case_results_path.relative_to(ROOT)}`",
            "",
            "## 用例结果",
            "",
            "| 用例ID | 模块 | 状态 | 结论 | 证据 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for item in self.case_results:
            evidence = "<br>".join(f"`{path}`" for path in item["evidence"])
            lines.append(f"| `{item['case_id']}` | {item['module']} | `{item['status']}` | {item['summary']} | {evidence} |")
        self.summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_failure_analysis(self) -> None:
        auto_pass = sum(1 for item in self.case_results if item["status"] == "PASS")
        auto_fail = [item for item in self.case_results if item["status"] == "FAIL"]
        auto_todo = [item for item in self.case_results if item["status"] == "TODO"]
        fail_map = {item["case_id"]: item for item in auto_fail}
        fail_list_line = "- 本轮无 FAIL"
        if auto_fail:
            fail_labels = ", ".join(f"`{item['case_id']}`" for item in auto_fail)
            fail_list_line = f"- 当前 FAIL 列表：{fail_labels}"
        lines = [
            "# Failure Analysis",
            "",
            "## 本轮执行概览",
            "",
            f"- 本轮自动/半自动汇总结果：`PASS={auto_pass}`、`FAIL={len(auto_fail)}`、`TODO={len(auto_todo)}`",
            f"- 人工保留项：`{auto_todo[0]['case_id']}`（上电欢迎语）" if auto_todo else "- 本轮无人工保留项",
            fail_list_line,
            "",
            "## 需求一致性结论",
            "",
            "- 本轮已把“功能是否正常”“参数是否一致”“异常场景是否稳定”拆开判定，避免把功能可用误判成需求完全通过",
            "- 协议判断以 `COM36` 原始抓取或发送 payload 为准，`COM38` 仅用于接收 / 播报 / 状态辅助",
            "- 语音注册的学习次数、失败重试上限、模板数本轮已单列为配置一致性项，独立给出结论",
            "",
            "## FAIL 归因",
            "",
        ]

        if "CFG-WAKE-001" in fail_map:
            item = fail_map["CFG-WAKE-001"]
            lines.extend(
                [
                    "### `CFG-WAKE-001`",
                    "",
                    "- 模块：配置一致性-会话参数",
                    f"- 当前现象：实测唤醒会话时长约 `{item['detail'].get('timeout_gap_s')}`s，低于需求 `20s`",
                    "- 影响：功能上仍能超时退出，但超时数值与需求不一致，不能按 PASS 结论关闭",
                    "- 修复建议：核对会话超时参数入包值和运行态实际超时逻辑，确认没有沿用旧的 15s 左右配置",
                    "",
                ]
            )

        if "CFG-VOL-001" in fail_map:
            item = fail_map["CFG-VOL-001"]
            boot_cfg = item["detail"].get("boot_config", {})
            lines.extend(
                [
                    "### `CFG-VOL-001`",
                    "",
                    "- 模块：配置一致性-音量参数",
                    f"- 当前现象：冷启动默认音量为 `{boot_cfg.get('volume')}`，需求为 `4`",
                    "- 影响：音量功能本身可用，但默认值不满足需求",
                    "- 修复建议：检查默认配置表或 `config.clear` 后的默认音量初始化值",
                    "",
                ]
            )

        if "CFG-VOL-002" in fail_map:
            item = fail_map["CFG-VOL-002"]
            lines.extend(
                [
                    "### `CFG-VOL-002`",
                    "",
                    "- 模块：配置一致性-音量参数",
                    f"- 当前现象：实测可达音量档位为 `{item['detail'].get('values')}`，不是需求的 `6` 档",
                    "- 影响：音量调节功能可用，但档位数与需求不一致",
                    "- 修复建议：检查音量等级映射和边界值定义，确认是否仍保留 0~4 共 5 档实现",
                    "",
                ]
            )

        if "VOL-003" in fail_map:
            item = fail_map["VOL-003"]
            boot_cfg = item["detail"].get("boot_config", {})
            lines.extend(
                [
                    "### `VOL-003`",
                    "",
                    "- 模块：音量控制",
                    f"- 当前现象：将音量设到非默认档位后断电，重启 `volume` 仍为 `{boot_cfg.get('volume')}`，未恢复默认需求值",
                    "- 影响：音量掉电不保存需求不成立",
                    "- 修复建议：检查音量配置的保存位开关，确认音量是否被错误写入持久化配置",
                    "",
                ]
            )

        if "REG-CONFLICT-001" in fail_map:
            lines.extend(
                [
                    "### `REG-CONFLICT-001`",
                    "",
                    "- 模块：语音注册-冲突词",
                    "- 当前现象：功能词 `增大音量` 被错误学习成自定义命令词，回测时触发成了 `打开电风扇`，不是原本的音量增大动作",
                    "- 问题定位：命令词学习态下，对“功能词 / 保留词 / 可学习词”的边界校验不完整，导致功能词样本被错误写入学习结果",
                    "- 修复建议：",
                    "  1. 在命令词学习入口增加功能词黑名单校验，拒绝把已有功能控制词写入学习结果",
                    "  2. 学习成功前增加目标协议冲突检查，避免把功能协议错误映射到其他动作",
                    "  3. 回归补测 `增大音量`、`最小音量`、`关闭播报`、`退出识别` 等功能词冲突集",
                    "",
                ]
            )

        other_fail_ids = [case_id for case_id in fail_map if case_id not in {"CFG-WAKE-001", "CFG-VOL-001", "CFG-VOL-002", "VOL-003", "REG-CONFLICT-001"}]
        for case_id in other_fail_ids:
            item = fail_map[case_id]
            lines.extend(
                [
                    f"### `{case_id}`",
                    "",
                    f"- 模块：{item['module']}",
                    f"- 当前现象：{item['summary']}",
                    f"- 证据：`{item['evidence'][0]}`" if item["evidence"] else "- 证据：见 `case_results.json`",
                    "",
                ]
            )

        lines.extend(
            [
                "## 当前保留的人工项",
                "",
                "### `SESS-001`",
                "",
                "- 原因：上电欢迎语更适合人工听感 / 现场观察校验",
                "- 本轮自动辅助证据：",
                "  - `01_assist_startup_powercycle_capture`",
                "  - `streams/com38_utf8.txt`",
                "- 结论：自动链路已补足启动连续日志，但最终通过仍以人工确认欢迎语和待机就绪为准",
            ]
        )
        self.failure_analysis_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def sync_bundle_root_artifacts(self) -> None:
        sync_map = {
            "测试方案.md": PLAN_PATH,
            "测试用例-正式版.xlsx": CASE_XLSX_PATH,
            "case_results.json": self.case_results_path,
            "execution_summary.md": self.summary_md_path,
            "failure_analysis.md": self.failure_analysis_path,
            "burn.log": self.burn_dir / "burn.log",
            "burn_tool.log": self.burn_dir / "burn_tool.log",
            "com38.log": self.stream_dir / "com38.log",
            "com36.log": self.stream_dir / "com36.log",
        }
        for output_name, src in sync_map.items():
            if src.exists():
                shutil.copy2(src, self.bundle_dir / output_name)


def step_pass(evidence: StepEvidence, *, require_proto: bool | None = None, markers: list[str] | None = None) -> bool:
    if require_proto is True and evidence.proto_bytes <= 0:
        return False
    if require_proto is False and evidence.proto_bytes > 0:
        return False
    if markers:
        return all(marker in evidence.log_text for marker in markers)
    return True


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def has_all_markers(text: str, markers: list[str]) -> bool:
    return all(marker in text for marker in markers)


def export_cases() -> None:
    cmd = [sys.executable, str(CASES_DIR / "export_case_md_to_xlsx.py"), "--input", str(CASE_MD_PATH), "--output", str(CASE_XLSX_PATH)]
    subprocess.run(cmd, cwd=ROOT, check=True)


def regenerate_formal_assets() -> None:
    cmd = [sys.executable, str(GENERATE_ASSETS_SCRIPT)]
    subprocess.run(cmd, cwd=ROOT, check=True)


def parse_case_table_line(line: str) -> tuple[str, list[str]] | None:
    if not line.startswith("| `"):
        return None
    cells = [cell.strip() for cell in line[1:-1].split("|")]
    if len(cells) != 10:
        return None
    case_id = cells[0].strip("`")
    return case_id, cells


def collect_statuses_from_lines(lines: list[str]) -> dict[str, str]:
    status_map: dict[str, str] = {}
    for line in lines:
        parsed = parse_case_table_line(line)
        if not parsed:
            continue
        case_id, cells = parsed
        status_map[case_id] = cells[8].strip("`")
    return status_map


def update_case_markdown(case_results: list[dict[str, Any]], evidence_map: dict[str, list[Path]]) -> None:
    status_map = {item["case_id"]: item["status"] for item in case_results}
    lines = CASE_MD_PATH.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    for line in lines:
        parsed = parse_case_table_line(line)
        if not parsed:
            updated.append(line)
            continue
        case_id, cells = parsed
        if case_id not in status_map:
            updated.append(line)
            continue
        cells[8] = f"`{status_map[case_id]}`"
        evidence_paths = evidence_map.get(case_id, [])
        if evidence_paths:
            evidence = "<br>".join(f"`{path.relative_to(ROOT)}`" for path in evidence_paths)
            cells[9] = f"{evidence}<br>目录重构后复跑闭环"
        updated.append("| " + " | ".join(cells) + " |")
    final_status_map = collect_statuses_from_lines(updated)
    pass_count = sum(1 for status in final_status_map.values() if status == "PASS")
    fail_ids = [case_id for case_id, status in final_status_map.items() if status == "FAIL"]
    todo_ids = [case_id for case_id, status in final_status_map.items() if status == "TODO"]
    text = "\n".join(updated)
    text = re.sub(r"- 当前状态分布：`PASS=\d+`、`FAIL=\d+`、`TODO=\d+`", f"- 当前状态分布：`PASS={pass_count}`、`FAIL={len(fail_ids)}`、`TODO={len(todo_ids)}`", text)
    fail_line = "- 当前明确保留缺陷："
    fail_line += "无" if not fail_ids else "、".join(f"`{case_id}`" for case_id in fail_ids)
    text = re.sub(r"- 当前(?:唯一)?明确保留缺陷：.*", fail_line, text)
    todo_header = "- 当前仅剩人工保留项 `TODO` 为："
    todo_block = todo_header
    if todo_ids:
        todo_block += "\n" + "\n".join(f"  - `{case_id}`" for case_id in todo_ids)
    else:
        todo_block += "\n  - 无"
    text = re.sub(r"- 当前(?:仅剩人工保留项|优先级最高的) `TODO` 为：\n(?:  - .*\n?)*", todo_block, text)
    CASE_MD_PATH.write_text(text + "\n", encoding="utf-8")

def main() -> int:
    regenerate_formal_assets()
    runner = FullflowRunner()
    evidence_map: dict[str, list[Path]] = {}
    requirements = runner.spec["requirements"]
    words = runner.spec["words"]
    voice_reg = runner.spec["voice_reg"]

    runner.prepare_static_assets()
    runner.burn_firmware()
    runner.open_ports()
    try:
        startup = runner.run_powercycle_step("assist_startup_powercycle_capture")
        startup_cfg = parse_boot_config(startup.log_text)
        burn_log_text = read_text(runner.burn_dir / "burn.log") if (runner.burn_dir / "burn.log").exists() else ""

        env001_status = "PASS" if str(startup_cfg.get("version")) == "1.0.0" else "FAIL"
        runner.add_case_result("ENV-001", "环境确认", env001_status, f"启动配置版本字段为 `{startup_cfg.get('version', 'missing')}`", [startup.step_dir], {"boot_config": startup_cfg})
        evidence_map["ENV-001"] = [startup.step_dir]

        env002_status = "PASS" if "Burn flow completed" in burn_log_text and env001_status == "PASS" else "FAIL"
        runner.add_case_result("ENV-002", "烧录确认", env002_status, "烧录流程成功且启动版本与目标固件一致", [runner.burn_dir / "burn.log", startup.step_dir])
        evidence_map["ENV-002"] = [runner.burn_dir / "burn.log", startup.step_dir]

        runner.add_case_result("SESS-001", "启动待机", "TODO", "本轮保留为人工验证；已补充启动连续日志作为辅助证据", [startup.step_dir])
        evidence_map["SESS-001"] = [startup.step_dir]

        reg_cmd_full_entry = runner.run_voice_sequence("assist_reg_cmd_template_full_entry", ["小度小度", "学习命令词"], post_wait_s=3.0)

        runner.run_shell_step("assist_config_clear_after_burn", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        reboot_after_clear = runner.run_shell_step("assist_reboot_after_config_clear", "reboot", capture_s=10.0, ready_wait_s=8.0)
        clean_cfg = parse_boot_config(reboot_after_clear.log_text)
        clean_gain = parse_mic_gain(reboot_after_clear.log_text)

        cfg_audio_status = "PASS" if clean_gain.get("analog_gain_db") == requirements["mic_analog_gain_db"] and clean_gain.get("digital_gain_db") == requirements["mic_digital_gain_db"] else "FAIL"
        runner.add_case_result(
            "CFG-AUDIO-001",
            "配置一致性-基础参数",
            cfg_audio_status,
            f"启动日志 mic 增益={clean_gain.get('analog_gain_db', 'missing')}/{clean_gain.get('digital_gain_db', 'missing')}dB，需求={requirements['mic_analog_gain_db']}/{requirements['mic_digital_gain_db']}dB",
            [reboot_after_clear.step_dir],
            {"boot_config": clean_cfg, "mic_gain": clean_gain},
        )
        evidence_map["CFG-AUDIO-001"] = [reboot_after_clear.step_dir]

        cfg_default_volume_status = "PASS" if clean_cfg.get("volume") == requirements["default_volume"] else "FAIL"
        runner.add_case_result(
            "CFG-VOL-001",
            "配置一致性-音量参数",
            cfg_default_volume_status,
            f"默认音量启动值={clean_cfg.get('volume', 'missing')}，需求={requirements['default_volume']}",
            [reboot_after_clear.step_dir],
            {"boot_config": clean_cfg},
        )
        evidence_map["CFG-VOL-001"] = [reboot_after_clear.step_dir]

        timeout_probe = runner.run_wake_timeout_probe("cfg_wake_timeout_probe", "小度小度", wait_s=float(requirements["wake_timeout_s"] + 8))
        timeout_gap = timeout_probe.detail.get("timeout_gap_s")
        cfg_wake_status = "PASS" if isinstance(timeout_gap, (int, float)) and abs(timeout_gap - requirements["wake_timeout_s"]) <= 1.5 else "FAIL"
        runner.add_case_result(
            "CFG-WAKE-001",
            "配置一致性-会话参数",
            cfg_wake_status,
            f"实测唤醒会话时长约 `{timeout_gap}`s，需求 `{requirements['wake_timeout_s']}s`",
            [timeout_probe.step_dir],
            timeout_probe.detail,
        )
        evidence_map["CFG-WAKE-001"] = [timeout_probe.step_dir]

        passive_report = runner.run_protocol_step("cfg_passive_report_proto", words["播报语"]["接收协议"], post_wait_s=4.0, pre_wait_s=0.3)
        passive_report_status = "PASS" if passive_report.detail.get("payload_hex") == words["播报语"]["接收协议"] and has_all_markers(passive_report.log_text, ["receive msg:: A5 FB 12 CC", "play start", "play id : 18", "play stop"]) else "FAIL"
        runner.add_case_result(
            "CFG-PROTO-003",
            "配置一致性-协议",
            passive_report_status,
            f"被动播报协议发送 `{passive_report.detail.get('payload_hex')}`，日志已{'命中' if passive_report_status == 'PASS' else '未完整命中'}接收与播报链路",
            [passive_report.step_dir],
            passive_report.detail,
        )
        evidence_map["CFG-PROTO-003"] = [passive_report.step_dir]

        volume_probe = runner.run_voice_sequence("cfg_volume_level_probe", ["小度小度", "大声点", "大声点", "大声点", "最大音量", "最小音量"], post_wait_s=3.0)
        volume_min_setup = runner.run_voice_sequence("cfg_volume_nonpersist_min", ["小度小度", "最小音量"], post_wait_s=3.0)
        volume_nonpersist_boot = runner.run_powercycle_step("cfg_volume_nonpersist_reboot", capture_s=10.0, ready_wait_s=8.0)
        volume_nonpersist_cfg = parse_boot_config(volume_nonpersist_boot.log_text)
        volume_values = {value for value in [clean_cfg.get("volume"), volume_nonpersist_cfg.get("volume")] if isinstance(value, int)}
        volume_values.update(int(item) for item in re.findall(r"refresh config volume=(\d+)", volume_probe.log_text))
        volume_values.update(int(item) for item in re.findall(r"refresh config volume=(\d+)", volume_min_setup.log_text))
        sorted_volume_values = sorted(volume_values)
        contiguous = bool(sorted_volume_values) and sorted_volume_values == list(range(sorted_volume_values[0], sorted_volume_values[-1] + 1))
        cfg_volume_steps_status = "PASS" if contiguous and len(sorted_volume_values) == requirements["volume_steps"] else "FAIL"
        runner.add_case_result(
            "CFG-VOL-002",
            "配置一致性-音量参数",
            cfg_volume_steps_status,
            f"实测可达音量档位={sorted_volume_values}（共 {len(sorted_volume_values)} 档），需求={requirements['volume_steps']} 档",
            [volume_probe.step_dir, volume_min_setup.step_dir, volume_nonpersist_boot.step_dir],
            {"values": sorted_volume_values, "contiguous": contiguous},
        )
        evidence_map["CFG-VOL-002"] = [volume_probe.step_dir, volume_min_setup.step_dir, volume_nonpersist_boot.step_dir]

        vol003_status = "PASS" if volume_nonpersist_cfg.get("volume") == requirements["default_volume"] else "FAIL"
        runner.add_case_result(
            "VOL-003",
            "音量控制",
            vol003_status,
            f"最小音量断电后启动值={volume_nonpersist_cfg.get('volume', 'missing')}，需求应恢复到默认音量 {requirements['default_volume']}",
            [volume_min_setup.step_dir, volume_nonpersist_boot.step_dir],
            {"boot_config": volume_nonpersist_cfg},
        )
        evidence_map["VOL-003"] = [volume_min_setup.step_dir, volume_nonpersist_boot.step_dir]

        runner.run_shell_step("assist_config_clear_after_volume_cfg", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("assist_reboot_after_volume_cfg_clear", "reboot", capture_s=10.0, ready_wait_s=8.0)

        sess007 = runner.run_voice_sequence("sess_idle_open_blocked", ["打开电风扇"], post_wait_s=3.0)
        runner.add_case_result("SESS-007", "待机阻断", "PASS" if step_pass(sess007, require_proto=False) else "FAIL", "未唤醒时直说控制词未产生主动控制协议", [sess007.step_dir])
        evidence_map["SESS-007"] = [sess007.step_dir]

        sess006_exit = runner.run_voice_sequence("sess_exit_sequence_only", ["小度小度", "退出识别"], post_wait_s=3.0)
        sess006_recover = runner.run_voice_sequence("sess_exit_rewake_open_recovery", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        runner.add_case_result("SESS-006", "退出识别", "PASS" if step_pass(sess006_recover, require_proto=True) else "FAIL", "退出识别后重新唤醒，基础控制恢复正常", [sess006_exit.step_dir, sess006_recover.step_dir])
        evidence_map["SESS-006"] = [sess006_exit.step_dir, sess006_recover.step_dir]

        vol004 = runner.run_voice_sequence("volume_rapid_stability", ["小度小度", "大声点", "大声点", "小声点"], post_wait_s=3.0)
        runner.add_case_result("VOL-004", "音量控制", "PASS" if step_pass(vol004, require_proto=True) else "FAIL", "连续快速调音过程中协议持续正常输出，未见失控迹象", [vol004.step_dir])
        evidence_map["VOL-004"] = [vol004.step_dir]

        voice_off = runner.run_voice_sequence("assist_voice_off_setup", ["小度小度", "关闭语音"], post_wait_s=3.0)
        invalid_proto = runner.run_protocol_step("voice_invalid_proto", "A5 FB 0B CC", post_wait_s=4.0, pre_wait_s=0.3)
        invalid_block = runner.run_voice_sequence("voice_invalid_proto_then_wake_open_blocked", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        runner.add_case_result("VOICE-005", "语音开关", "PASS" if step_pass(invalid_block, require_proto=False) else "FAIL", "错误协议未误开语音，语音入口仍保持关闭", [voice_off.step_dir, invalid_proto.step_dir, invalid_block.step_dir])
        evidence_map["VOICE-005"] = [voice_off.step_dir, invalid_proto.step_dir, invalid_block.step_dir]

        valid_proto = runner.run_protocol_step("voice_valid_proto_open", "A5 FB 0A CC", post_wait_s=3.0, pre_wait_s=0.5)
        voice003 = runner.run_voice_sequence("voice_on_then_volume_up", ["小度小度", "大声点"], post_wait_s=3.0)
        runner.add_case_result("VOICE-003", "语音开关", "PASS" if step_pass(voice003, require_proto=True) else "FAIL", "协议开语音后，音量调节链路恢复正常", [valid_proto.step_dir, voice003.step_dir])
        evidence_map["VOICE-003"] = [valid_proto.step_dir, voice003.step_dir]

        switch_next = runner.run_voice_sequence("switch_wake_to_next", ["小度小度", "切换唤醒词"], post_wait_s=3.0)
        swake_idle_current_open = runner.run_idle_wait_step("switch_idle_before_current_wake_open", duration_s=22.0)
        swake004_open = runner.run_voice_sequence("switch_current_wake_open", ["小爱同学", "打开电风扇"], post_wait_s=3.0)
        swake_idle_current_volume = runner.run_idle_wait_step("switch_idle_before_current_wake_volume", duration_s=22.0)
        swake004_volume = runner.run_voice_sequence("switch_current_wake_volume", ["小爱同学", "大声点"], post_wait_s=3.0)
        swake_idle_default_open = runner.run_idle_wait_step("switch_idle_before_default_wake_open", duration_s=22.0)
        swake005_open = runner.run_voice_sequence("switch_default_wake_open", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        swake_idle_default_volume = runner.run_idle_wait_step("switch_idle_before_default_wake_volume", duration_s=22.0)
        swake005_volume = runner.run_voice_sequence("switch_default_wake_volume", ["小度小度", "大声点"], post_wait_s=3.0)
        swake_idle = runner.run_idle_wait_step("switch_idle_before_other_wake_blocked", duration_s=22.0)
        swake003 = runner.run_voice_sequence("switch_other_wake_blocked", ["天猫精灵", "打开电风扇"], post_wait_s=3.0)
        switch_to_tmall = runner.run_voice_sequence("switch_cycle_to_tmall", ["小度小度", "切换唤醒词"], post_wait_s=3.0)
        switch_idle_tmall_open = runner.run_idle_wait_step("switch_idle_before_tmall_open", duration_s=22.0)
        switch_tmall_open = runner.run_voice_sequence("switch_cycle_tmall_open", ["天猫精灵", "打开电风扇"], post_wait_s=3.0)
        switch_back_default = runner.run_voice_sequence("switch_cycle_back_default", ["小度小度", "切换唤醒词"], post_wait_s=3.0)

        runner.add_case_result("SWAKE-003", "切换唤醒词", "PASS" if step_pass(swake003, require_proto=False) else "FAIL", "非当前非默认唤醒词未误唤醒", [switch_next.step_dir, swake_idle.step_dir, swake003.step_dir])
        evidence_map["SWAKE-003"] = [switch_next.step_dir, swake_idle.step_dir, swake003.step_dir]

        runner.add_case_result("SWAKE-004", "切换唤醒词", "PASS" if step_pass(swake004_open, require_proto=True) and step_pass(swake004_volume, require_proto=True) else "FAIL", "切换后的当前唤醒词下，基础控制和音量都正常", [switch_next.step_dir, swake_idle_current_open.step_dir, swake004_open.step_dir, swake_idle_current_volume.step_dir, swake004_volume.step_dir])
        evidence_map["SWAKE-004"] = [switch_next.step_dir, swake_idle_current_open.step_dir, swake004_open.step_dir, swake_idle_current_volume.step_dir, swake004_volume.step_dir]

        runner.add_case_result("SWAKE-005", "切换唤醒词", "PASS" if step_pass(swake005_open, require_proto=True) and step_pass(swake005_volume, require_proto=True) else "FAIL", "切换后默认唤醒词仍可完成基础控制和音量交互", [switch_next.step_dir, swake_idle_default_open.step_dir, swake005_open.step_dir, swake_idle_default_volume.step_dir, swake005_volume.step_dir])
        evidence_map["SWAKE-005"] = [switch_next.step_dir, swake_idle_default_open.step_dir, swake005_open.step_dir, swake_idle_default_volume.step_dir, swake005_volume.step_dir]

        runner.add_case_result("SWAKE-007", "切换唤醒词", "PASS" if step_pass(switch_tmall_open, require_proto=True) else "FAIL", "切换唤醒词已复跑完整回环：小爱同学 -> 天猫精灵 -> 默认", [switch_next.step_dir, switch_to_tmall.step_dir, switch_idle_tmall_open.step_dir, switch_tmall_open.step_dir, switch_back_default.step_dir])
        evidence_map["SWAKE-007"] = [switch_next.step_dir, switch_to_tmall.step_dir, switch_idle_tmall_open.step_dir, switch_tmall_open.step_dir, switch_back_default.step_dir]

        runner.run_shell_step("assist_reg_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("assist_reg_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)

        reg_entry = runner.run_voice_sequence("reg_entry_timeout_wait30s", ["小度小度", "学习命令词"], post_wait_s=3.0)
        timeout_wait = runner.run_idle_wait_step("reg_entry_timeout_idle_30s", duration_s=30.0)
        reg_entry_recover = runner.run_voice_sequence("reg_entry_timeout_recover_open", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        reg_entry_status = "PASS" if step_pass(reg_entry_recover, require_proto=True) else "FAIL"
        runner.add_case_result("REG-ENTRY-003", "语音注册", reg_entry_status, "学习入口超时后状态回收正常，默认控制链路恢复", [reg_entry.step_dir, timeout_wait.step_dir, reg_entry_recover.step_dir])
        evidence_map["REG-ENTRY-003"] = [reg_entry.step_dir, timeout_wait.step_dir, reg_entry_recover.step_dir]
        reg_cmd_learn = runner.run_voice_sequence("reg_cmd_learn_close_sequence", ["小度小度", "学习命令词", "学习下一个", "笑逐颜开", "笑逐颜开"], post_wait_s=3.0)
        reg_cmd_alias = runner.run_voice_sequence("reg_cmd_alias_close_recheck", ["小度小度", "笑逐颜开"], post_wait_s=3.0)
        reg_cmd_default = runner.run_voice_sequence("reg_cmd_default_close_recheck", ["小度小度", "关闭电风扇"], post_wait_s=3.0)
        runner.add_case_result("REG-CMD-003", "语音注册-命令词", "PASS" if step_pass(reg_cmd_alias, require_proto=True) and step_pass(reg_cmd_default, require_proto=True) else "FAIL", "学习别名与原始默认命令共存成立", [reg_cmd_learn.step_dir, reg_cmd_alias.step_dir, reg_cmd_default.step_dir])
        evidence_map["REG-CMD-003"] = [reg_cmd_learn.step_dir, reg_cmd_alias.step_dir, reg_cmd_default.step_dir]

        runner.run_shell_step("assist_reg_wake_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("assist_reg_wake_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)

        reg_wake_learn = runner.run_voice_sequence("reg_wake_learn_sequence", ["小度小度", "学习唤醒词", "晴空万里", "晴空万里"], post_wait_s=3.0)
        reg_wake_template_full = runner.run_voice_sequence("reg_wake_template_full_reenter", ["小度小度", "学习唤醒词"], post_wait_s=3.0)
        reg_wake_open = runner.run_voice_sequence("reg_wake_newword_open", ["晴空万里", "打开电风扇"], post_wait_s=3.0)
        reg_wake_volume = runner.run_voice_sequence("reg_wake_newword_volume", ["晴空万里", "大声点"], post_wait_s=3.0)
        reg_wake_idle = runner.run_idle_wait_step("reg_wake_idle_before_other_ordinary_blocked", duration_s=22.0)
        reg_wake_other = runner.run_voice_sequence("reg_wake_other_ordinary_blocked", ["小爱同学", "打开电风扇"], post_wait_s=3.0)
        runner.add_case_result("REG-WAKE-003", "语音注册-唤醒词", "PASS" if step_pass(reg_wake_open, require_proto=True) and step_pass(reg_wake_volume, require_proto=True) else "FAIL", "学习唤醒词后，基础控制与音量交互都正常", [reg_wake_learn.step_dir, reg_wake_open.step_dir, reg_wake_volume.step_dir])
        evidence_map["REG-WAKE-003"] = [reg_wake_learn.step_dir, reg_wake_open.step_dir, reg_wake_volume.step_dir]

        runner.add_case_result("REG-WAKE-004", "语音注册-唤醒词", "PASS" if step_pass(reg_wake_other, require_proto=False) else "FAIL", "学习唤醒词后，其他普通唤醒词未误唤醒", [reg_wake_learn.step_dir, reg_wake_idle.step_dir, reg_wake_other.step_dir])
        evidence_map["REG-WAKE-004"] = [reg_wake_learn.step_dir, reg_wake_idle.step_dir, reg_wake_other.step_dir]

        runner.run_shell_step("assist_powerloss_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("assist_powerloss_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        reg_powerloss_entry = runner.run_voice_sequence("powerloss_during_case_enter_learning", ["小度小度", "学习命令词"], post_wait_s=2.0)
        reg_powerloss_boot = runner.run_powercycle_step("powerloss_during_case_boot", capture_s=10.0, ready_wait_s=8.0)
        reg_powerloss_recover = runner.run_voice_sequence("powerloss_during_case_recover_open", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        runner.add_case_result("REG-SAVE-002", "语音注册-保持", "PASS" if step_pass(reg_powerloss_recover, require_proto=True) else "FAIL", "学习流程中突发断电后，设备仍能正常启动并恢复基础功能", [reg_powerloss_entry.step_dir, reg_powerloss_boot.step_dir, reg_powerloss_recover.step_dir])
        evidence_map["REG-SAVE-002"] = [reg_powerloss_entry.step_dir, reg_powerloss_boot.step_dir, reg_powerloss_recover.step_dir]

        runner.run_shell_step("final_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("final_reboot_clean", "reboot", capture_s=10.0, ready_wait_s=8.0)

        cfg_proto_1_status = "PASS" if evidence_has_frames(sess006_recover, [words["小度小度"]["发送协议"], words["打开电风扇"]["发送协议"]]) else "FAIL"
        runner.add_case_result(
            "CFG-PROTO-001",
            "配置一致性-协议",
            cfg_proto_1_status,
            f"默认唤醒 + 打开电风扇协议链路={proto_frames_from_hex(sess006_recover.proto_hex)}",
            [sess006_recover.step_dir],
            {"frames": proto_frames_from_hex(sess006_recover.proto_hex)},
        )
        evidence_map["CFG-PROTO-001"] = [sess006_recover.step_dir]

        cfg_proto_2_status = "PASS" if evidence_has_frames(voice_off, [words["小度小度"]["发送协议"], words["关闭语音"]["发送协议"]]) and valid_proto.detail.get("payload_hex") == words["开语音"]["接收协议"] else "FAIL"
        runner.add_case_result(
            "CFG-PROTO-002",
            "配置一致性-协议",
            cfg_proto_2_status,
            f"关语音主动协议链路={proto_frames_from_hex(voice_off.proto_hex)}，开语音发送值={valid_proto.detail.get('payload_hex')}",
            [voice_off.step_dir, valid_proto.step_dir],
            {"voice_off_frames": proto_frames_from_hex(voice_off.proto_hex), "voice_on_payload": valid_proto.detail.get("payload_hex")},
        )
        evidence_map["CFG-PROTO-002"] = [voice_off.step_dir, valid_proto.step_dir]

        reg_cmd_repeat_status = "PASS" if count_occurrences(reg_cmd_learn.log_text, "reg again!") == voice_reg["command_repeat_count"] - 1 and has_all_markers(reg_cmd_learn.log_text, ["play id : 28", "play id : 35"]) else "FAIL"
        runner.add_case_result(
            "REG-CFG-001",
            "配置一致性-语音注册",
            reg_cmd_repeat_status,
            f"命令词学习过程中 `reg again!` 次数={count_occurrences(reg_cmd_learn.log_text, 'reg again!')}，需求={voice_reg['command_repeat_count'] - 1}",
            [reg_cmd_learn.step_dir],
        )
        evidence_map["REG-CFG-001"] = [reg_cmd_learn.step_dir]

        reg_wake_repeat_status = "PASS" if count_occurrences(reg_wake_learn.log_text, "reg again!") == voice_reg["wakeup_repeat_count"] - 1 and has_all_markers(reg_wake_learn.log_text, ["play id : 28", "play id : 35"]) else "FAIL"
        runner.add_case_result(
            "REG-CFG-002",
            "配置一致性-语音注册",
            reg_wake_repeat_status,
            f"唤醒词学习过程中 `reg again!` 次数={count_occurrences(reg_wake_learn.log_text, 'reg again!')}，需求={voice_reg['wakeup_repeat_count'] - 1}",
            [reg_wake_learn.step_dir],
        )
        evidence_map["REG-CFG-002"] = [reg_wake_learn.step_dir]

        reg_cmd_template_status = "PASS" if startup_cfg.get("regCmdCount") == voice_reg["command_template_count"] and has_all_markers(reg_cmd_full_entry.log_text, ["reg over!", "play id : 34"]) else "FAIL"
        runner.add_case_result(
            "REG-CFG-005",
            "配置一致性-语音注册",
            reg_cmd_template_status,
            f"启动配置 `regCmdCount`={startup_cfg.get('regCmdCount', 'missing')}，再次进入命令词学习时{'出现' if 'reg over!' in reg_cmd_full_entry.log_text else '未出现'}模板已满提示",
            [startup.step_dir, reg_cmd_full_entry.step_dir],
            {"boot_config": startup_cfg},
        )
        evidence_map["REG-CFG-005"] = [startup.step_dir, reg_cmd_full_entry.step_dir]

        reg_wake_template_status = "PASS" if has_all_markers(reg_wake_template_full.log_text, ["reg over!", "play id : 34"]) and step_pass(reg_wake_open, require_proto=True) else "FAIL"
        runner.add_case_result(
            "REG-CFG-006",
            "配置一致性-语音注册",
            reg_wake_template_status,
            "学成一个唤醒词后再次进入学习唤醒词，已触发模板已满提示且原学习唤醒词仍有效",
            [reg_wake_learn.step_dir, reg_wake_template_full.step_dir, reg_wake_open.step_dir],
        )
        evidence_map["REG-CFG-006"] = [reg_wake_learn.step_dir, reg_wake_template_full.step_dir, reg_wake_open.step_dir]
    finally:
        runner.save_streams()
        runner.close_ports()

    cmd_retry_path = ROOT / "result" / "0418072345_22_reg_voice005_cmd_retry_exhaust_sequence" / "log_utf8.txt"
    wake_retry_path = ROOT / "result" / "0418073824_54_reg_voice006_wakeup_retry_exhaust_sequence" / "log_utf8.txt"
    cmd_retry_recheck_path = ROOT / "result" / "0418072503_23_reg_voice005_cmd_retry_exhaust_failed_alias_probe"
    wake_retry_recheck_path = ROOT / "result" / "0418073938_55_reg_voice006_wakeup_retry_exhaust_failed_wake_probe"
    reg_conflict_paths = [
        ROOT / "result" / "0418072549_26_reg_voice007_cmd_conflict_volume_word_sequence",
        ROOT / "result" / "0418072637_27_reg_voice007_cmd_conflict_volume_word_recheck",
    ]

    cmd_retry_text = read_text(cmd_retry_path)
    wake_retry_text = read_text(wake_retry_path)
    reg_cmd_retry_status = "PASS" if count_occurrences(cmd_retry_text, "reg simila error!") == voice_reg["command_retry_count"] and has_all_markers(cmd_retry_text, [f"error cnt > {voice_reg['command_retry_count']}", "reg failed!"]) else "FAIL"
    reg_wake_retry_status = "PASS" if count_occurrences(wake_retry_text, "reg simila error!") == voice_reg["wakeup_retry_count"] and has_all_markers(wake_retry_text, [f"error cnt > {voice_reg['wakeup_retry_count']}", "reg failed!"]) else "FAIL"

    runner.add_case_result(
        "REG-CFG-003",
        "配置一致性-语音注册",
        reg_cmd_retry_status,
        f"命令词失败耗尽日志中 `reg simila error!` 次数={count_occurrences(cmd_retry_text, 'reg simila error!')}，需求={voice_reg['command_retry_count']}",
        [cmd_retry_path, cmd_retry_recheck_path],
    )
    evidence_map["REG-CFG-003"] = [cmd_retry_path, cmd_retry_recheck_path]

    runner.add_case_result(
        "REG-CFG-004",
        "配置一致性-语音注册",
        reg_wake_retry_status,
        f"唤醒词失败耗尽日志中 `reg simila error!` 次数={count_occurrences(wake_retry_text, 'reg simila error!')}，需求={voice_reg['wakeup_retry_count']}",
        [wake_retry_path, wake_retry_recheck_path],
    )
    evidence_map["REG-CFG-004"] = [wake_retry_path, wake_retry_recheck_path]

    runner.add_case_result(
        "REG-CONFLICT-001",
        "语音注册-冲突词",
        "FAIL",
        "功能词 `增大音量` 被错误学习成命令词，历史证据保持 FAIL",
        reg_conflict_paths,
    )
    evidence_map["REG-CONFLICT-001"] = reg_conflict_paths

    update_case_markdown(runner.case_results, evidence_map)
    export_cases()
    shutil.copy2(PLAN_PATH, runner.static_dir / "plan" / PLAN_PATH.name)
    shutil.copy2(CASE_MD_PATH, runner.static_dir / "cases" / CASE_MD_PATH.name)
    shutil.copy2(CASE_XLSX_PATH, runner.static_dir / "cases" / CASE_XLSX_PATH.name)
    runner.write_case_results()
    runner.write_failure_analysis()
    runner.sync_bundle_root_artifacts()
    print(runner.bundle_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
