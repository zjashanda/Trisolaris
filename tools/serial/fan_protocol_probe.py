#!/usr/bin/env python
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import serial


ROOT = Path(__file__).resolve().parents[2]


def parse_hex_bytes(text: str) -> bytes:
    compact = text.replace(" ", "").replace(",", "").replace("0x", "").replace("0X", "")
    if len(compact) % 2 != 0:
        raise ValueError(f"Hex string must have an even number of digits: {text}")
    return bytes.fromhex(compact)


def capture_logs(
    proto_port_name: str,
    proto_baudrate: int,
    payload: bytes,
    log_port_name: str,
    log_baudrate: int,
    result_dir: Path,
    pre_wait_s: float,
    post_wait_s: float,
    send_loglevel4: bool,
) -> dict:
    result_dir.mkdir(parents=True, exist_ok=True)
    log_raw_path = result_dir / "log_raw.bin"
    log_text_path = result_dir / "log_utf8.txt"
    proto_rx_path = result_dir / "proto_rx.bin"
    meta_path = result_dir / "meta.json"

    log_chunks = bytearray()
    proto_rx_chunks = bytearray()
    started_at = datetime.now().isoformat(timespec="seconds")
    sent_at = None

    log_port = serial.Serial(log_port_name, baudrate=log_baudrate, timeout=0.05, write_timeout=0.5)
    proto_port = serial.Serial(proto_port_name, baudrate=proto_baudrate, timeout=0.05, write_timeout=0.5)
    try:
        log_port.reset_input_buffer()
        proto_port.reset_input_buffer()

        if send_loglevel4:
            log_port.write(b"loglevel 4\r\n")
            log_port.flush()
            time.sleep(1.0)
            log_port.reset_input_buffer()

        pre_deadline = time.time() + pre_wait_s
        while time.time() < pre_deadline:
            data = log_port.read(4096)
            if data:
                log_chunks.extend(data)
            data = proto_port.read(4096)
            if data:
                proto_rx_chunks.extend(data)
            time.sleep(0.02)

        proto_port.write(payload)
        proto_port.flush()
        sent_at = datetime.now().isoformat(timespec="milliseconds")

        post_deadline = time.time() + post_wait_s
        while time.time() < post_deadline:
            data = log_port.read(4096)
            if data:
                log_chunks.extend(data)
            data = proto_port.read(4096)
            if data:
                proto_rx_chunks.extend(data)
            time.sleep(0.02)
    finally:
        proto_port.close()
        log_port.close()

    log_raw_path.write_bytes(log_chunks)
    log_text_path.write_text(log_chunks.decode("utf-8", errors="replace"), encoding="utf-8")
    proto_rx_path.write_bytes(proto_rx_chunks)
    meta = {
        "started_at": started_at,
        "sent_at": sent_at,
        "proto_port": proto_port_name,
        "proto_baudrate": proto_baudrate,
        "payload_hex": payload.hex(" ").upper(),
        "log_port": log_port_name,
        "log_baudrate": log_baudrate,
        "pre_wait_s": pre_wait_s,
        "post_wait_s": post_wait_s,
        "send_loglevel4": send_loglevel4,
        "log_bytes": len(log_chunks),
        "proto_rx_bytes": len(proto_rx_chunks),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a binary protocol frame and capture device logs.")
    parser.add_argument("--proto-port", default="COM36")
    parser.add_argument("--proto-baudrate", type=int, default=9600)
    parser.add_argument("--payload-hex", required=True, help="Example: 'A5 FB 0A CC'")
    parser.add_argument("--log-port", default="COM38")
    parser.add_argument("--log-baudrate", type=int, default=115200)
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--pre-wait-s", type=float, default=0.3)
    parser.add_argument("--post-wait-s", type=float, default=4.0)
    parser.add_argument("--send-loglevel4", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    meta = capture_logs(
        proto_port_name=args.proto_port,
        proto_baudrate=args.proto_baudrate,
        payload=parse_hex_bytes(args.payload_hex),
        log_port_name=args.log_port,
        log_baudrate=args.log_baudrate,
        result_dir=Path(args.result_dir).expanduser().resolve(),
        pre_wait_s=args.pre_wait_s,
        post_wait_s=args.post_wait_s,
        send_loglevel4=args.send_loglevel4,
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
