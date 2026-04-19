#!/usr/bin/env python
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import serial


def write_meta(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def capture_shell(
    port_name: str,
    baudrate: int,
    command: str,
    result_dir: Path,
    capture_s: float,
    ready_wait_s: float,
) -> dict:
    result_dir.mkdir(parents=True, exist_ok=True)
    raw_path = result_dir / "serial_raw.bin"
    text_path = result_dir / "serial_utf8.txt"
    meta_path = result_dir / "meta.json"
    chunks = bytearray()

    port = serial.Serial(port_name, baudrate=baudrate, timeout=0.05, write_timeout=0.5)
    try:
        port.reset_input_buffer()
        port.write((command + "\r\n").encode("ascii"))
        port.flush()
        deadline = time.time() + capture_s
        while time.time() < deadline:
            data = port.read(4096)
            if data:
                chunks.extend(data)
            time.sleep(0.02)
    finally:
        port.close()

    raw_path.write_bytes(chunks)
    text_path.write_text(chunks.decode("utf-8", errors="replace"), encoding="utf-8")
    meta = {
        "mode": "shell",
        "command": command,
        "port": port_name,
        "baudrate": baudrate,
        "capture_s": capture_s,
        "ready_wait_s": ready_wait_s,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "log_bytes": len(chunks),
    }
    write_meta(meta_path, meta)
    if ready_wait_s > 0:
        time.sleep(ready_wait_s)
    return meta


def capture_powercycle(
    ctrl_port: str,
    ctrl_baudrate: int,
    log_port: str,
    log_baudrate: int,
    commands: list[str],
    result_dir: Path,
    cmd_delay_s: float,
    capture_s: float,
    ready_wait_s: float,
) -> dict:
    result_dir.mkdir(parents=True, exist_ok=True)
    raw_path = result_dir / "boot_log_raw.bin"
    text_path = result_dir / "boot_log_utf8.txt"
    meta_path = result_dir / "meta.json"
    chunks = bytearray()

    log_handle = serial.Serial(log_port, baudrate=log_baudrate, timeout=0.05, write_timeout=0.5)
    ctrl_handle = serial.Serial(ctrl_port, baudrate=ctrl_baudrate, timeout=0.05, write_timeout=0.5)
    try:
        log_handle.reset_input_buffer()
        ctrl_handle.reset_input_buffer()
        for command in commands:
            ctrl_handle.write((command + "\r\n").encode("ascii"))
            ctrl_handle.flush()
            time.sleep(cmd_delay_s)
        deadline = time.time() + capture_s
        while time.time() < deadline:
            data = log_handle.read(4096)
            if data:
                chunks.extend(data)
            time.sleep(0.02)
    finally:
        ctrl_handle.close()
        log_handle.close()

    raw_path.write_bytes(chunks)
    text_path.write_text(chunks.decode("utf-8", errors="replace"), encoding="utf-8")
    meta = {
        "mode": "powercycle",
        "commands": commands,
        "ctrl_port": ctrl_port,
        "ctrl_baudrate": ctrl_baudrate,
        "log_port": log_port,
        "log_baudrate": log_baudrate,
        "cmd_delay_s": cmd_delay_s,
        "capture_s": capture_s,
        "ready_wait_s": ready_wait_s,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "log_bytes": len(chunks),
    }
    write_meta(meta_path, meta)
    if ready_wait_s > 0:
        time.sleep(ready_wait_s)
    return meta


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generic serial maintenance helpers for shell and power-cycle capture.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_shell = sub.add_parser("shell")
    p_shell.add_argument("--port", default="COM38")
    p_shell.add_argument("--baudrate", type=int, default=115200)
    p_shell.add_argument("--command", required=True)
    p_shell.add_argument("--result-dir", required=True)
    p_shell.add_argument("--capture-s", type=float, default=8.0)
    p_shell.add_argument("--ready-wait-s", type=float, default=0.0)

    p_cycle = sub.add_parser("powercycle")
    p_cycle.add_argument("--ctrl-port", default="COM39")
    p_cycle.add_argument("--ctrl-baudrate", type=int, default=115200)
    p_cycle.add_argument("--log-port", default="COM38")
    p_cycle.add_argument("--log-baudrate", type=int, default=115200)
    p_cycle.add_argument("--commands", nargs="+", default=["uut-switch1.off", "uut-switch2.off", "uut-switch1.on"])
    p_cycle.add_argument("--result-dir", required=True)
    p_cycle.add_argument("--cmd-delay-s", type=float, default=0.35)
    p_cycle.add_argument("--capture-s", type=float, default=10.0)
    p_cycle.add_argument("--ready-wait-s", type=float, default=8.0)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result_dir = Path(args.result_dir).expanduser().resolve()
    if args.cmd == "shell":
        meta = capture_shell(
            port_name=args.port,
            baudrate=args.baudrate,
            command=args.command,
            result_dir=result_dir,
            capture_s=args.capture_s,
            ready_wait_s=args.ready_wait_s,
        )
    else:
        meta = capture_powercycle(
            ctrl_port=args.ctrl_port,
            ctrl_baudrate=args.ctrl_baudrate,
            log_port=args.log_port,
            log_baudrate=args.log_baudrate,
            commands=args.commands,
            result_dir=result_dir,
            cmd_delay_s=args.cmd_delay_s,
            capture_s=args.capture_s,
            ready_wait_s=args.ready_wait_s,
        )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
