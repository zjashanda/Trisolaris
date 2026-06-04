from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

import serial

ROOT = Path(__file__).resolve().parents[3]


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "scenario"


class SerialCapture:
    def __init__(self, port: str, baud: int, out_file: Path, *, as_hex: bool) -> None:
        self.port = port
        self.baud = baud
        self.out_file = out_file
        self.as_hex = as_hex
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.serial_port: serial.Serial | None = None
        self.write_lock = threading.Lock()
        self.chunks: list[bytes] = []
        self.error: str | None = None

    def start(self) -> None:
        self.out_file.parent.mkdir(parents=True, exist_ok=True)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self) -> None:
        try:
            with serial.Serial(self.port, self.baud, timeout=0.05, write_timeout=0.5) as ser, self.out_file.open("wb") as fh:
                self.serial_port = ser
                try:
                    ser.reset_input_buffer()
                except Exception:
                    pass
                self.ready_event.set()
                while not self.stop_event.is_set():
                    data = ser.read(4096)
                    if not data:
                        continue
                    self.chunks.append(data)
                    if self.as_hex:
                        fh.write(data.hex(" ").upper().encode("ascii") + b"\n")
                    else:
                        fh.write(data)
                    fh.flush()
        except Exception as exc:  # pragma: no cover - hardware path
            self.error = f"{self.port}: {exc}"
            self.ready_event.set()
        finally:
            self.serial_port = None

    def write(self, data: bytes, *, timeout_s: float = 1.0) -> None:
        if not self.ready_event.wait(timeout_s):
            raise RuntimeError(f"{self.port}: capture port is not ready for write")
        if self.error:
            raise RuntimeError(self.error)
        if self.serial_port is None:
            raise RuntimeError(f"{self.port}: capture port is already closed")
        with self.write_lock:
            self.serial_port.write(data)
            self.serial_port.flush()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

    @property
    def text(self) -> str:
        if self.as_hex:
            return b"".join(self.chunks).hex(" ").upper()
        return b"".join(self.chunks).decode("utf-8", errors="replace")

    @property
    def byte_count(self) -> int:
        return sum(len(chunk) for chunk in self.chunks)


def before_all(context):
    run_id = os.environ.get("TRISOLARIS_CUCUMBER_RUN_ID") or datetime.now().strftime("%Y%m%d_%H%M%S_xiaodu_cucumber")
    context.run_id = run_id
    context.root = ROOT
    context.report_dir = Path(os.environ.get("TRISOLARIS_CUCUMBER_REPORT_DIR", ROOT / "cucumber_test" / "debug" / "reports" / run_id)).resolve()
    context.evidence_dir = Path(os.environ.get("TRISOLARIS_CUCUMBER_EVIDENCE_DIR", ROOT / "cucumber_test" / "debug" / "evidence" / run_id)).resolve()
    context.report_dir.mkdir(parents=True, exist_ok=True)
    context.evidence_dir.mkdir(parents=True, exist_ok=True)
    context.log_port = os.environ.get("TRISOLARIS_LOG_PORT", "/dev/ttyACM0")
    context.proto_port = os.environ.get("TRISOLARIS_PROTO_PORT", "/dev/ttyACM2")
    context.ctrl_port = os.environ.get("TRISOLARIS_CTRL_PORT", "/dev/ttyACM4")
    context.log_baud = int(os.environ.get("TRISOLARIS_LOG_BAUD", "115200"))
    context.proto_baud = int(os.environ.get("TRISOLARIS_PROTO_BAUD", "9600"))
    context.device_key = os.environ.get("TRISOLARIS_DEVICE_KEY", "VID_8765&PID_5678:USB_0_4_3_1_0")
    context.listenai_play = Path(os.environ.get("TRISOLARIS_LISTENAI_PLAY", ROOT / "tools" / "audio" / "listenai-play" / "scripts" / "listenai_play.py")).resolve()
    if not context.listenai_play.exists():
        context.listenai_play = Path("/home/aitestu/.codex/skills/listenai-play/scripts/listenai_play.py")
    context.scenario_evidence = []


def before_scenario(context, scenario):
    context.current_capture = {}
    context.current_playback = []
    context.current_markers = {}
    context.current_errors = []
    context.scenario_dir = context.evidence_dir / safe_name(scenario.name)
    context.scenario_dir.mkdir(parents=True, exist_ok=True)


def after_scenario(context, scenario):
    for cap in getattr(context, "current_capture", {}).values():
        cap.stop()
    evidence = {
        "scenario": scenario.name,
        "status": scenario.status.name if hasattr(scenario.status, "name") else str(scenario.status),
        "dir": str(context.scenario_dir.relative_to(context.root)),
        "captures": {},
        "playback": getattr(context, "current_playback", []),
        "markers": getattr(context, "current_markers", {}),
        "errors": getattr(context, "current_errors", []),
    }
    for name, cap in getattr(context, "current_capture", {}).items():
        evidence["captures"][name] = {
            "path": str(cap.out_file.relative_to(context.root)),
            "bytes": cap.byte_count,
            "error": cap.error,
        }
        if cap.error:
            evidence["errors"].append(cap.error)
    (context.scenario_dir / "scenario_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    context.scenario_evidence.append(evidence)


def after_all(context):
    out = context.report_dir / "scenario_evidence_index.json"
    out.write_text(json.dumps(context.scenario_evidence, ensure_ascii=False, indent=2), encoding="utf-8")
