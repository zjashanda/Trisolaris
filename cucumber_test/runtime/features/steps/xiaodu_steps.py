from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from behave import given, then, when

from environment import SerialCapture


def audio_file(context, phrase: str) -> Path:
    candidates = sorted((context.root / "audio_cache" / "tts").glob(f"{phrase}_*.wav"))
    if not candidates:
        raise AssertionError(f"未找到语料音频: {phrase}")
    return candidates[-1]


def normalize_hex(value: str) -> str:
    return " ".join(value.upper().split())


@given("当前小度项目验证环境已准备")
def step_env_ready(context):
    context.project_id = "csk5062_xiaodu_fan"
    assert context.listenai_play.exists(), f"listenai-play 不存在: {context.listenai_play}"


@then('日志口 "{port}" 应存在')
def step_log_port_exists(context, port):
    assert Path(port).exists(), f"日志口不存在: {port}"
    assert port == context.log_port, f"日志口与当前环境不一致: feature={port}, env={context.log_port}"


@then('协议口 "{port}" 应存在')
def step_proto_port_exists(context, port):
    assert Path(port).exists(), f"协议口不存在: {port}"
    assert port == context.proto_port, f"协议口与当前环境不一致: feature={port}, env={context.proto_port}"


@then('控制口 "{port}" 应存在')
def step_ctrl_port_exists(context, port):
    assert Path(port).exists(), f"控制口不存在: {port}"
    assert port == context.ctrl_port, f"控制口与当前环境不一致: feature={port}, env={context.ctrl_port}"


@then('声卡 "{device_key}" 应可探测')
def step_audio_probe(context, device_key):
    assert device_key == context.device_key, f"声卡 key 与当前环境不一致: feature={device_key}, env={context.device_key}"
    cmd = [
        sys.executable,
        str(context.listenai_play),
        "probe",
        "--platform",
        "linux",
        "--device-key",
        device_key,
    ]
    completed = subprocess.run(cmd, cwd=context.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=20)
    probe_log = context.scenario_dir / "audio_probe.log"
    probe_log.write_text("$ " + " ".join(cmd) + "\n" + completed.stdout, encoding="utf-8")
    context.current_playback.append({"type": "probe", "returncode": completed.returncode, "log": str(probe_log.relative_to(context.root))})
    assert completed.returncode == 0, f"声卡 probe 失败: {completed.stdout}"


@when("开始采集日志口和协议口")
def step_start_capture(context):
    log_capture = SerialCapture(context.log_port, context.log_baud, context.scenario_dir / "ttyACM0_log.txt", as_hex=False)
    proto_capture = SerialCapture(context.proto_port, context.proto_baud, context.scenario_dir / "ttyACM2_proto_hex.txt", as_hex=True)
    context.current_capture["log"] = log_capture
    context.current_capture["proto"] = proto_capture
    log_capture.start()
    proto_capture.start()
    time.sleep(0.2)


@when('播放语音 "{phrase}"')
def step_play_phrase(context, phrase):
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
    playback_log = context.scenario_dir / f"play_{phrase}.log"
    playback_log.write_text("$ " + " ".join(cmd) + "\n" + completed.stdout + f"\nRC={completed.returncode}\n", encoding="utf-8")
    context.current_playback.append({
        "type": "play",
        "phrase": phrase,
        "audio": str(audio.relative_to(context.root)),
        "returncode": completed.returncode,
        "log": str(playback_log.relative_to(context.root)),
    })
    assert completed.returncode == 0, f"播放失败: {phrase}: {completed.stdout}"


@when("等待 {seconds:g} 秒")
def step_wait_seconds(context, seconds):
    time.sleep(float(seconds))


@then('日志口应出现 "{marker}"')
def step_log_contains(context, marker):
    cap = context.current_capture.get("log")
    assert cap is not None, "日志采集未启动"
    text = cap.text
    ok = marker in text
    context.current_markers[f"log::{marker}"] = ok
    if not ok and marker == "keyword:xiao du xiao du":
        ok = "keyword:xiao du xiao du" in text or "keyword: xiao du xiao du" in text
        context.current_markers[f"log::{marker}"] = ok
    assert ok, f"日志口未出现标记: {marker}"


@then('协议口应捕获十六进制帧 "{frame}"')
def step_proto_contains(context, frame):
    cap = context.current_capture.get("proto")
    assert cap is not None, "协议采集未启动"
    wanted = normalize_hex(frame)
    got = normalize_hex(cap.text)
    ok = wanted in got
    context.current_markers[f"proto::{wanted}"] = ok
    assert ok, f"协议口未捕获帧: {wanted}; 实际: {got[-400:]}"
