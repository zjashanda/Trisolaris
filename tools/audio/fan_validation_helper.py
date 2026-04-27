#!/usr/bin/env python
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import serial
from listenai_play_repo import resolve_listenai_play


ROOT = Path(__file__).resolve().parents[2]
AUDIO_CACHE_DIR = ROOT / "audio_cache" / "tts"
MANIFEST_PATH = ROOT / "audio_cache" / "manifest.json"


def run_tts(text: str, out_path: Path, voice: str, rate: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    def validate_output() -> None:
        if not out_path.is_file() or out_path.stat().st_size <= 44:
            raise RuntimeError(f"TTS output missing or too small: {out_path}")

    def try_powershell_tts() -> bool:
        if not shutil.which("powershell"):
            errors.append("PowerShell TTS skipped: powershell not found")
            return False
        ps_text = text.replace("'", "''")
        ps_out = str(out_path).replace("'", "''")
        ps_voice = voice.replace("'", "''")
        ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.SelectVoice('{ps_voice}'); "
            f"$s.Rate = {rate}; "
            f"$s.SetOutputToWaveFile('{ps_out}'); "
            f"$s.Speak('{ps_text}'); "
            "$s.Dispose();"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            check=False,
            timeout=int(os.environ.get("TRISOLARIS_TTS_TIMEOUT_S", "60")),
        )
        if completed.returncode != 0:
            errors.append(
                f"PowerShell TTS failed: {completed.returncode}; stdout={completed.stdout.strip()}; stderr={completed.stderr.strip()}"
            )
            return False
        validate_output()
        return True

    def try_edge_tts() -> bool:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            errors.append("edge-tts skipped: ffmpeg not found")
            return False
        edge_voice = os.environ.get("TRISOLARIS_EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
        edge_rate = os.environ.get("TRISOLARIS_EDGE_TTS_RATE", f"{rate:+d}%")
        mp3_path = out_path.with_suffix(".edge.mp3")
        script = (
            "import asyncio, sys, edge_tts\n"
            "async def main():\n"
            "    communicate = edge_tts.Communicate(sys.argv[1], voice=sys.argv[3], rate=sys.argv[4])\n"
            "    await communicate.save(sys.argv[2])\n"
            "asyncio.run(main())\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script, text, str(mp3_path), edge_voice, edge_rate],
            capture_output=True,
            text=True,
            check=False,
            timeout=int(os.environ.get("TRISOLARIS_TTS_TIMEOUT_S", "60")),
        )
        if completed.returncode != 0 or not mp3_path.is_file() or mp3_path.stat().st_size <= 0:
            errors.append(
                f"edge-tts failed: {completed.returncode}; stdout={completed.stdout.strip()}; stderr={completed.stderr.strip()}"
            )
            mp3_path.unlink(missing_ok=True)
            return False
        converted = subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(mp3_path), "-ar", "16000", "-ac", "1", str(out_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=int(os.environ.get("TRISOLARIS_TTS_TIMEOUT_S", "60")),
        )
        mp3_path.unlink(missing_ok=True)
        if converted.returncode != 0:
            errors.append(
                f"edge-tts ffmpeg convert failed: {converted.returncode}; stdout={converted.stdout.strip()}; stderr={converted.stderr.strip()}"
            )
            return False
        validate_output()
        return True

    def try_espeak_tts() -> bool:
        espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        ffmpeg = shutil.which("ffmpeg")
        if not espeak:
            errors.append("espeak TTS skipped: espeak-ng/espeak not found")
            return False
        temp_path = out_path.with_suffix(".espeak.wav")
        voice_name = os.environ.get("TRISOLARIS_ESPEAK_VOICE", "cmn")
        speed = int(os.environ.get("TRISOLARIS_ESPEAK_SPEED", str(max(120, 160 + rate * 10))))
        completed = subprocess.run(
            [espeak, "-v", voice_name, "-s", str(speed), "-w", str(temp_path), text],
            capture_output=True,
            text=True,
            check=False,
            timeout=int(os.environ.get("TRISOLARIS_TTS_TIMEOUT_S", "60")),
        )
        if completed.returncode != 0 or not temp_path.is_file() or temp_path.stat().st_size <= 44:
            errors.append(
                f"espeak TTS failed: {completed.returncode}; stdout={completed.stdout.strip()}; stderr={completed.stderr.strip()}"
            )
            temp_path.unlink(missing_ok=True)
            return False
        if ffmpeg:
            converted = subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-i", str(temp_path), "-ar", "16000", "-ac", "1", str(out_path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=int(os.environ.get("TRISOLARIS_TTS_TIMEOUT_S", "60")),
            )
            temp_path.unlink(missing_ok=True)
            if converted.returncode != 0:
                errors.append(
                    f"espeak ffmpeg convert failed: {converted.returncode}; stdout={converted.stdout.strip()}; stderr={converted.stderr.strip()}"
                )
                return False
        else:
            temp_path.replace(out_path)
        validate_output()
        return True

    preferred = os.environ.get("TRISOLARIS_TTS_ENGINE", "").strip().lower()
    engines = {
        "powershell": try_powershell_tts,
        "edge": try_edge_tts,
        "edge-tts": try_edge_tts,
        "espeak": try_espeak_tts,
        "espeak-ng": try_espeak_tts,
    }
    ordered = [engines[preferred]] if preferred in engines else []
    for engine in [try_powershell_tts, try_edge_tts, try_espeak_tts]:
        if engine not in ordered:
            ordered.append(engine)
    for engine in ordered:
        try:
            if engine():
                return
        except Exception as exc:
            errors.append(f"{engine.__name__} raised {type(exc).__name__}: {exc}")
            out_path.unlink(missing_ok=True)
    raise RuntimeError("TTS failed on all engines:\n" + "\n".join(errors))


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        return {"entries": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def sanitize_filename_fragment(value: str) -> str:
    value = re.sub(r"\s+", "_", value.strip())
    cleaned = re.sub(r"[^0-9A-Za-z_\-\u4E00-\u9FFF]+", "_", value)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._ ")
    return cleaned or "tts"


def build_tts_filename(text: str, label: str, key: str) -> str:
    # Prefer the spoken text itself so cached wav names stay human-readable in Chinese.
    text_fragment = sanitize_filename_fragment(text)
    label_fragment = sanitize_filename_fragment(label)
    if text_fragment != "tts":
        base = text_fragment
    elif label_fragment != "tts":
        base = label_fragment
    else:
        base = "tts"
    if len(base) > 32:
        base = base[:32].rstrip("_")
    return f"{base}_{key[:10]}.wav"


def relocate_cached_file(existing: Path, preferred: Path) -> Path:
    if existing.resolve() == preferred.resolve():
        return existing
    preferred.parent.mkdir(parents=True, exist_ok=True)
    if preferred.is_file():
        return preferred
    try:
        existing.rename(preferred)
        return preferred
    except OSError:
        return existing


def cache_key(text: str, voice: str, rate: int) -> str:
    raw = f"{voice}\n{rate}\n{text}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def resolve_manifest_audio_path(raw_path: str) -> Path:
    normalized = Path(raw_path.replace("\\", "/"))
    candidate = ROOT / normalized
    if candidate.is_file():
        return candidate
    fallback = AUDIO_CACHE_DIR / normalized.name
    return fallback


def ensure_cached_tts(text: str, voice: str, rate: int, label: str) -> tuple[Path, bool]:
    manifest = load_manifest()
    entries = manifest.setdefault("entries", {})
    key = cache_key(text, voice, rate)
    preferred_name = build_tts_filename(text=text, label=label, key=key)
    preferred_path = AUDIO_CACHE_DIR / preferred_name
    if key in entries:
        existing = resolve_manifest_audio_path(entries[key]["path"])
        if existing.is_file():
            final_path = relocate_cached_file(existing, preferred_path)
            entries[key]["path"] = str(final_path.relative_to(ROOT))
            entries[key]["label"] = label
            save_manifest(manifest)
            return final_path, True

    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = preferred_path
    run_tts(text, out_path, voice, rate)
    entries[key] = {
        "text": text,
        "voice": voice,
        "rate": rate,
        "label": label,
        "path": str(out_path.relative_to(ROOT)),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_manifest(manifest)
    return out_path, False


def pump_serial(port: serial.Serial, chunks: bytearray, duration_s: float) -> None:
    deadline = time.time() + duration_s
    while time.time() < deadline:
        data = port.read(4096)
        if data:
            chunks.extend(data)
        time.sleep(0.02)


def update_response_state(state: dict, text: str, event_time: Optional[float] = None) -> None:
    if any(marker in text for marker in ["Wakeup:", "keyword:", "send msg::", "evt msg -> exit"]):
        state["saw_response"] = True
    if "play start" in text:
        state["saw_response"] = True
        state["saw_play_start"] = True
    if "play stop" in text:
        state["saw_response"] = True
        state["saw_play_stop"] = True
    if event_time is not None:
        state["last_data_at"] = event_time


def wait_for_response_completion(
    port: serial.Serial,
    chunks: bytearray,
    max_wait_s: float,
    min_wait_s: float,
    quiet_window_s: float,
    initial_state: Optional[dict] = None,
) -> dict:
    start = time.time()
    local_chunks = bytearray()
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
    completion_reason: Optional[str] = None

    while True:
        now = time.time()
        data = port.read(4096)
        if data:
            chunks.extend(data)
            local_chunks.extend(data)
            text = local_chunks.decode("utf-8", errors="replace")
            update_response_state(state, text, now)
            if completion_reason == "quiet_after_response":
                completion_reason = None

        elapsed = now - start
        last_data_at = state["last_data_at"]

        if state["saw_play_start"] and state["saw_play_stop"]:
            completion_reason = "play_stop"

        if completion_reason == "play_stop" and elapsed >= min_wait_s:
            return {
                "reason": completion_reason,
                "elapsed_s": round(elapsed, 3),
            }

        if (
            state["saw_response"]
            and not state["saw_play_start"]
            and last_data_at is not None
            and (now - last_data_at) >= quiet_window_s
        ):
            completion_reason = "quiet_after_response"

        if completion_reason == "quiet_after_response" and elapsed >= min_wait_s:
            return {
                "reason": completion_reason,
                "elapsed_s": round(elapsed, 3),
            }

        if elapsed >= max_wait_s:
            return {
                "reason": "max_wait",
                "elapsed_s": round(elapsed, 3),
            }
        time.sleep(0.02)


def run_playback(
    audio_file: Path,
    device_key: str,
    port: serial.Serial,
    chunks: bytearray,
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
    playback_output: list[str] = []
    playback_chunks = bytearray()
    response_state = {
        "saw_response": False,
        "saw_play_start": False,
        "saw_play_stop": False,
        "last_data_at": None,
    }
    while True:
        data = port.read(4096)
        if data:
            chunks.extend(data)
            playback_chunks.extend(data)
            text = playback_chunks.decode("utf-8", errors="replace")
            update_response_state(response_state, text, time.time())
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
    response_state["serial_bytes_during_playback"] = len(playback_chunks)
    return {
        "output": playback_output,
        "response_state": response_state,
    }


def capture_sequence(
    audio_files: list[Path],
    device_key: str,
    serial_port: str,
    baudrate: int,
    result_dir: Path,
    between_max_wait_s: float,
    between_min_wait_s: float,
    quiet_window_s: float,
    post_wait_s: float,
    send_loglevel4: bool,
    update_play_tool: bool,
) -> dict:
    result_dir.mkdir(parents=True, exist_ok=True)
    raw_path = result_dir / "serial_raw.bin"
    text_path = result_dir / "serial_utf8.txt"
    meta_path = result_dir / "meta.json"

    listenai_play = resolve_listenai_play(update=update_play_tool)
    port = serial.Serial(serial_port, baudrate=baudrate, timeout=0.05, write_timeout=0.5)
    try:
        port.reset_input_buffer()
        if send_loglevel4:
            port.write(b"loglevel 4\r\n")
            port.flush()
            time.sleep(1.0)
            port.reset_input_buffer()
        started_at = datetime.now().isoformat(timespec="seconds")
        chunks = bytearray()
        playback_output: list[dict] = []
        between_wait_result: list[dict] = []
        for index, audio_file in enumerate(audio_files):
            play_result = run_playback(audio_file, device_key, port, chunks, listenai_play)
            playback_output.append(
                {
                    "audio_file": str(audio_file),
                    "output": play_result["output"],
                    "response_state": play_result["response_state"],
                }
            )
            if index < len(audio_files) - 1 and between_max_wait_s > 0:
                between_wait_result.append(
                    wait_for_response_completion(
                        port=port,
                        chunks=chunks,
                        max_wait_s=between_max_wait_s,
                        min_wait_s=between_min_wait_s,
                        quiet_window_s=quiet_window_s,
                        initial_state=play_result["response_state"],
                    )
                )

        pump_serial(port, chunks, post_wait_s)
    finally:
        port.close()

    raw_path.write_bytes(chunks)
    text_path.write_text(chunks.decode("utf-8", errors="replace"), encoding="utf-8")
    meta = {
        "audio_files": [str(item) for item in audio_files],
        "device_key": device_key,
        "serial_port": serial_port,
        "baudrate": baudrate,
        "started_at": started_at,
        "between_max_wait_s": between_max_wait_s,
        "between_min_wait_s": between_min_wait_s,
        "quiet_window_s": quiet_window_s,
        "post_wait_s": post_wait_s,
        "send_loglevel4": send_loglevel4,
        "listenai_play": str(listenai_play),
        "playback_output": playback_output,
        "between_wait_result": between_wait_result,
        "serial_bytes": len(chunks),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def cmd_tts(args: argparse.Namespace) -> int:
    out_path = Path(args.out).expanduser().resolve()
    run_tts(args.text, out_path, args.voice, args.rate)
    print(out_path)
    return 0


def cmd_tts_cache(args: argparse.Namespace) -> int:
    out_path, cached = ensure_cached_tts(
        text=args.text,
        voice=args.voice,
        rate=args.rate,
        label=args.label or "tts",
    )
    print(json.dumps({"path": str(out_path), "cached": cached}, ensure_ascii=False, indent=2))
    return 0


def cmd_probe_play(args: argparse.Namespace) -> int:
    audio_file = Path(args.audio_file).expanduser().resolve()
    result_dir = Path(args.result_dir).expanduser().resolve()
    meta = capture_sequence(
        audio_files=[audio_file],
        device_key=args.device_key,
        serial_port=args.serial_port,
        baudrate=args.baudrate,
        result_dir=result_dir,
        between_max_wait_s=0.0,
        between_min_wait_s=0.0,
        quiet_window_s=0.0,
        post_wait_s=args.post_wait_s,
        send_loglevel4=args.send_loglevel4,
        update_play_tool=args.update_play_tool,
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


def cmd_probe_sequence(args: argparse.Namespace) -> int:
    audio_files = [Path(item).expanduser().resolve() for item in args.audio_files]
    result_dir = Path(args.result_dir).expanduser().resolve()
    meta = capture_sequence(
        audio_files=audio_files,
        device_key=args.device_key,
        serial_port=args.serial_port,
        baudrate=args.baudrate,
        result_dir=result_dir,
        between_max_wait_s=args.between_max_wait_s,
        between_min_wait_s=args.between_min_wait_s,
        quiet_window_s=args.quiet_window_s,
        post_wait_s=args.post_wait_s,
        send_loglevel4=args.send_loglevel4,
        update_play_tool=args.update_play_tool,
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Small helper for CSK5062 fan voice validation.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_tts = sub.add_parser("tts", help="Generate a wav file with local Windows TTS.")
    p_tts.add_argument("--text", required=True)
    p_tts.add_argument("--out", required=True)
    p_tts.add_argument("--voice", default="Microsoft Huihui Desktop")
    p_tts.add_argument("--rate", type=int, default=0)
    p_tts.set_defaults(func=cmd_tts)

    p_cache = sub.add_parser("tts-cache", help="Generate or reuse a cached wav file.")
    p_cache.add_argument("--text", required=True)
    p_cache.add_argument("--label", default="tts")
    p_cache.add_argument("--voice", default="Microsoft Huihui Desktop")
    p_cache.add_argument("--rate", type=int, default=0)
    p_cache.set_defaults(func=cmd_tts_cache)

    p_probe = sub.add_parser("probe-play", help="Play an audio file and capture serial logs.")
    p_probe.add_argument("--audio-file", required=True)
    p_probe.add_argument("--device-key", required=True)
    p_probe.add_argument("--serial-port", default="COM38")
    p_probe.add_argument("--baudrate", type=int, default=115200)
    p_probe.add_argument("--result-dir", required=True)
    p_probe.add_argument("--post-wait-s", type=float, default=4.0)
    p_probe.add_argument("--send-loglevel4", action="store_true")
    p_probe.add_argument("--update-play-tool", action="store_true")
    p_probe.set_defaults(func=cmd_probe_play)

    p_seq = sub.add_parser("probe-sequence", help="Play multiple audio files in order and capture serial logs.")
    p_seq.add_argument("--audio-files", nargs="+", required=True)
    p_seq.add_argument("--device-key", required=True)
    p_seq.add_argument("--serial-port", default="COM38")
    p_seq.add_argument("--baudrate", type=int, default=115200)
    p_seq.add_argument("--result-dir", required=True)
    p_seq.add_argument("--between-max-wait-s", type=float, default=4.5)
    p_seq.add_argument("--between-min-wait-s", type=float, default=0.8)
    p_seq.add_argument("--quiet-window-s", type=float, default=0.6)
    p_seq.add_argument("--post-wait-s", type=float, default=4.0)
    p_seq.add_argument("--send-loglevel4", action="store_true")
    p_seq.add_argument("--update-play-tool", action="store_true")
    p_seq.set_defaults(func=cmd_probe_sequence)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
