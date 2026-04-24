#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

import comtypes
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
AUDIO_DIR = ROOT / "tools" / "audio"
if str(AUDIO_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIO_DIR))

from fan_validation_helper import ensure_cached_tts  # noqa: E402
from listenai_play_repo import resolve_listenai_play  # noqa: E402


RESULT_ROOT = ROOT / "result" / "csk3022_htt_clothes_airer"
DEFAULT_TEXT = "小好小好"
DEFAULT_SAMPLE_INTERVAL_S = 0.05
DEFAULT_POST_WAIT_S = 1.0


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


def scan_render_devices(play_script: Path) -> list[dict]:
    completed = run_command(
        [
            sys.executable,
            str(play_script),
            "scan",
            "--platform",
            "windows",
            "--direction",
            "Render",
            "--json",
        ]
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip() or "listenai-play scan failed")
    payload = json.loads(completed.stdout or "[]")
    if not isinstance(payload, list):
        raise RuntimeError("listenai-play scan returned invalid payload")
    return payload


def build_meter_map() -> dict[str, object]:
    warnings.filterwarnings("ignore")
    meter_map: dict[str, object] = {}
    for dev in AudioUtilities.GetAllDevices():
        name = dev.FriendlyName or ""
        if not dev.id.startswith("{0.0.0."):
            continue
        if "ListenAI Audio" not in name:
            continue
        raw = dev._dev.Activate(IAudioMeterInformation._iid_, comtypes.CLSCTX_ALL, None)
        meter_map[name] = raw.QueryInterface(IAudioMeterInformation)
    return meter_map


def make_target_list(render_devices: list[dict], include_default: bool) -> list[dict]:
    targets: list[dict] = []
    if include_default:
        targets.append(
            {
                "tag": "default",
                "device_key": None,
                "name": "default render device",
            }
        )
    for index, item in enumerate(render_devices, start=1):
        targets.append(
            {
                "tag": f"key_{index}",
                "device_key": item.get("device_key"),
                "name": item.get("name") or item.get("backend_target") or "",
                "backend_target": item.get("backend_target") or "",
                "endpoint_id": item.get("endpoint_id") or "",
            }
        )
    return targets


def play_and_sample(
    play_script: Path,
    target: dict,
    audio_file: Path,
    meters: dict[str, object],
    sample_interval_s: float,
    post_wait_s: float,
) -> dict:
    command = [
        sys.executable,
        str(play_script),
        "play",
        "--platform",
        "windows",
        "--audio-file",
        str(audio_file),
        "--skip-probe",
    ]
    if target.get("device_key"):
        command.extend(["--device-key", str(target["device_key"])])

    started_at = datetime.now().isoformat(timespec="seconds")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    max_peaks = {name: 0.0 for name in meters}
    samples: list[dict] = []
    t0 = time.perf_counter()
    while True:
        sample = {"t_s": round(time.perf_counter() - t0, 3)}
        for name, meter in meters.items():
            try:
                peak = float(meter.GetPeakValue())
            except Exception as exc:  # pragma: no cover - diagnostic path
                peak = None
                sample[f"{name}__error"] = repr(exc)
            sample[name] = peak
            if isinstance(peak, float) and peak > max_peaks[name]:
                max_peaks[name] = peak
        samples.append(sample)
        if process.poll() is not None:
            break
        time.sleep(sample_interval_s)

    if post_wait_s > 0:
        post_deadline = time.perf_counter() + post_wait_s
        while time.perf_counter() < post_deadline:
            sample = {"t_s": round(time.perf_counter() - t0, 3)}
            for name, meter in meters.items():
                try:
                    peak = float(meter.GetPeakValue())
                except Exception as exc:  # pragma: no cover - diagnostic path
                    peak = None
                    sample[f"{name}__error"] = repr(exc)
                sample[name] = peak
                if isinstance(peak, float) and peak > max_peaks[name]:
                    max_peaks[name] = peak
            samples.append(sample)
            time.sleep(sample_interval_s)

    stdout = process.stdout.read() if process.stdout else ""
    ended_at = datetime.now().isoformat(timespec="seconds")
    return {
        "tag": target["tag"],
        "device_key": target.get("device_key"),
        "target_name": target.get("name"),
        "backend_target": target.get("backend_target"),
        "endpoint_id": target.get("endpoint_id"),
        "started_at": started_at,
        "ended_at": ended_at,
        "audio_file": str(audio_file),
        "returncode": process.returncode,
        "stdout": stdout,
        "max_peaks": max_peaks,
        "samples": samples,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe ListenAI render endpoint activity with pycaw meters.")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="TTS text to play for the endpoint probe.")
    parser.add_argument(
        "--sample-interval-s",
        type=float,
        default=DEFAULT_SAMPLE_INTERVAL_S,
        help="Endpoint peak sampling interval in seconds.",
    )
    parser.add_argument(
        "--post-wait-s",
        type=float,
        default=DEFAULT_POST_WAIT_S,
        help="Extra sampling time after playback exits.",
    )
    parser.add_argument(
        "--include-default",
        action="store_true",
        help="Also probe the Windows default render device.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    play_script = resolve_listenai_play(update=False)
    render_devices = scan_render_devices(play_script)
    targets = make_target_list(render_devices, include_default=args.include_default)
    if not targets:
        raise RuntimeError("No render targets available for endpoint probe")

    audio_file, cached = ensure_cached_tts(
        text=args.text,
        voice="Microsoft Huihui Desktop",
        rate=0,
        label="listenai_endpoint_meter_probe",
    )
    meters = build_meter_map()
    if not meters:
        raise RuntimeError("No ListenAI render meters available")

    suite_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_listenai_endpoint_meter_probe"
    bundle_dir = RESULT_ROOT / suite_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict] = []
    for target in targets:
        result = play_and_sample(
            play_script=play_script,
            target=target,
            audio_file=audio_file,
            meters=meters,
            sample_interval_s=args.sample_interval_s,
            post_wait_s=args.post_wait_s,
        )
        runs.append(result)
        (bundle_dir / f"{target['tag']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    summary = {
        "suite_name": suite_name,
        "bundle_dir": str(bundle_dir),
        "text": args.text,
        "audio_file": str(audio_file),
        "cached": cached,
        "targets": targets,
        "runs": [
            {
                "tag": item["tag"],
                "device_key": item.get("device_key"),
                "target_name": item.get("target_name"),
                "returncode": item["returncode"],
                "max_peaks": item["max_peaks"],
            }
            for item in runs
        ],
    }
    (bundle_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    payload = json.dumps(summary, ensure_ascii=False, indent=2)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
