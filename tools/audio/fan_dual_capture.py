#!/usr/bin/env python
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import serial

from fan_validation_helper import ensure_cached_tts, update_response_state
from listenai_play_repo import resolve_listenai_play


ROOT = Path(__file__).resolve().parents[2]


def pump_dual(
    log_port: serial.Serial,
    proto_port: serial.Serial,
    log_chunks: bytearray,
    proto_chunks: bytearray,
    duration_s: float,
    state: Optional[dict] = None,
) -> None:
    deadline = time.time() + duration_s
    local_log = bytearray()
    while time.time() < deadline:
        log_data = log_port.read(4096)
        if log_data:
            log_chunks.extend(log_data)
            local_log.extend(log_data)
            if state is not None:
                update_response_state(state, local_log.decode("utf-8", errors="replace"), time.time())
        proto_data = proto_port.read(4096)
        if proto_data:
            proto_chunks.extend(proto_data)
        time.sleep(0.02)


def wait_for_completion_dual(
    log_port: serial.Serial,
    proto_port: serial.Serial,
    log_chunks: bytearray,
    proto_chunks: bytearray,
    max_wait_s: float,
    min_wait_s: float,
    quiet_window_s: float,
    initial_state: Optional[dict] = None,
) -> dict:
    start = time.time()
    local_log = bytearray()
    state = {
        "saw_response": False,
        "saw_play_start": False,
        "saw_play_stop": False,
        "last_data_at": None,
    }
    if initial_state:
        state.update(
            {
                "saw_response": bool(initial_state.get("saw_response")),
                "saw_play_start": bool(initial_state.get("saw_play_start")),
                "saw_play_stop": bool(initial_state.get("saw_play_stop")),
                "last_data_at": initial_state.get("last_data_at"),
            }
        )
    completion_reason = None

    while True:
        now = time.time()
        log_data = log_port.read(4096)
        if log_data:
            log_chunks.extend(log_data)
            local_log.extend(log_data)
            update_response_state(state, local_log.decode("utf-8", errors="replace"), now)
            if completion_reason == "quiet_after_response":
                completion_reason = None

        proto_data = proto_port.read(4096)
        if proto_data:
            proto_chunks.extend(proto_data)

        elapsed = now - start
        last_data_at = state["last_data_at"]

        if state["saw_play_start"] and state["saw_play_stop"]:
            completion_reason = "play_stop"

        if completion_reason == "play_stop" and elapsed >= min_wait_s:
            return {"reason": completion_reason, "elapsed_s": round(elapsed, 3)}

        if (
            state["saw_response"]
            and not state["saw_play_start"]
            and last_data_at is not None
            and (now - last_data_at) >= quiet_window_s
        ):
            completion_reason = "quiet_after_response"

        if completion_reason == "quiet_after_response" and elapsed >= min_wait_s:
            return {"reason": completion_reason, "elapsed_s": round(elapsed, 3)}

        if elapsed >= max_wait_s:
            return {"reason": "max_wait", "elapsed_s": round(elapsed, 3)}
        time.sleep(0.02)


def run_playback_dual(
    audio_file: Path,
    device_key: str,
    log_port: serial.Serial,
    proto_port: serial.Serial,
    log_chunks: bytearray,
    proto_chunks: bytearray,
    listenai_play: Path,
) -> dict:
    cmd = [
        sys.executable,
        str(listenai_play),
        "play",
        "--audio-file",
        str(audio_file),
        "--device-key",
        device_key,
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    playback_output = []
    local_log = bytearray()
    response_state = {
        "saw_response": False,
        "saw_play_start": False,
        "saw_play_stop": False,
        "last_data_at": None,
    }
    while True:
        log_data = log_port.read(4096)
        if log_data:
            log_chunks.extend(log_data)
            local_log.extend(log_data)
            update_response_state(response_state, local_log.decode("utf-8", errors="replace"), time.time())
        proto_data = proto_port.read(4096)
        if proto_data:
            proto_chunks.extend(proto_data)
        if proc.stdout:
            line = proc.stdout.readline()
            if line:
                playback_output.append(line.rstrip("\r\n"))
        if proc.poll() is not None:
            break
        time.sleep(0.02)
    if proc.stdout:
        for line in proc.stdout.read().splitlines():
            playback_output.append(line)
    response_state["serial_bytes_during_playback"] = len(local_log)
    return {
        "output": playback_output,
        "response_state": response_state,
    }


def capture_sequence(
    texts: list[str],
    device_key: str,
    log_port_name: str,
    log_baudrate: int,
    proto_port_name: str,
    proto_baudrate: int,
    result_dir: Path,
    between_max_wait_s: float,
    between_min_wait_s: float,
    quiet_window_s: float,
    post_wait_s: float,
    send_loglevel4: bool,
    voice: str,
    rate: int,
    update_play_tool: bool,
) -> dict:
    result_dir.mkdir(parents=True, exist_ok=True)
    log_raw_path = result_dir / "log_raw.bin"
    log_text_path = result_dir / "log_utf8.txt"
    proto_raw_path = result_dir / "proto_raw.bin"
    proto_hex_path = result_dir / "proto_hex.txt"
    meta_path = result_dir / "meta.json"

    audio_items = []
    for index, text in enumerate(texts, start=1):
        audio_path, cached = ensure_cached_tts(text=text, voice=voice, rate=rate, label=f"dual_{index}")
        audio_items.append({"text": text, "audio_file": str(audio_path), "cached": cached})

    log_port = serial.Serial(log_port_name, baudrate=log_baudrate, timeout=0.05, write_timeout=0.5)
    proto_port = serial.Serial(proto_port_name, baudrate=proto_baudrate, timeout=0.05, write_timeout=0.5)
    listenai_play = resolve_listenai_play(update=update_play_tool)
    started_at = datetime.now().isoformat(timespec="seconds")
    log_chunks = bytearray()
    proto_chunks = bytearray()
    playback_output = []
    between_wait_result = []

    try:
        log_port.reset_input_buffer()
        proto_port.reset_input_buffer()
        if send_loglevel4:
            log_port.write(b"loglevel 4\r\n")
            log_port.flush()
            time.sleep(1.0)
            log_port.reset_input_buffer()
            proto_port.reset_input_buffer()

        for index, item in enumerate(audio_items):
            play_result = run_playback_dual(
                audio_file=Path(item["audio_file"]),
                device_key=device_key,
                log_port=log_port,
                proto_port=proto_port,
                log_chunks=log_chunks,
                proto_chunks=proto_chunks,
                listenai_play=listenai_play,
            )
            playback_output.append(
                {
                    "text": item["text"],
                    "audio_file": item["audio_file"],
                    "cached": item["cached"],
                    "output": play_result["output"],
                    "response_state": play_result["response_state"],
                }
            )
            if index < len(audio_items) - 1 and between_max_wait_s > 0:
                between_wait_result.append(
                    wait_for_completion_dual(
                        log_port=log_port,
                        proto_port=proto_port,
                        log_chunks=log_chunks,
                        proto_chunks=proto_chunks,
                        max_wait_s=between_max_wait_s,
                        min_wait_s=between_min_wait_s,
                        quiet_window_s=quiet_window_s,
                        initial_state=play_result["response_state"],
                    )
                )

        pump_dual(
            log_port=log_port,
            proto_port=proto_port,
            log_chunks=log_chunks,
            proto_chunks=proto_chunks,
            duration_s=post_wait_s,
        )
    finally:
        proto_port.close()
        log_port.close()

    log_raw_path.write_bytes(log_chunks)
    log_text_path.write_text(log_chunks.decode("utf-8", errors="replace"), encoding="utf-8")
    proto_raw_path.write_bytes(proto_chunks)
    proto_hex_path.write_text(proto_chunks.hex(" ").upper(), encoding="utf-8")
    meta = {
        "texts": texts,
        "audio_items": audio_items,
        "device_key": device_key,
        "log_port": log_port_name,
        "log_baudrate": log_baudrate,
        "proto_port": proto_port_name,
        "proto_baudrate": proto_baudrate,
        "started_at": started_at,
        "between_max_wait_s": between_max_wait_s,
        "between_min_wait_s": between_min_wait_s,
        "quiet_window_s": quiet_window_s,
        "post_wait_s": post_wait_s,
        "send_loglevel4": send_loglevel4,
        "listenai_play": str(listenai_play),
        "voice": voice,
        "rate": rate,
        "playback_output": playback_output,
        "between_wait_result": between_wait_result,
        "log_bytes": len(log_chunks),
        "proto_bytes": len(proto_chunks),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Play TTS prompts and capture both log and protocol UART.")
    parser.add_argument("--texts", nargs="+", required=True)
    parser.add_argument("--device-key", required=True)
    parser.add_argument("--log-port", default="COM38")
    parser.add_argument("--log-baudrate", type=int, default=115200)
    parser.add_argument("--proto-port", default="COM36")
    parser.add_argument("--proto-baudrate", type=int, default=9600)
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--between-max-wait-s", type=float, default=4.5)
    parser.add_argument("--between-min-wait-s", type=float, default=0.8)
    parser.add_argument("--quiet-window-s", type=float, default=0.6)
    parser.add_argument("--post-wait-s", type=float, default=4.0)
    parser.add_argument("--send-loglevel4", action="store_true")
    parser.add_argument("--voice", default="Microsoft Huihui Desktop")
    parser.add_argument("--rate", type=int, default=0)
    parser.add_argument("--update-play-tool", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    meta = capture_sequence(
        texts=args.texts,
        device_key=args.device_key,
        log_port_name=args.log_port,
        log_baudrate=args.log_baudrate,
        proto_port_name=args.proto_port,
        proto_baudrate=args.proto_baudrate,
        result_dir=Path(args.result_dir).expanduser().resolve(),
        between_max_wait_s=args.between_max_wait_s,
        between_min_wait_s=args.between_min_wait_s,
        quiet_window_s=args.quiet_window_s,
        post_wait_s=args.post_wait_s,
        send_loglevel4=args.send_loglevel4,
        voice=args.voice,
        rate=args.rate,
        update_play_tool=args.update_play_tool,
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
