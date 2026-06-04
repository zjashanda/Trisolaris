from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import serial
from behave import given, then, when

from environment import SerialCapture
from xiaodu_steps import audio_file, normalize_hex

CONTROL_FRAMES = {
    "A5 FA 04 BB",
    "A5 FA 05 BB",
    "A5 FA 06 BB",
    "A5 FA 07 BB",
    "A5 FA 11 BB",
    "A5 FA 13 BB",
    "A5 FA 14 BB",
    "A5 FA 15 BB",
    "A5 FA 16 BB",
    "A5 FA 17 BB",
}


def proto_frames(proto_text: str) -> list[str]:
    compact = re.sub(r"[^0-9A-Fa-f]", "", proto_text).upper()
    frames: list[str] = []
    for idx in range(0, max(len(compact) - 7, 0), 2):
        chunk = compact[idx : idx + 8]
        if len(chunk) == 8 and chunk.startswith("A5") and chunk.endswith("BB"):
            frames.append(" ".join(chunk[i : i + 2] for i in range(0, len(chunk), 2)))
        if len(chunk) == 8 and chunk.startswith("A5") and chunk.endswith("CC"):
            frames.append(" ".join(chunk[i : i + 2] for i in range(0, len(chunk), 2)))
    # Preserve order but remove accidental duplicates caused by sliding parse.
    deduped: list[str] = []
    for frame in frames:
        if not deduped or deduped[-1] != frame:
            deduped.append(frame)
    return deduped


def current_log(context) -> str:
    cap = context.current_capture.get("log")
    return cap.text if cap else ""


def current_proto(context) -> str:
    cap = context.current_capture.get("proto")
    return cap.text if cap else ""


def row_value(row, *names: str, default: str = "") -> str:
    data = row.as_dict()
    for name in names:
        value = data.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


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
        config[key] = int(value) if value.isdigit() else value
    return config


def parse_requirements(context) -> dict[str, int | str]:
    req_dir = Path(os.environ.get("TRISOLARIS_REQ_DIR", context.root / "项目需求" / "CSK5062小度风扇需求"))
    req_path = req_dir / "需求文档.md"
    text = req_path.read_text(encoding="utf-8")

    def expect_int(pattern: str) -> int:
        match = re.search(pattern, text)
        if not match:
            raise AssertionError(f"需求字段解析失败: {pattern} in {req_path}")
        return int(match.group(1))

    return {
        "req_path": str(req_path.relative_to(context.root)),
        "volume_steps": expect_int(r"音量档位:\s*(\d+)"),
        "default_volume": expect_int(r"初始化默认音量:\s*(\d+)"),
    }


def extract_runtime_volume_levels(log_text: str) -> list[int]:
    return [int(item) for item in re.findall(r"mini player set vol\s*:\s*(\d+)", log_text)]


def last_runtime_volume_level(log_text: str) -> int | None:
    values = extract_runtime_volume_levels(log_text)
    return values[-1] if values else None


def ordered_unique(values: list[int]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def log_has_play_id(log_text: str, play_id: int) -> bool:
    return re.search(rf"play id\s*:\s*{play_id}\b", log_text) is not None


def serial_shell_window(port_name: str, baudrate: int, command: str, capture_s: float, out_file: Path) -> str:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    chunks: list[bytes] = []
    with serial.Serial(port_name, baudrate, timeout=0.05, write_timeout=0.5) as port:
        try:
            port.reset_input_buffer()
        except Exception:
            pass
        port.write((command + "\r\n").encode("utf-8"))
        port.flush()
        deadline = time.monotonic() + float(capture_s)
        while time.monotonic() < deadline:
            data = port.read(4096)
            if data:
                chunks.append(data)
    text = b"".join(chunks).decode("utf-8", errors="replace")
    out_file.write_text(text, encoding="utf-8", errors="replace")
    return text


def play_phrase_and_slice_log(context, phrase: str, wait_s: float) -> str:
    before = len(current_log(context))
    step_native_play(context, phrase)
    if wait_s > 0:
        time.sleep(wait_s)
    return current_log(context)[before:]


@given("当前小度 Native 执行环境已准备")
def step_native_env_ready(context):
    context.project_id = "csk5062_xiaodu_fan"
    assert context.listenai_play.exists(), f"listenai-play 不存在: {context.listenai_play}"
    assert Path(context.log_port).exists(), f"日志口不存在: {context.log_port}"
    assert Path(context.proto_port).exists(), f"协议口不存在: {context.proto_port}"


@given("Native 已清除配置并烧录当前项目固件")
def step_native_clear_and_burn(context):
    burn_dir = context.scenario_dir / "native_burn"
    burn_dir.mkdir(parents=True, exist_ok=True)
    context.native_requirements = parse_requirements(context)

    preclear_text = serial_shell_window(
        context.log_port,
        context.log_baud,
        "config.clear",
        3.0,
        burn_dir / "00_preburn_config_clear.txt",
    )
    prereboot_text = serial_shell_window(
        context.log_port,
        context.log_baud,
        "reboot",
        10.0,
        burn_dir / "01_preburn_reboot.txt",
    )

    firmware = Path(os.environ.get("TRISOLARIS_FIRMWARE_BIN", context.root / "项目需求" / "CSK5062小度风扇需求" / "fw-csk5062_xiaodu_fan-v1.0.0.bin"))
    burn_script = context.root / "tools" / "burn_bundle" / "run_fan_burn.sh"
    cmd = [
        "bash",
        str(burn_script),
        "-FirmwareBin",
        str(firmware),
        "-CtrlPort",
        context.ctrl_port,
        "-BurnPort",
        context.log_port,
        "-PreBurnWaitMs",
        os.environ.get("TRISOLARIS_PRE_BURN_WAIT_MS", "6000"),
        "-MaxRetry",
        "3",
    ]
    completed = subprocess.run(
        cmd,
        cwd=context.root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=360,
    )
    run_log = burn_dir / "run_fan_burn.log"
    run_log.write_text("$ " + " ".join(cmd) + "\n" + completed.stdout + f"\nRC={completed.returncode}\n", encoding="utf-8")

    bundle_log = context.root / "tools" / "burn_bundle" / "linux" / "burn.log"
    bundle_tool_log = context.root / "tools" / "burn_bundle" / "linux" / "burn_tool.log"
    copied_burn_log = burn_dir / "burn.log"
    if bundle_log.exists():
        shutil.copy2(bundle_log, copied_burn_log)
    if bundle_tool_log.exists():
        shutil.copy2(bundle_tool_log, burn_dir / "burn_tool.log")

    burn_text = copied_burn_log.read_text(encoding="utf-8", errors="replace") if copied_burn_log.exists() else completed.stdout
    first_boot_config = parse_boot_config(burn_text)
    post_burn_reboot_config: dict[str, int | str] = {}
    if not first_boot_config and completed.returncode == 0 and "Burn flow completed" in burn_text:
        post_burn_text = serial_shell_window(
            context.log_port,
            context.log_baud,
            "reboot",
            10.0,
            burn_dir / "02_postburn_reboot_config.txt",
        )
        post_burn_reboot_config = parse_boot_config(post_burn_text)
        first_boot_config = post_burn_reboot_config
    try:
        firmware_for_report = str(firmware.resolve().relative_to(context.root))
    except ValueError:
        firmware_for_report = str(firmware.resolve())

    context.native_burn = {
        "firmware": firmware_for_report,
        "returncode": completed.returncode,
        "preclear_has_output": bool(preclear_text.strip()),
        "prereboot_has_output": bool(prereboot_text.strip()),
        "burn_log": str(copied_burn_log.relative_to(context.root)) if copied_burn_log.exists() else str(run_log.relative_to(context.root)),
        "first_boot_config": first_boot_config,
        "post_burn_reboot_config": post_burn_reboot_config,
    }
    (burn_dir / "native_burn_meta.json").write_text(json.dumps(context.native_burn, ensure_ascii=False, indent=2), encoding="utf-8")
    context.current_playback.append({"type": "native_burn", **context.native_burn})

    assert completed.returncode == 0, f"Native 烧录失败: {run_log}"
    assert "Burn flow completed" in burn_text, f"Native 烧录缺少成功标记: {copied_burn_log if copied_burn_log.exists() else run_log}"


@when("开始 Native 采集")
def step_native_start_capture(context):
    log_capture = SerialCapture(context.log_port, context.log_baud, context.scenario_dir / "ttyACM0_log.txt", as_hex=False)
    proto_capture = SerialCapture(context.proto_port, context.proto_baud, context.scenario_dir / "ttyACM2_proto_hex.txt", as_hex=True)
    context.current_capture["log"] = log_capture
    context.current_capture["proto"] = proto_capture
    log_capture.start()
    proto_capture.start()
    time.sleep(0.2)
    # 被动协议、播报和配置类断言依赖详细日志；每个场景采集开始后统一打开运行日志级别。
    try:
        log_capture.write(b"loglevel 4\r\n")
        time.sleep(0.3)
    except Exception as exc:  # pragma: no cover - hardware path
        context.current_errors.append(f"loglevel setup failed: {exc}")


@when('Native 播放语音 "{phrase}"')
def step_native_play(context, phrase):
    audio = audio_file(context, phrase)
    cmd = [
        sys.executable,
        str(context.listenai_play),
        "play",
        "--platform",
        "linux",
        "--audio-file",
        str(audio),
        "--device-key",
        context.device_key,
    ]
    completed = subprocess.run(cmd, cwd=context.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=30)
    playback_log = context.scenario_dir / f"native_play_{phrase}.log"
    playback_log.write_text("$ " + " ".join(cmd) + "\n" + completed.stdout + f"\nRC={completed.returncode}\n", encoding="utf-8")
    context.current_playback.append({
        "type": "native_play",
        "phrase": phrase,
        "audio": str(audio.relative_to(context.root)),
        "returncode": completed.returncode,
        "log": str(playback_log.relative_to(context.root)),
    })
    assert completed.returncode == 0, f"播放失败: {phrase}: {completed.stdout}"


@when("Native 等待 {seconds:g} 秒")
def step_native_wait(context, seconds):
    time.sleep(float(seconds))


@when("Native 执行动作表")
def step_native_action_table(context):
    assert context.table is not None, "缺少动作表"
    for row in context.table:
        action = row_value(row, "动作", "action").lower()
        value = row_value(row, "值", "value")
        wait_s = row_value(row, "等待秒", "wait_s", "wait", default="")
        if action in {"开始采集", "start_capture", "capture"}:
            step_native_start_capture(context)
        elif action in {"播放", "play"}:
            step_native_play(context, value)
        elif action in {"等待", "wait"}:
            step_native_wait(context, value or wait_s or "0")
            continue
        elif action in {"协议发送", "proto_send", "send_proto"}:
            step_native_send_proto(context, value)
        elif action in {"日志命令", "log_shell", "shell"}:
            step_native_shell(context, value, float(wait_s or 0))
            continue
        else:
            raise AssertionError(f"未知 Native 动作: {action}")
        if wait_s:
            time.sleep(float(wait_s))


@when("Native 使用音量边界探测法推断默认档位")
def step_native_probe_default_volume(context):
    assert context.current_capture.get("log") is not None, "音量探测前必须先开始 Native 采集"
    requirements = getattr(context, "native_requirements", None) or parse_requirements(context)
    context.native_requirements = requirements
    max_iterations = int(requirements["volume_steps"]) + 3
    max_overflow_id = 23
    min_overflow_id = 24
    observed_levels: list[int] = []
    action_segments: list[dict[str, object]] = []
    up_success_steps = 0
    last_level: int | None = None

    def command_pair(direction: str, index: int, phrase: str, overflow_id: int) -> tuple[str, int | None, bool]:
        before = len(current_log(context))
        step_native_play(context, "小度小度")
        time.sleep(1.6)
        step_native_play(context, phrase)
        time.sleep(4.0)
        segment = current_log(context)[before:]
        level = last_runtime_volume_level(segment)
        overflow = log_has_play_id(segment, overflow_id)
        segment_path = context.scenario_dir / f"volume_probe_{direction}_{index}.log"
        segment_path.write_text(segment, encoding="utf-8", errors="replace")
        action_segments.append(
            {
                "direction": direction,
                "index": index,
                "phrase": phrase,
                "runtime_level": level,
                "overflow_play_id": overflow_id if overflow else None,
                "segment": str(segment_path.relative_to(context.root)),
            }
        )
        if isinstance(level, int):
            observed_levels.append(level)
        return segment, level, overflow

    for index in range(1, max_iterations + 1):
        _, level, overflow = command_pair("default_to_max_up", index, "大声点", max_overflow_id)
        if overflow:
            break
        if level is None:
            break
        if last_level is not None and level <= last_level:
            break
        up_success_steps += 1
        last_level = level

    last_level = observed_levels[-1] if observed_levels else None
    for index in range(1, max_iterations + 1):
        _, level, overflow = command_pair("max_to_min_down", index, "小声点", min_overflow_id)
        if overflow:
            break
        if level is None:
            break
        if last_level is not None and level >= last_level:
            break
        last_level = level

    last_level = observed_levels[-1] if observed_levels else None
    for index in range(1, max_iterations + 1):
        _, level, overflow = command_pair("min_to_max_up", index, "大声点", max_overflow_id)
        if overflow:
            break
        if level is None:
            break
        if last_level is not None and level <= last_level:
            break
        last_level = level

    unique_levels = ordered_unique(observed_levels)
    total_levels = len(unique_levels)
    inferred_default_gear = total_levels - up_success_steps if total_levels > 0 else None
    context.native_volume_probe = {
        "expected_volume_steps": requirements["volume_steps"],
        "expected_default_volume": requirements["default_volume"],
        "first_boot_config": getattr(context, "native_burn", {}).get("first_boot_config", {}),
        "up_success_steps_to_max": up_success_steps,
        "observed_runtime_levels": observed_levels,
        "unique_runtime_levels": unique_levels,
        "sorted_runtime_levels": sorted(set(unique_levels)),
        "total_levels": total_levels,
        "inferred_default_gear": inferred_default_gear,
        "segments": action_segments,
    }
    probe_path = context.scenario_dir / "native_default_volume_probe.json"
    probe_path.write_text(json.dumps(context.native_volume_probe, ensure_ascii=False, indent=2), encoding="utf-8")
    context.current_markers["native_default_volume_probe"] = context.native_volume_probe


@when('Native 向协议口发送十六进制 "{frame}"')
def step_native_send_proto(context, frame):
    payload = bytes.fromhex(frame)
    cap = context.current_capture.get("proto")
    if cap is not None:
        cap.write(payload)
    else:
        with serial.Serial(context.proto_port, context.proto_baud, timeout=0.05, write_timeout=0.5) as port:
            port.write(payload)
            port.flush()
    sent_log = context.scenario_dir / "native_proto_sent.txt"
    sent_log.write_text(normalize_hex(frame) + "\n", encoding="utf-8")
    context.current_playback.append({"type": "native_proto_send", "frame": normalize_hex(frame), "log": str(sent_log.relative_to(context.root))})


@when('Native 执行日志口命令 "{command}" 并等待 {seconds:g} 秒')
def step_native_shell(context, command, seconds):
    payload = (command + "\r\n").encode("utf-8")
    cap = context.current_capture.get("log")
    if cap is not None:
        cap.write(payload)
    else:
        with serial.Serial(context.log_port, context.log_baud, timeout=0.05, write_timeout=0.5) as port:
            port.write(payload)
            port.flush()
    cmd_log = context.scenario_dir / "native_shell_command.txt"
    cmd_log.write_text(command + "\n", encoding="utf-8")
    time.sleep(float(seconds))
    if command.strip().lower() == "reboot" and cap is not None:
        try:
            cap.write(b"loglevel 4\r\n")
            time.sleep(0.5)
        except Exception as exc:  # pragma: no cover - hardware path
            context.current_errors.append(f"post-reboot loglevel setup failed: {exc}")


@then('Native 协议口应捕获 "{frame}"')
def step_native_proto_should(context, frame):
    wanted = normalize_hex(frame)
    frames = proto_frames(current_proto(context))
    ok = wanted in frames or wanted in normalize_hex(current_proto(context))
    context.current_markers[f"native_proto::{wanted}"] = ok
    assert ok, f"协议口未捕获 {wanted}; frames={frames}"


@then('Native 协议口不应捕获 "{frame}"')
def step_native_proto_should_not(context, frame):
    wanted = normalize_hex(frame)
    frames = proto_frames(current_proto(context))
    ok = wanted not in frames and wanted not in normalize_hex(current_proto(context))
    context.current_markers[f"native_proto_not::{wanted}"] = ok
    assert ok, f"协议口不应捕获 {wanted}; frames={frames}"


@then("Native 协议口不应捕获任何控制帧")
def step_native_no_control(context):
    frames = proto_frames(current_proto(context))
    controls = [frame for frame in frames if frame in CONTROL_FRAMES]
    context.current_markers["native_proto_no_control"] = not controls
    assert not controls, f"协议口出现控制帧: {controls}; frames={frames}"


@then("Native 断言表应满足")
def step_native_assertion_table(context):
    assert context.table is not None, "缺少断言表"
    for row in context.table:
        assertion = row_value(row, "断言", "assertion", "类型", "type").lower()
        value = row_value(row, "值", "value")
        if assertion in {"协议包含", "proto_contains"}:
            step_native_proto_should(context, value)
        elif assertion in {"协议不包含", "proto_not_contains"}:
            step_native_proto_should_not(context, value)
        elif assertion in {"无控制帧", "proto_no_control", "no_control"}:
            step_native_no_control(context)
        elif assertion in {"日志包含", "log_contains"}:
            step_native_log_should(context, value)
        elif assertion in {"日志不包含", "log_not_contains"}:
            step_native_log_should_not(context, value)
        else:
            raise AssertionError(f"未知 Native 断言: {assertion}")


@then("Native 默认音量档位应等于需求值")
def step_native_default_volume_should_match_requirement(context):
    probe = getattr(context, "native_volume_probe", None)
    assert probe, "缺少 Native 默认音量探测结果"
    expected = probe.get("expected_default_volume")
    actual = probe.get("inferred_default_gear")
    boot_config = probe.get("first_boot_config") or {}
    context.current_markers["native_default_volume_expected"] = expected
    context.current_markers["native_default_volume_actual"] = actual
    if not isinstance(actual, int):
        raise AssertionError(
            "默认音量探测未形成完整档位证据，不能判定默认值；"
            f"observed={probe.get('observed_runtime_levels')}, boot_config={boot_config}"
        )
    assert actual == expected, (
        "默认音量与需求不一致，归因候选仅保留固件默认值或需求错误；"
        f"Native 探测默认档位={actual}，需求={expected}，"
        f"启动 raw volume={boot_config.get('volume', 'missing')}，"
        f"总档位={probe.get('total_levels')}，上行有效步数={probe.get('up_success_steps_to_max')}，"
        f"runtime_levels={probe.get('unique_runtime_levels')}"
    )


@then('Native 日志口应出现 "{marker}"')
def step_native_log_should(context, marker):
    text = current_log(context)
    ok = marker in text
    context.current_markers[f"native_log::{marker}"] = ok
    assert ok, f"日志口未出现: {marker}"


@then('Native 日志口不应出现 "{marker}"')
def step_native_log_should_not(context, marker):
    text = current_log(context)
    ok = marker not in text
    context.current_markers[f"native_log_not::{marker}"] = ok
    assert ok, f"日志口不应出现: {marker}"
