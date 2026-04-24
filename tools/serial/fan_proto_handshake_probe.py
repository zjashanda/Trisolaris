#!/usr/bin/env python
import argparse
import codecs
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import serial

INTER_REPLY_GAP_S = 0.03


def parse_hex_bytes(text: str) -> bytes:
    compact = text.replace(" ", "").replace(",", "").replace("0x", "").replace("0X", "")
    if len(compact) % 2 != 0:
        raise ValueError(f"Hex string must have an even number of digits: {text}")
    return bytes.fromhex(compact)


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def frame_checksum(frame_without_tail: bytes) -> int:
    return sum(frame_without_tail) & 0xFF


def describe_frame(frame: bytes) -> str:
    if len(frame) != 7:
        return frame.hex(" ").upper()
    checksum_ok = frame_checksum(frame[:-2]) == frame[-2]
    return (
        f"{frame.hex(' ').upper()} "
        f"(dir=0x{frame[2]:02X}, data=0x{frame[3]:02X}{frame[4]:02X}, "
        f"checksum={'ok' if checksum_ok else 'bad'})"
    )


@dataclass
class Rule:
    name: str
    match: bytes
    reply: bytes
    max_hits: int = 0
    hits: int = 0

    def can_fire(self) -> bool:
        return self.max_hits <= 0 or self.hits < self.max_hits


@dataclass
class TimedSend:
    payload: bytes
    at_s: float
    sent: bool = False


def parse_rule(text: str) -> Rule:
    parts = text.split("=", 1)
    if len(parts) != 2:
        raise ValueError(f"Rule must be '<match>=<reply>': {text}")
    match_text, reply_text = parts
    name = match_text.strip().replace(" ", "_")
    return Rule(name=name, match=parse_hex_bytes(match_text), reply=parse_hex_bytes(reply_text))


def parse_periodic(text: str) -> tuple[bytes, float]:
    parts = text.split("@", 1)
    if len(parts) != 2:
        raise ValueError(f"Periodic rule must be '<payload>@<seconds>': {text}")
    return parse_hex_bytes(parts[0]), float(parts[1])


def parse_timed_send(text: str) -> TimedSend:
    parts = text.split("@", 1)
    if len(parts) != 2:
        raise ValueError(f"Timed send must be '<payload_hex>@<seconds>': {text}")
    return TimedSend(payload=parse_hex_bytes(parts[0]), at_s=float(parts[1]))


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def feed_timed_log_lines(
    line_buffer: str,
    chunk_text: str,
    t_s: float,
    timed_lines: list[dict],
) -> str:
    line_buffer += chunk_text
    while True:
        newline_index = line_buffer.find("\n")
        if newline_index < 0:
            break
        raw_line = line_buffer[:newline_index]
        line_buffer = line_buffer[newline_index + 1 :]
        timed_lines.append({"t_s": round(t_s, 3), "text": raw_line.rstrip("\r")})
    return line_buffer


def load_default_commands(name: str) -> list[str]:
    if name == "normal":
        return ["uut-switch1.off", "uut-switch2.off", "uut-switch1.on"]
    if name == "burn":
        return ["uut-switch1.off", "uut-switch2.on", "uut-switch1.on", "uut-switch2.off"]
    if name == "none":
        return []
    raise ValueError(f"Unknown command preset: {name}")


def run_probe(
    result_dir: Path,
    proto_port_name: str,
    proto_baudrate: int,
    log_port_name: str,
    log_baudrate: int,
    ctrl_port_name: str,
    ctrl_baudrate: int,
    commands: list[str],
    cmd_delay_s: float,
    pre_capture_s: float,
    capture_s: float,
    loglevel4_at_s: float,
    rules: list[Rule],
    periodic: list[tuple[bytes, float]],
    timed_sends: list[TimedSend],
) -> dict:
    result_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().isoformat(timespec="seconds")

    proto_raw = bytearray()
    log_raw = bytearray()
    proto_frames: list[dict] = []
    events: list[dict] = []
    control_log: list[str] = []
    proto_pending = bytearray()
    timed_log_lines: list[dict] = []
    log_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    log_line_buffer = ""
    last_log_t_s = 0.0

    periodic_state = [
        {"payload": payload, "interval_s": interval_s, "next_at": pre_capture_s + interval_s}
        for payload, interval_s in periodic
    ]

    with serial.Serial(log_port_name, baudrate=log_baudrate, timeout=0.05, write_timeout=0.5) as log_port, \
        serial.Serial(proto_port_name, baudrate=proto_baudrate, timeout=0.05, write_timeout=0.5) as proto_port, \
        serial.Serial(ctrl_port_name, baudrate=ctrl_baudrate, timeout=0.05, write_timeout=0.5) as ctrl_port:
        log_port.reset_input_buffer()
        proto_port.reset_input_buffer()
        ctrl_port.reset_input_buffer()

        for command in commands:
            stamp = datetime.now().isoformat(timespec="milliseconds")
            ctrl_port.write((command + "\r\n").encode("ascii"))
            ctrl_port.flush()
            control_log.append(f"[{stamp}] {command}")
            time.sleep(cmd_delay_s)

        start_monotonic = time.perf_counter()
        deadline = start_monotonic + pre_capture_s + capture_s
        loglevel4_sent = False

        while time.perf_counter() < deadline:
            now = time.perf_counter()
            elapsed_s = now - start_monotonic

            if loglevel4_at_s >= 0 and (not loglevel4_sent) and elapsed_s >= loglevel4_at_s:
                log_port.write(b"loglevel 4\r\n")
                log_port.flush()
                loglevel4_sent = True
                events.append(
                    {
                        "t_s": round(elapsed_s, 3),
                        "type": "log_command",
                        "payload_hex": "6C 6F 67 6C 65 76 65 6C 20 34 0D 0A",
                        "text": "loglevel 4",
                    }
                )

            proto_data = proto_port.read(4096)
            if proto_data:
                proto_raw.extend(proto_data)
                proto_pending.extend(proto_data)

                while True:
                    header_index = proto_pending.find(b"\xA5\xFA")
                    if header_index < 0:
                        if len(proto_pending) > 16:
                            del proto_pending[:-4]
                        break
                    if header_index > 0:
                        del proto_pending[:header_index]
                    if len(proto_pending) < 7:
                        break
                    frame = bytes(proto_pending[:7])
                    if frame[-1] != 0xFB:
                        del proto_pending[0]
                        continue
                    del proto_pending[:7]

                    frame_info = {
                        "t_s": round(elapsed_s, 3),
                        "frame_hex": frame.hex(" ").upper(),
                        "direction": f"0x{frame[2]:02X}",
                        "data_word": f"0x{frame[3]:02X}{frame[4]:02X}",
                        "checksum_ok": frame_checksum(frame[:-2]) == frame[-2],
                    }
                    proto_frames.append(frame_info)

                    for rule in rules:
                        if frame == rule.match and rule.can_fire():
                            proto_port.write(rule.reply)
                            proto_port.flush()
                            # Leave a small gap so two auto-replies do not get glued
                            # into one read line on the DUT side and trip checksum parsing.
                            time.sleep(INTER_REPLY_GAP_S)
                            rule.hits += 1
                            events.append(
                                {
                                    "t_s": round(elapsed_s, 3),
                                    "type": "rule_reply",
                                    "rule": rule.name,
                                    "match_hex": rule.match.hex(" ").upper(),
                                    "reply_hex": rule.reply.hex(" ").upper(),
                                    "hit_index": rule.hits,
                                }
                            )

            log_data = log_port.read(4096)
            if log_data:
                log_raw.extend(log_data)
                last_log_t_s = round(elapsed_s, 3)
                log_line_buffer = feed_timed_log_lines(
                    log_line_buffer,
                    log_decoder.decode(log_data),
                    elapsed_s,
                    timed_log_lines,
                )

            for item in periodic_state:
                if elapsed_s < pre_capture_s:
                    continue
                if now >= start_monotonic + item["next_at"]:
                    proto_port.write(item["payload"])
                    proto_port.flush()
                    events.append(
                        {
                            "t_s": round(elapsed_s, 3),
                            "type": "periodic_send",
                            "payload_hex": item["payload"].hex(" ").upper(),
                            "interval_s": item["interval_s"],
                        }
                    )
                    item["next_at"] += item["interval_s"]

            for item in timed_sends:
                if item.sent or elapsed_s < pre_capture_s or elapsed_s < item.at_s:
                    continue
                proto_port.write(item.payload)
                proto_port.flush()
                item.sent = True
                events.append(
                    {
                        "t_s": round(elapsed_s, 3),
                        "type": "timed_send",
                        "payload_hex": item.payload.hex(" ").upper(),
                        "at_s": item.at_s,
                    }
                )

            time.sleep(0.01)

    (result_dir / "com38_raw.bin").write_bytes(log_raw)
    write_text(result_dir / "com38_utf8.txt", decode_text(log_raw))
    final_tail = log_decoder.decode(b"", final=True)
    if final_tail:
        log_line_buffer = feed_timed_log_lines(log_line_buffer, final_tail, last_log_t_s, timed_log_lines)
    if log_line_buffer:
        timed_log_lines.append({"t_s": last_log_t_s, "text": log_line_buffer.rstrip("\r")})
    write_text(
        result_dir / "com38_timed_lines.txt",
        "\n".join(f"[{item['t_s']:>8.3f}] {item['text']}" for item in timed_log_lines) + ("\n" if timed_log_lines else ""),
    )
    write_json(result_dir / "com38_timed_lines.json", {"lines": timed_log_lines})
    (result_dir / "com36_raw.bin").write_bytes(proto_raw)
    write_text(result_dir / "com36_hex.txt", bytes(proto_raw).hex(" ").upper())
    write_text(
        result_dir / "com36_frames.txt",
        "\n".join(f"[{item['t_s']:>6}] {item['frame_hex']}" for item in proto_frames) + ("\n" if proto_frames else ""),
    )
    write_text(result_dir / "control_sequence.log", "\n".join(control_log) + ("\n" if control_log else ""))
    write_json(result_dir / "events.json", {"events": events})

    meta = {
        "started_at": started_at,
        "proto_port": proto_port_name,
        "proto_baudrate": proto_baudrate,
        "log_port": log_port_name,
        "log_baudrate": log_baudrate,
        "ctrl_port": ctrl_port_name,
        "ctrl_baudrate": ctrl_baudrate,
        "commands": commands,
        "cmd_delay_s": cmd_delay_s,
        "pre_capture_s": pre_capture_s,
        "capture_s": capture_s,
        "loglevel4_at_s": loglevel4_at_s,
        "rules": [
            {
                "name": rule.name,
                "match_hex": rule.match.hex(" ").upper(),
                "reply_hex": rule.reply.hex(" ").upper(),
                "hits": rule.hits,
                "max_hits": rule.max_hits,
            }
            for rule in rules
        ],
        "periodic": [
            {"payload_hex": payload.hex(" ").upper(), "interval_s": interval_s}
            for payload, interval_s in periodic
        ],
        "timed_sends": [
            {"payload_hex": item.payload.hex(" ").upper(), "at_s": item.at_s, "sent": item.sent}
            for item in timed_sends
        ],
        "proto_frames": len(proto_frames),
        "events": len(events),
        "proto_bytes": len(proto_raw),
        "log_bytes": len(log_raw),
    }
    write_json(result_dir / "meta.json", meta)
    return meta


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Power-cycle the device and emulate basic MCU handshake replies on COM36.")
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--proto-port", default="COM36")
    parser.add_argument("--proto-baudrate", type=int, default=9600)
    parser.add_argument("--log-port", default="COM38")
    parser.add_argument("--log-baudrate", type=int, default=115200)
    parser.add_argument("--ctrl-port", default="COM39")
    parser.add_argument("--ctrl-baudrate", type=int, default=115200)
    parser.add_argument("--command-preset", choices=["normal", "burn", "none"], default="normal")
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--cmd-delay-s", type=float, default=0.35)
    parser.add_argument("--pre-capture-s", type=float, default=0.0)
    parser.add_argument("--capture-s", type=float, default=12.0)
    parser.add_argument("--loglevel4-at-s", type=float, default=-1.0)
    parser.add_argument("--respond", action="append", default=[], help="Rule format: '<match_hex>=<reply_hex>'")
    parser.add_argument("--periodic", action="append", default=[], help="Periodic send: '<payload_hex>@<interval_s>'")
    parser.add_argument("--inject-once", action="append", default=[], help="Timed send: '<payload_hex>@<seconds>'")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    commands = load_default_commands(args.command_preset)
    if args.command:
        commands.extend(args.command)

    rules = [parse_rule(text) for text in args.respond]
    periodic = [parse_periodic(text) for text in args.periodic]
    timed_sends = [parse_timed_send(text) for text in args.inject_once]

    meta = run_probe(
        result_dir=Path(args.result_dir).expanduser().resolve(),
        proto_port_name=args.proto_port,
        proto_baudrate=args.proto_baudrate,
        log_port_name=args.log_port,
        log_baudrate=args.log_baudrate,
        ctrl_port_name=args.ctrl_port,
        ctrl_baudrate=args.ctrl_baudrate,
        commands=commands,
        cmd_delay_s=args.cmd_delay_s,
        pre_capture_s=args.pre_capture_s,
        capture_s=args.capture_s,
        loglevel4_at_s=args.loglevel4_at_s,
        rules=rules,
        periodic=periodic,
        timed_sends=timed_sends,
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
INTER_REPLY_GAP_S = 0.03
