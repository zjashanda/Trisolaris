#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
import tempfile
import threading
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

import pyaudio


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
AUDIO_DIR = ROOT / "tools" / "audio"
if str(AUDIO_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIO_DIR))

from fan_validation_helper import ensure_cached_tts  # noqa: E402


RESULT_ROOT = ROOT / "result" / "csk3022_htt_clothes_airer"
HANDSHAKE_SCRIPT = ROOT / "tools" / "serial" / "fan_proto_handshake_probe.py"

CTRL_PORT = "COM39"
LOG_PORT = "COM38"
PROTO_PORT = "COM36"
CTRL_BAUD = 115200
LOG_BAUD = 115200
PROTO_BAUD = 9600

BASELINE_RESET_HEX = "A5 FA 81 00 6C 8C FB"
DEFAULT_TEXTS = ["小好小好", "打开照明"]
DEFAULT_INITIAL_WAIT_S = 33.0
DEFAULT_GAP_S = 1.6
DEFAULT_CAPTURE_S = 80.0
DEFAULT_BUFFER_FRAMES = 1024


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def parse_data_words(text: str) -> list[int]:
    values: list[int] = []
    for match in re.finditer(r"A5 FA 7F ([0-9A-F]{2}) ([0-9A-F]{2}) [0-9A-F]{2} FB", text):
        values.append((int(match.group(1), 16) << 8) | int(match.group(2), 16))
    return values


def parse_play_ids(text: str) -> list[int]:
    return [int(match.group(1)) for match in re.finditer(r"play id\s*:\s*(\d+)", text)]


def normalize_audio(source: Path, target: Path, rate: int, channels: int) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        str(channels),
        "-ar",
        str(rate),
        str(target),
    ]
    completed = run_command(command)
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip() or "ffmpeg normalize failed")


def apply_channel_mode(path: Path, mode: str) -> None:
    if mode == "both":
        return
    with wave.open(str(path), "rb") as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        frame_rate = reader.getframerate()
        frame_count = reader.getnframes()
        frames = reader.readframes(frame_count)
    if channels != 2 or sample_width != 2:
        raise RuntimeError(f"channel mode {mode} requires 16-bit stereo wav, got channels={channels} sample_width={sample_width}")
    samples = list(struct.unpack("<" + ("h" * (len(frames) // 2)), frames))
    for index in range(0, len(samples), 2):
        left = samples[index]
        right = samples[index + 1]
        if mode == "left":
            samples[index] = left
            samples[index + 1] = 0
        elif mode == "right":
            samples[index] = 0
            samples[index + 1] = right
        else:
            raise RuntimeError(f"unsupported channel mode: {mode}")
    packed = struct.pack("<" + ("h" * len(samples)), *samples)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(sample_width)
        writer.setframerate(frame_rate)
        writer.writeframes(packed)


def prepare_audio_from_source(source: Path, rate: int, channels: int, channel_mode: str, suite_dir: Path, index: int) -> Path:
    normalized_path = suite_dir / f"play_{index:02d}_normalized.wav"
    normalize_audio(source, normalized_path, rate=rate, channels=channels)
    if channels == 2:
        apply_channel_mode(normalized_path, channel_mode)
    return normalized_path


def prepare_audio(text: str, rate: int, channels: int, channel_mode: str, suite_dir: Path, index: int) -> Path:
    cached_path, _ = ensure_cached_tts(text=text, voice="Microsoft Huihui Desktop", rate=0, label=f"htt_route_{index}")
    return prepare_audio_from_source(cached_path, rate=rate, channels=channels, channel_mode=channel_mode, suite_dir=suite_dir, index=index)


def build_handshake_command(result_dir: Path, capture_s: float) -> list[str]:
    return [
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
        "--inject-once",
        f"{BASELINE_RESET_HEX}@6.0",
    ]


def get_host_api_name(pa: pyaudio.PyAudio, host_api_index: int) -> str:
    try:
        return str(pa.get_host_api_info_by_index(host_api_index).get("name", ""))
    except Exception:
        return ""


def device_snapshot(pa: pyaudio.PyAudio, device_index: int) -> dict[str, Any]:
    info = pa.get_device_info_by_index(device_index)
    return {
        "index": device_index,
        "name": info.get("name"),
        "host_api_index": info.get("hostApi"),
        "host_api_name": get_host_api_name(pa, int(info.get("hostApi", -1))),
        "max_input_channels": int(info.get("maxInputChannels", 0)),
        "max_output_channels": int(info.get("maxOutputChannels", 0)),
        "default_sample_rate": int(info.get("defaultSampleRate", 0)),
    }


class CaptureRecorder:
    def __init__(self, pa: pyaudio.PyAudio, device_index: int, frames_per_buffer: int) -> None:
        info = pa.get_device_info_by_index(device_index)
        self.pa = pa
        self.device_index = device_index
        self.channels = int(info.get("maxInputChannels", 0)) or 1
        self.sample_rate = int(info.get("defaultSampleRate", 16000)) or 16000
        self.frames_per_buffer = frames_per_buffer
        self.max_abs = [0] * self.channels
        self.read_iterations = 0
        self.captured_bytes = 0
        self.error: str | None = None
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, name="htt-capture-recorder", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=10.0)

    def _run(self) -> None:
        try:
            stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.frames_per_buffer,
            )
        except Exception as exc:
            self.error = f"open failed: {exc!r}"
            return

        try:
            while not self._stop_event.is_set():
                try:
                    data = stream.read(self.frames_per_buffer, exception_on_overflow=False)
                except Exception as exc:
                    self.error = f"read failed: {exc!r}"
                    break
                self.captured_bytes += len(data)
                self.read_iterations += 1
                sample_count = len(data) // 2
                if sample_count <= 0:
                    continue
                samples = struct.unpack("<" + ("h" * sample_count), data)
                for index, sample in enumerate(samples):
                    channel = index % self.channels
                    value = abs(int(sample))
                    if value > self.max_abs[channel]:
                        self.max_abs[channel] = value
        finally:
            stream.stop_stream()
            stream.close()

    def summary(self) -> dict[str, Any]:
        return {
            "device_index": self.device_index,
            "channels": self.channels,
            "sample_rate": self.sample_rate,
            "captured_bytes": self.captured_bytes,
            "read_iterations": self.read_iterations,
            "max_abs": self.max_abs,
            "error": self.error,
        }


def play_wav_via_pyaudio(
    pa: pyaudio.PyAudio,
    output_device_index: int,
    audio_file: Path,
    frames_per_buffer: int,
) -> dict[str, Any]:
    with wave.open(str(audio_file), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        data_format = pa.get_format_from_width(sample_width)
        stream = pa.open(
            format=data_format,
            channels=channels,
            rate=sample_rate,
            output=True,
            output_device_index=output_device_index,
            frames_per_buffer=frames_per_buffer,
        )
        bytes_played = 0
        started = time.perf_counter()
        try:
            while True:
                data = handle.readframes(frames_per_buffer)
                if not data:
                    break
                stream.write(data)
                bytes_played += len(data)
        finally:
            stream.stop_stream()
            stream.close()
        duration_s = time.perf_counter() - started
        return {
            "audio_file": str(audio_file),
            "channels": channels,
            "sample_width": sample_width,
            "sample_rate": sample_rate,
            "bytes_played": bytes_played,
            "duration_s": round(duration_s, 3),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HTT handshake capture while playing audio through a chosen PyAudio output device.")
    parser.add_argument("--suite-tag", default="", help="Optional suffix for the result directory name.")
    parser.add_argument("--output-device-index", type=int, required=True, help="PyAudio output device index.")
    parser.add_argument("--capture-device-index", type=int, default=-1, help="Optional PyAudio capture device index for channel max-abs stats.")
    parser.add_argument("--output-rate", type=int, default=0, help="Override output sample rate; default uses device default.")
    parser.add_argument("--output-channels", type=int, default=0, help="Override output channel count; default uses device max output channels.")
    parser.add_argument("--channel-mode", choices=["both", "left", "right"], default="both", help="For stereo output, keep both channels or drive only the left/right channel.")
    parser.add_argument("--frames-per-buffer", type=int, default=DEFAULT_BUFFER_FRAMES)
    parser.add_argument("--initial-wait-s", type=float, default=DEFAULT_INITIAL_WAIT_S)
    parser.add_argument("--gap-s", type=float, default=DEFAULT_GAP_S)
    parser.add_argument("--capture-s", type=float, default=DEFAULT_CAPTURE_S)
    parser.add_argument("--text", action="append", default=[], help="Playback text. Repeat to play multiple utterances.")
    parser.add_argument("--audio-file", action="append", default=[], help="Existing audio file to play. Repeat to play multiple files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_name = f"{timestamp}_htt_pyaudio_route_probe"
    if args.suite_tag:
        suite_name = f"{suite_name}_{args.suite_tag}"
    suite_dir = RESULT_ROOT / suite_name
    suite_dir.mkdir(parents=True, exist_ok=True)

    pa = pyaudio.PyAudio()
    try:
        output_info = device_snapshot(pa, args.output_device_index)
        output_rate = args.output_rate or output_info["default_sample_rate"] or 16000
        output_channels = args.output_channels or output_info["max_output_channels"] or 2
        if args.audio_file:
            source_files = [Path(item).expanduser().resolve() for item in args.audio_file]
            missing_files = [str(path) for path in source_files if not path.exists()]
            if missing_files:
                raise FileNotFoundError(", ".join(missing_files))
            texts = args.text if args.text else [path.stem for path in source_files]
            normalized_files = [
                prepare_audio_from_source(
                    source=path,
                    rate=output_rate,
                    channels=output_channels,
                    channel_mode=args.channel_mode,
                    suite_dir=suite_dir,
                    index=index + 1,
                )
                for index, path in enumerate(source_files)
            ]
        else:
            texts = args.text or list(DEFAULT_TEXTS)
            normalized_files = [
                prepare_audio(
                    text=text,
                    rate=output_rate,
                    channels=output_channels,
                    channel_mode=args.channel_mode,
                    suite_dir=suite_dir,
                    index=index + 1,
                )
                for index, text in enumerate(texts)
            ]

        probe_stdout = (suite_dir / "probe_stdout.txt").open("w", encoding="utf-8")
        probe_stderr = (suite_dir / "probe_stderr.txt").open("w", encoding="utf-8")
        process = subprocess.Popen(build_handshake_command(suite_dir, args.capture_s), stdout=probe_stdout, stderr=probe_stderr)

        capture_recorder: CaptureRecorder | None = None
        capture_info: dict[str, Any] | None = None
        playback_records: list[dict[str, Any]] = []
        playback_error: str | None = None
        try:
            time.sleep(args.initial_wait_s)

            if args.capture_device_index >= 0:
                capture_info = device_snapshot(pa, args.capture_device_index)
                capture_recorder = CaptureRecorder(pa, args.capture_device_index, args.frames_per_buffer)
                capture_recorder.start()

            for index, audio_file in enumerate(normalized_files, start=1):
                try:
                    record = play_wav_via_pyaudio(
                        pa=pa,
                        output_device_index=args.output_device_index,
                        audio_file=audio_file,
                        frames_per_buffer=args.frames_per_buffer,
                    )
                except Exception as exc:
                    playback_error = repr(exc)
                    break
                record["text"] = texts[index - 1]
                playback_records.append(record)
                (suite_dir / f"play_{index:02d}.txt").write_text(
                    f"pyaudio index={args.output_device_index} bytes={record['bytes_played']} duration_s={record['duration_s']}\n",
                    encoding="utf-8",
                )
                if index < len(normalized_files):
                    time.sleep(args.gap_s)

            if capture_recorder is not None:
                time.sleep(0.6)
                capture_recorder.stop()

            process.wait(timeout=args.capture_s + 10.0)
        finally:
            if capture_recorder is not None and capture_recorder._thread.is_alive():
                capture_recorder.stop()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5.0)
            probe_stdout.close()
            probe_stderr.close()

        com36_text = (suite_dir / "com36_frames.txt").read_text(encoding="utf-8", errors="replace")
        com38_text = (suite_dir / "com38_utf8.txt").read_text(encoding="utf-8", errors="replace")
        data_words = parse_data_words(com36_text)
        play_ids = parse_play_ids(com38_text)

        summary = {
            "suite_name": suite_name,
            "suite_dir": str(suite_dir),
            "output_device": output_info,
            "capture_device": capture_info,
            "texts": texts,
            "output_rate": output_rate,
            "output_channels": output_channels,
            "channel_mode": args.channel_mode,
            "initial_wait_s": args.initial_wait_s,
            "gap_s": args.gap_s,
            "capture_s": args.capture_s,
            "playback": playback_records,
            "playback_error": playback_error,
            "capture_stats": capture_recorder.summary() if capture_recorder is not None else None,
            "wakeup_hits": com38_text.count("Wakeup:"),
            "keyword_hits": com38_text.count("keyword:"),
            "has_0001": 0x0001 in data_words,
            "has_0009": 0x0009 in data_words,
            "observed_words": [f"0x{word:04X}" for word in data_words],
            "observed_play_ids": play_ids,
        }
        (suite_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    finally:
        pa.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
