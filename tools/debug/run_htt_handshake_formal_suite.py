#!/usr/bin/env python
import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
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

DEVICE_KEY = "VID_8765&PID_5678:8_804B35B_1_0000"
CTRL_PORT = "COM39"
LOG_PORT = "COM38"
PROTO_PORT = "COM36"
CTRL_BAUD = 115200
LOG_BAUD = 115200
PROTO_BAUD = 9600
BOOT_READY_WAIT_S = 6.0
BETWEEN_TEXT_WAIT_S = 1.6


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


BASELINE_RESET_WORD = 0x006C
BASELINE_RESET_AT_S = 6.0
BASELINE_READY_WAIT_S = 33.0
POST_PLAY_GUARD_S = 8.0


@dataclass
class CaseDef:
    case_id: str
    title: str
    category: str
    objective: str
    texts: list[str] = field(default_factory=list)
    expected_words: list[int] = field(default_factory=list)
    forbidden_words: list[int] = field(default_factory=list)
    max_word_counts: dict[int, int] = field(default_factory=dict)
    timed_sends: list[tuple[float, str]] = field(default_factory=list)
    expected_log_markers: list[str] = field(default_factory=list)
    forbidden_log_markers: list[str] = field(default_factory=list)
    min_log_marker_counts: dict[str, int] = field(default_factory=dict)
    max_log_marker_counts: dict[str, int] = field(default_factory=dict)
    required_play_ids: list[int] = field(default_factory=list)
    forbidden_play_ids: list[int] = field(default_factory=list)
    extra_respond_rules: list[tuple[str, str]] = field(default_factory=list)
    capture_s: float = 28.0
    between_wait_s: float = BETWEEN_TEXT_WAIT_S
    gaps_s: list[float] = field(default_factory=list)
    initial_wait_s: float = BOOT_READY_WAIT_S
    notes: str = ""


CASES: list[CaseDef] = [
    CaseDef(
        case_id="ENV-BOOT-001",
        title="握手补齐后启动可进入 ready",
        category="环境/握手",
        objective="验证仿真 MCU 握手补齐后，启动日志不再报 MCU 未就绪。",
        expected_log_markers=[
            "version         :       1.0.9",
            "receive msg:: A5 FA 83 5A 5A D6 FB",
            "receive msg:: A5 FA 83 A5 A5 6C FB",
            "send msg:: A5 FA 7F A5 A5 68 FB",
        ],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=18.0,
        notes="仅上电观察，不播报语音。",
    ),
    CaseDef(
        case_id="SESS-WAKE-001",
        title="默认唤醒词生效",
        category="会话",
        objective="验证默认唤醒词“小好小好”可进入识别态并下发主动协议。",
        texts=["小好小好"],
        expected_words=[0x0001],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=24.0,
    ),
    CaseDef(
        case_id="CTRL-LIGHT-001",
        title="打开照明",
        category="灯光/场景",
        objective="验证“小好小好 -> 打开照明”可下发照明打开协议。",
        texts=["小好小好", "打开照明"],
        expected_words=[0x0001, 0x0009],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=30.0,
    ),
    CaseDef(
        case_id="CTRL-LIGHT-002",
        title="关闭照明",
        category="灯光/场景",
        objective="验证“小好小好 -> 关闭照明”可下发照明关闭协议。",
        texts=["小好小好", "关闭照明"],
        expected_words=[0x0001, 0x000A],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=30.0,
    ),
    CaseDef(
        case_id="CTRL-READ-001",
        title="打开阅读模式",
        category="灯光/场景",
        objective="验证“小好小好 -> 打开阅读模式”可下发阅读模式打开协议。",
        texts=["小好小好", "打开阅读模式"],
        expected_words=[0x0001, 0x0065],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=30.0,
    ),
    CaseDef(
        case_id="CTRL-READ-002",
        title="关闭阅读模式",
        category="灯光/场景",
        objective="验证“小好小好 -> 关闭阅读模式”可下发阅读模式关闭协议。",
        texts=["小好小好", "关闭阅读模式"],
        expected_words=[0x0001, 0x0069],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=30.0,
    ),
    CaseDef(
        case_id="NET-PAIR-001",
        title="开始配网",
        category="联网",
        objective="验证“小好小好 -> 开始配网”可下发配网协议。",
        texts=["小好小好", "开始配网"],
        expected_words=[0x0001, 0x0020],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=30.0,
    ),
    CaseDef(
        case_id="SESS-BLOCK-001",
        title="未唤醒直说命令阻断",
        category="会话",
        objective="验证未唤醒时直接说“打开照明”不会下发照明控制协议。",
        texts=["打开照明"],
        forbidden_words=[0x0001, 0x0009],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=22.0,
        notes="该用例以未出现主动控制协议为 PASS 判据。",
    ),
    CaseDef(
        case_id="VOL-UP-001",
        title="调大音量",
        category="音量",
        objective="验证“小好小好 -> 调大音量”可下发音量增大协议。",
        texts=["小好小好", "调大音量"],
        expected_words=[0x0001, 0x0041],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=28.0,
    ),
    CaseDef(
        case_id="VOL-DOWN-001",
        title="调小音量",
        category="音量",
        objective="验证“小好小好 -> 调小音量”可下发音量减小协议。",
        texts=["小好小好", "调小音量"],
        expected_words=[0x0001, 0x0042],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=28.0,
    ),
    CaseDef(
        case_id="VOL-MAX-001",
        title="最大音量",
        category="音量",
        objective="验证“小好小好 -> 最大音量”可下发最大音量协议。",
        texts=["小好小好", "最大音量"],
        expected_words=[0x0001, 0x0043],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=28.0,
    ),
    CaseDef(
        case_id="VOL-MIN-001",
        title="最小音量",
        category="音量",
        objective="验证“小好小好 -> 最小音量”可下发最小音量协议。",
        texts=["小好小好", "最小音量"],
        expected_words=[0x0001, 0x0044],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=28.0,
    ),
    CaseDef(
        case_id="REPORT-OFF-001",
        title="打开静音",
        category="播报开关",
        objective="验证“小好小好 -> 关闭播报功能”可下发播报关闭协议。",
        texts=["小好小好", "关闭播报功能"],
        expected_words=[0x0001, 0x0046],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=28.0,
    ),
    CaseDef(
        case_id="REPORT-ON-001",
        title="退出静音",
        category="播报开关",
        objective="验证“小好小好 -> 退出静音”可下发播报开启协议。",
        texts=["小好小好", "退出静音"],
        expected_words=[0x0001, 0x0045],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=28.0,
    ),
    CaseDef(
        case_id="VOICE-OFF-BLOCK-001",
        title="关闭语音后普通命令受限",
        category="语音开关",
        objective="验证在唤醒后关闭语音，模组进入受限交互状态，后续唤醒/普通命令都不再继续下发给 MCU。",
        texts=["小好小好", "语音功能关闭", "小好小好", "打开照明"],
        expected_words=[0x0001, 0x0016, 0x0001],
        forbidden_words=[0x0009],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=34.0,
        notes="PASS 条件：先产生 0x0001 + 0x0016；受限态下再次唤醒仍可被识别，但普通命令 0x0009 不能再下发。",
    ),
    CaseDef(
        case_id="VOICE-ON-RECOVER-001",
        title="关闭语音后重新打开并恢复命令",
        category="语音开关",
        objective="验证关闭语音后，在受限状态下说“语音功能打开”可恢复业务，再次唤醒后允许继续执行照明命令。",
        texts=["小好小好", "语音功能关闭", "语音功能打开", "小好小好", "打开照明"],
        expected_words=[0x0001, 0x0016, 0x0017, 0x0001, 0x0009],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=56.0,
        gaps_s=[1.6, 2.4, 4.0, 4.0],
    ),
    CaseDef(
        case_id="SESS-TIMEOUT-001",
        title="超时回休眠后未重唤醒命令阻断",
        category="会话",
        objective="验证唤醒后经过一段长静默后，会话已回休眠，未重唤醒时业务命令不会继续下发。",
        texts=["小好小好", "打开照明"],
        expected_words=[0x0001],
        forbidden_words=[0x0009],
        forbidden_log_markers=["MCU is not ready!"],
        capture_s=46.0,
        gaps_s=[26.0],
        notes="本用例当前只验证“长静默后命令被阻断”的功能表现；真实超时值应单独测量“唤醒响应结束 -> TIME_OUT / MODE=0”再与需求 25s 比对，不能用 26s 等待窗口反推。",
    ),
    CaseDef(
        case_id="PASSIVE-RESET-001",
        title="被动0x006C恢复出厂",
        category="被动协议",
        objective="验证 MCU 被动下发 0x006C 后，模组执行恢复出厂并刷新默认配置。",
        timed_sends=[(6.0, passive_frame_hex(0x006C))],
        expected_log_markers=[
            f"receive msg:: {passive_frame_hex(0x006C)}",
            "restore factory response",
            "mini player set vol : 58",
            "refresh config volume=2 voice=1 wakeup=0 play_mode=0",
            "save config success",
        ],
        forbidden_log_markers=["MCU is not ready!"],
        required_play_ids=[103],
        min_log_marker_counts={"play id : ": 1},
        max_log_marker_counts={"play id : ": 1},
        capture_s=16.0,
        notes="当前只实测到恢复出厂后的日志值 `mini player set vol : 58` 和 `refresh config volume=2`；它们是否等价于需求“默认 3 档”，必须先建立真实档位映射后再判断，不能直接反推。",
    ),
    CaseDef(
        case_id="PASSIVE-REPORT-OFF-001",
        title="被动0x0082强制关闭播报",
        category="被动协议",
        objective="验证先恢复默认，再由 MCU 被动下发 0x0082 后，播报状态被强制关闭且不新增播报播放。",
        timed_sends=[
            (6.0, passive_frame_hex(0x006C)),
            (10.0, passive_frame_hex(0x0082)),
        ],
        expected_log_markers=[
            f"receive msg:: {passive_frame_hex(0x006C)}",
            f"receive msg:: {passive_frame_hex(0x0082)}",
            "restore factory response",
            "close play mode",
            "refresh config volume=2 voice=1 wakeup=0 play_mode=1",
            "save config success",
        ],
        forbidden_log_markers=["MCU is not ready!"],
        required_play_ids=[103],
        min_log_marker_counts={"play id : ": 1},
        max_log_marker_counts={"play id : ": 1},
        capture_s=18.0,
        notes="`play start` 只允许出现 1 次，用于确认仅恢复出厂提示播放，0x0082 本身不再额外播报。",
    ),
    CaseDef(
        case_id="PASSIVE-REPORT-ON-001",
        title="被动0x0069强制开启播报",
        category="被动协议",
        objective="验证先恢复默认并关闭播报，再由 MCU 被动下发 0x0069 后，播报状态被强制开启并触发播报。",
        timed_sends=[
            (6.0, passive_frame_hex(0x006C)),
            (10.0, passive_frame_hex(0x0082)),
            (14.0, passive_frame_hex(0x0069)),
        ],
        expected_log_markers=[
            f"receive msg:: {passive_frame_hex(0x006C)}",
            f"receive msg:: {passive_frame_hex(0x0082)}",
            f"receive msg:: {passive_frame_hex(0x0069)}",
            "restore factory response",
            "close play mode",
            "open play mode",
            "refresh config volume=2 voice=1 wakeup=0 play_mode=0",
            "save config success",
        ],
        forbidden_log_markers=["MCU is not ready!"],
        required_play_ids=[103, 100],
        min_log_marker_counts={"play id : ": 2},
        max_log_marker_counts={"play id : ": 2},
        capture_s=22.0,
        notes="`play start` 共应出现 2 次：一次来自 0x006C 恢复提示，一次来自 0x0069 强制开启播报提示。",
    ),
    CaseDef(
        case_id="PASSIVE-VOICE-ON-001",
        title="被动0x0012关闭语音后可恢复",
        category="被动协议",
        objective="验证先恢复默认，再由 MCU 被动下发 0x0012 关闭语音后，经再次唤醒并说“语音功能打开”可恢复业务并重新执行照明命令。",
        texts=["小好小好", "语音功能打开", "小好小好", "打开照明"],
        expected_words=[0x0001, 0x0017, 0x0001, 0x0009],
        timed_sends=[
            (6.0, passive_frame_hex(0x006C)),
            (10.0, passive_frame_hex(0x0012)),
        ],
        expected_log_markers=[
            f"receive msg:: {passive_frame_hex(0x006C)}",
            f"receive msg:: {passive_frame_hex(0x0012)}",
            "refresh config volume=2 voice=0 wakeup=0 play_mode=0",
            "save config success",
        ],
        forbidden_log_markers=["MCU is not ready!"],
        required_play_ids=[103, 65],
        capture_s=72.0,
        initial_wait_s=14.0,
        gaps_s=[2.0, 8.0, 6.0],
        notes="先用 0x006C 建立语音/播报默认态，再验证 0x0012 关闭语音后，需要先唤醒再说“语音功能打开”的恢复链路。",
    ),
    CaseDef(
        case_id="PASSIVE-VOICE-OFF-001",
        title="被动0x0012关闭语音后阻断业务",
        category="被动协议",
        objective="验证先恢复默认，再由 MCU 被动下发 0x0012 关闭语音后，后续普通照明命令不再继续下发给 MCU。",
        texts=["小好小好", "打开照明"],
        expected_words=[0x0001],
        forbidden_words=[0x0009],
        timed_sends=[
            (6.0, passive_frame_hex(0x006C)),
            (10.0, passive_frame_hex(0x0012)),
        ],
        expected_log_markers=[
            f"receive msg:: {passive_frame_hex(0x006C)}",
            f"receive msg:: {passive_frame_hex(0x0012)}",
            "refresh config volume=2 voice=0 wakeup=0 play_mode=0",
            "save config success",
        ],
        forbidden_log_markers=["MCU is not ready!"],
        required_play_ids=[103, 65],
        capture_s=42.0,
        initial_wait_s=14.0,
        gaps_s=[1.8],
        notes="当前固件受限态下仍会下发唤醒协议 0x0001，但业务协议 0x0009 应继续被阻断。",
    ),
]


def run_command(command: list[str]) -> tuple[int, list[str]]:
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed.returncode, completed.stdout.splitlines()


def parse_data_words(text: str) -> list[int]:
    values: list[int] = []
    for match in re.finditer(r"A5 FA 7F ([0-9A-F]{2}) ([0-9A-F]{2}) [0-9A-F]{2} FB", text):
        values.append((int(match.group(1), 16) << 8) | int(match.group(2), 16))
    return values


def parse_play_ids(text: str) -> list[int]:
    return [int(match.group(1)) for match in re.finditer(r"play id\s*:\s*(\d+)", text)]


def contains_in_order(items: list[int], expected: list[int]) -> bool:
    if not expected:
        return True
    index = 0
    for item in items:
        if item == expected[index]:
            index += 1
            if index >= len(expected):
                return True
    return False


def should_reset_case_baseline(case: CaseDef) -> bool:
    if case.case_id == "ENV-BOOT-001":
        return False
    baseline_reset_hex = passive_frame_hex(BASELINE_RESET_WORD)
    return all(payload_hex != baseline_reset_hex for _, payload_hex in case.timed_sends)


def has_factory_reset_during_case(case: CaseDef) -> bool:
    if should_reset_case_baseline(case):
        return True
    baseline_reset_hex = passive_frame_hex(BASELINE_RESET_WORD)
    return any(payload_hex == baseline_reset_hex for _, payload_hex in case.timed_sends)


def effective_initial_wait_s(case: CaseDef) -> float:
    if case.texts and has_factory_reset_during_case(case):
        return max(case.initial_wait_s, BASELINE_READY_WAIT_S)
    return case.initial_wait_s


def effective_capture_s(case: CaseDef) -> float:
    initial_wait_s = effective_initial_wait_s(case)
    tail_guard_s = POST_PLAY_GUARD_S if case.texts else 0.0
    return case.capture_s + max(0.0, initial_wait_s - case.initial_wait_s) + tail_guard_s


def build_handshake_cmd(case: CaseDef, result_dir: Path) -> list[str]:
    capture_s = effective_capture_s(case)
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
        "A5 FA 7F 01 02 21 FB=A5 FA 81 00 20 40 FB",
        "--respond",
        "A5 FA 7F 5A 5A D2 FB=A5 FA 83 5A 5A D6 FB",
        "--periodic",
        "A5 FA 83 A5 A5 6C FB@4.0",
    ]
    if should_reset_case_baseline(case):
        command.extend(["--inject-once", f"{passive_frame_hex(BASELINE_RESET_WORD)}@{BASELINE_RESET_AT_S}"])
    for match_hex, reply_hex in case.extra_respond_rules:
        command.extend(["--respond", f"{match_hex}={reply_hex}"])
    for at_s, payload_hex in case.timed_sends:
        command.extend(["--inject-once", f"{payload_hex}@{at_s}"])
    return command


def prepare_audio(text: str) -> Path:
    path, _ = ensure_cached_tts(text=text, voice="Microsoft Huihui Desktop", rate=0, label=f"htt_{text}")
    return path


def play_audio(play_script: Path, audio_file: Path, out_path: Path) -> dict[str, Any]:
    code, lines = run_command(
        [
            sys.executable,
            str(play_script),
            "play",
            "--audio-file",
            str(audio_file),
            "--device-key",
            DEVICE_KEY,
        ]
    )
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return {
        "command": "play",
        "audio_file": str(audio_file),
        "exit_code": code,
        "output": lines,
    }


def evaluate_case(case: CaseDef, case_dir: Path) -> dict[str, Any]:
    com36_text = (case_dir / "com36_frames.txt").read_text(encoding="utf-8", errors="replace")
    com38_text = (case_dir / "com38_utf8.txt").read_text(encoding="utf-8", errors="replace")
    words = parse_data_words(com36_text)
    play_ids = parse_play_ids(com38_text)
    expected_ok = contains_in_order(words, case.expected_words)
    required_play_ids_ok = contains_in_order(play_ids, case.required_play_ids)
    forbidden_word_hits = [f"0x{word:04X}" for word in case.forbidden_words if word in words]
    forbidden_play_id_hits = [str(play_id) for play_id in case.forbidden_play_ids if play_id in play_ids]
    over_limit_word_hits = [
        f"0x{word:04X}={words.count(word)}>{limit}"
        for word, limit in case.max_word_counts.items()
        if words.count(word) > limit
    ]
    expected_marker_hits = [marker for marker in case.expected_log_markers if marker in com38_text]
    missing_markers = [marker for marker in case.expected_log_markers if marker not in com38_text]
    forbidden_marker_hits = [marker for marker in case.forbidden_log_markers if marker in com38_text]
    min_count_failures = [
        f"{marker}={com38_text.count(marker)}<{limit}"
        for marker, limit in case.min_log_marker_counts.items()
        if com38_text.count(marker) < limit
    ]
    max_count_failures = [
        f"{marker}={com38_text.count(marker)}>{limit}"
        for marker, limit in case.max_log_marker_counts.items()
        if com38_text.count(marker) > limit
    ]

    passed = (
        expected_ok
        and required_play_ids_ok
        and not forbidden_word_hits
        and not forbidden_play_id_hits
        and not over_limit_word_hits
        and not missing_markers
        and not forbidden_marker_hits
        and not min_count_failures
        and not max_count_failures
    )
    status = "PASS" if passed else "FAIL"

    return {
        "case_id": case.case_id,
        "title": case.title,
        "status": status,
        "expected_words": [f"0x{word:04X}" for word in case.expected_words],
        "observed_words": [f"0x{word:04X}" for word in words],
        "expected_play_ids": case.required_play_ids,
        "observed_play_ids": play_ids,
        "forbidden_word_hits": forbidden_word_hits,
        "required_play_ids_missing": [] if required_play_ids_ok else [str(play_id) for play_id in case.required_play_ids],
        "forbidden_play_id_hits": forbidden_play_id_hits,
        "over_limit_word_hits": over_limit_word_hits,
        "expected_marker_hits": expected_marker_hits,
        "missing_markers": missing_markers,
        "forbidden_marker_hits": forbidden_marker_hits,
        "min_count_failures": min_count_failures,
        "max_count_failures": max_count_failures,
        "notes": case.notes,
    }


def run_case(case: CaseDef, suite_dir: Path, play_script: Path) -> dict[str, Any]:
    case_dir = suite_dir / "steps" / case.case_id.lower()
    case_dir.mkdir(parents=True, exist_ok=True)
    probe_stdout = case_dir / "probe_stdout.txt"
    probe_stderr = case_dir / "probe_stderr.txt"
    handshake_cmd = build_handshake_cmd(case, case_dir)
    initial_wait_s = effective_initial_wait_s(case)
    capture_s = effective_capture_s(case)

    with probe_stdout.open("w", encoding="utf-8") as stdout_handle, probe_stderr.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(handshake_cmd, stdout=stdout_handle, stderr=stderr_handle)
        playback_records: list[dict[str, Any]] = []
        try:
            time.sleep(initial_wait_s)
            for index, text in enumerate(case.texts):
                audio_file = prepare_audio(text)
                playback_records.append(
                    play_audio(
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

    record = {
        "case_id": case.case_id,
        "title": case.title,
        "category": case.category,
        "objective": case.objective,
        "texts": case.texts,
        "expected_words": [f"0x{word:04X}" for word in case.expected_words],
        "forbidden_words": [f"0x{word:04X}" for word in case.forbidden_words],
        "max_word_counts": {f"0x{word:04X}": limit for word, limit in case.max_word_counts.items()},
        "required_play_ids": case.required_play_ids,
        "forbidden_play_ids": case.forbidden_play_ids,
        "extra_respond_rules": [{"match_hex": match_hex, "reply_hex": reply_hex} for match_hex, reply_hex in case.extra_respond_rules],
        "timed_sends": [{"at_s": at_s, "payload_hex": payload_hex} for at_s, payload_hex in case.timed_sends],
        "capture_s": capture_s,
        "baseline_reset": should_reset_case_baseline(case),
        "initial_wait_s": initial_wait_s,
        "playback": playback_records,
        "result_dir": str(case_dir),
    }

    required_files = [
        case_dir / "com36_frames.txt",
        case_dir / "com38_utf8.txt",
        case_dir / "meta.json",
    ]
    missing = [str(path.name) for path in required_files if not path.exists()]
    if missing:
        record["status"] = "BLOCKED"
        record["reason"] = f"运行产物缺失: {', '.join(missing)}"
    else:
        record.update(evaluate_case(case, case_dir))

    (case_dir / "analysis.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(1.0)
    return record


def write_plan_md(path: Path, suite_name: str, result_dir: Path) -> None:
    lines = [
        "# 好太太晾衣机握手仿真正式测试方案",
        "",
        f"- 套件名称：`{suite_name}`",
        f"- 原始结果目录：`{result_dir}`",
        "- 口径说明：本轮通过协议口仿真 MCU 握手，不代表真实整机 MCU 已完成修复。",
        "- 固定端口：控制 `COM39`、日志 `COM38`、协议 `COM36`。",
        "- 仿真握手规则：",
        "  - 启动品牌查询 `A5 FA 7F 01 02 21 FB` -> 回 `A5 FA 81 00 20 40 FB`",
        "  - 模组心跳 `A5 FA 7F 5A 5A D2 FB` -> 回 `A5 FA 83 5A 5A D6 FB`",
        "  - MCU 探测每 4s 发送 `A5 FA 83 A5 A5 6C FB`，模组应回 `A5 FA 7F A5 A5 68 FB`",
        "- 本轮执行目标：验证握手补齐后，启动 ready、主动语音控制、会话阻断，以及 MCU 被动协议注入（恢复出厂 / 播报开关 / 语音关闭）等关键链路是否成立。",
        "- 数值验证口径修正：数值项统一采用“先测真实值，再与需求比对”；不能把需求值直接当等待窗口或判定条件。",
        "- 因此本轮 22 条里，`0x0082/0x0069` 的播报次数属于已按实测次数闭环；`25s` 超时、`1~5 档`、默认 `3 档`、语音关闭后 `10s` 受限窗口目前只做到功能层或观察层，还需专项数值探针。",
        "- 当前新增被动协议覆盖：`0x006C` 恢复出厂、`0x0082` 强制关闭播报、`0x0069` 强制开启播报、`0x0012` 被动关闭语音。",
        "- 本轮暂未覆盖：断电后持久化复核、更多被动播报全集、完整异常分支、长时稳定性。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_cases_md(path: Path) -> None:
    lines = [
        "# 好太太晾衣机握手仿真正式测试用例",
        "",
        "| 用例ID | 分类 | 标题 | 输入文本 | 期望主动协议 | 备注 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case in CASES:
        text_parts: list[str] = []
        if case.timed_sends:
            text_parts.extend(f"被动@{at_s:.1f}s {payload_hex}" for at_s, payload_hex in case.timed_sends)
        if case.texts:
            text_parts.extend(case.texts)
        texts = " / ".join(text_parts) if text_parts else "仅启动观察"
        expected = " / ".join(active_frame_hex(word) for word in case.expected_words) if case.expected_words else "无"
        note = case.notes or case.objective
        if case.required_play_ids:
            note = f"{note}；期望播报ID={','.join(str(play_id) for play_id in case.required_play_ids)}"
        lines.append(f"| `{case.case_id}` | {case.category} | {case.title} | {texts} | {expected} | {note} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_report_md(path: Path, suite_name: str, suite_dir: Path, results: list[dict[str, Any]]) -> None:
    pass_count = sum(1 for item in results if item["status"] == "PASS")
    fail_count = sum(1 for item in results if item["status"] == "FAIL")
    blocked_count = sum(1 for item in results if item["status"] == "BLOCKED")

    lines = [
        "# 好太太晾衣机握手仿真正式执行报告",
        "",
        f"- 套件名称：`{suite_name}`",
        f"- 原始结果目录：`{suite_dir}`",
        "- 结论口径：以下结果成立的前提是测试夹具已替代 MCU 补齐品牌与心跳握手，不能直接外推为真实整机已修复。",
        f"- 总计：`{len(results)}` 条；PASS=`{pass_count}`，FAIL=`{fail_count}`，BLOCKED=`{blocked_count}`",
        "",
        "## 明细",
        "",
    ]
    for item in results:
        lines.append(f"### {item['case_id']} {item['title']}")
        lines.append(f"- 结果：`{item['status']}`")
        lines.append(f"- 结果目录：`{item['result_dir']}`")
        if item.get("status") == "BLOCKED":
            lines.append(f"- 原因：{item.get('reason', '')}")
        else:
            lines.append(f"- 期望主动协议：{', '.join(item.get('expected_words', [])) or '无'}")
            lines.append(f"- 观测主动协议：{', '.join(item.get('observed_words', [])) or '无'}")
            if item.get("expected_play_ids"):
                lines.append(f"- 期望播报ID：{', '.join(str(play_id) for play_id in item['expected_play_ids'])}")
                lines.append(f"- 观测播报ID：{', '.join(str(play_id) for play_id in item.get('observed_play_ids', [])) or '无'}")
            if item.get("missing_markers"):
                lines.append(f"- 缺失日志标记：{', '.join(item['missing_markers'])}")
            if item.get("forbidden_word_hits"):
                lines.append(f"- 命中禁止协议：{', '.join(item['forbidden_word_hits'])}")
            if item.get("required_play_ids_missing"):
                lines.append(f"- 缺失播报ID：{', '.join(item['required_play_ids_missing'])}")
            if item.get("forbidden_play_id_hits"):
                lines.append(f"- 命中禁止播报ID：{', '.join(item['forbidden_play_id_hits'])}")
            if item.get("over_limit_word_hits"):
                lines.append(f"- 协议出现次数超限：{', '.join(item['over_limit_word_hits'])}")
            if item.get("forbidden_marker_hits"):
                lines.append(f"- 命中禁止日志：{', '.join(item['forbidden_marker_hits'])}")
            if item.get("min_count_failures"):
                lines.append(f"- 日志出现次数不足：{', '.join(item['min_count_failures'])}")
            if item.get("max_count_failures"):
                lines.append(f"- 日志出现次数超限：{', '.join(item['max_count_failures'])}")
        if item.get("notes"):
            lines.append(f"- 备注：{item['notes']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the HTT handshake-emulation formal suite.")
    parser.add_argument(
        "--case-id",
        dest="case_ids",
        action="append",
        help="Run only the specified case id. Repeat the flag to select multiple cases.",
    )
    parser.add_argument(
        "--suite-tag",
        default="",
        help="Optional suffix appended to the generated suite directory name.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected_cases = CASES
    if args.case_ids:
        wanted = {item.strip().upper() for item in args.case_ids if item.strip()}
        selected_cases = [case for case in CASES if case.case_id.upper() in wanted]
        missing = sorted(wanted - {case.case_id.upper() for case in selected_cases})
        if missing:
            raise SystemExit(f"Unknown case id(s): {', '.join(missing)}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_name = f"{timestamp}_htt_handshake_formal_suite"
    if args.suite_tag:
        suite_name = f"{suite_name}_{args.suite_tag}"
    suite_dir = RESULT_ROOT / suite_name
    suite_dir.mkdir(parents=True, exist_ok=True)

    play_script = resolve_listenai_play(update=False)
    results: list[dict[str, Any]] = []
    for case in selected_cases:
        results.append(run_case(case, suite_dir, play_script))

    summary = {
        "suite_name": suite_name,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "device_key": DEVICE_KEY,
        "ctrl_port": CTRL_PORT,
        "log_port": LOG_PORT,
        "proto_port": PROTO_PORT,
        "selected_case_ids": [case.case_id for case in selected_cases],
        "results": results,
    }
    (suite_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    DELIVERABLE_ROOT.mkdir(parents=True, exist_ok=True)
    (DELIVERABLE_ROOT / "plan").mkdir(parents=True, exist_ok=True)
    (DELIVERABLE_ROOT / "cases").mkdir(parents=True, exist_ok=True)
    (DELIVERABLE_ROOT / "reports").mkdir(parents=True, exist_ok=True)

    plan_path = DELIVERABLE_ROOT / "plan" / "20260422_握手仿真正式测试方案_v4.md"
    case_path = DELIVERABLE_ROOT / "cases" / "20260422_握手仿真正式测试用例_v4.md"
    report_dir = DELIVERABLE_ROOT / "reports" / suite_name
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "summary.md"

    write_plan_md(plan_path, suite_name, suite_dir)
    write_cases_md(case_path)
    write_report_md(report_path, suite_name, suite_dir, results)

    print(json.dumps({"suite_name": suite_name, "suite_dir": str(suite_dir), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
