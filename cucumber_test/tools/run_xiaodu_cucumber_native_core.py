#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURE = ROOT / "cucumber_test" / "runtime" / "features" / "xiaodu_native_core.feature"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Xiaodu Cucumber-native hardware scenarios.")
    parser.add_argument("--log-port", default="/dev/ttyACM0")
    parser.add_argument("--proto-port", default="/dev/ttyACM2")
    parser.add_argument("--ctrl-port", default="/dev/ttyACM4")
    parser.add_argument("--device-key", default="VID_8765&PID_5678:USB_0_4_3_1_0")
    parser.add_argument("--tag", default="xiaodu_native_core")
    args = parser.parse_args()

    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.tag}"
    report_dir = ROOT / "cucumber_test" / "debug" / "reports" / run_id
    evidence_dir = ROOT / "cucumber_test" / "debug" / "evidence" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    behave_json = report_dir / "cucumber.json"
    plain_log = report_dir / "behave_plain.txt"

    env = {
        "PYTHONUNBUFFERED": "1",
        "TRISOLARIS_CUCUMBER_RUN_ID": run_id,
        "TRISOLARIS_CUCUMBER_REPORT_DIR": str(report_dir),
        "TRISOLARIS_CUCUMBER_EVIDENCE_DIR": str(evidence_dir),
        "TRISOLARIS_LOG_PORT": args.log_port,
        "TRISOLARIS_PROTO_PORT": args.proto_port,
        "TRISOLARIS_CTRL_PORT": args.ctrl_port,
        "TRISOLARIS_DEVICE_KEY": args.device_key,
    }
    import os
    env = {**os.environ, **env}
    cmd = [
        sys.executable,
        "-m",
        "behave",
        "--no-capture",
        "--no-capture-stderr",
        "--format",
        "json.pretty",
        "--outfile",
        str(behave_json),
        "--format",
        "plain",
        "--outfile",
        str(plain_log),
        str(FEATURE),
    ]
    run_log = report_dir / "run_command.log"
    with run_log.open("w", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(cmd) + "\n")
        fh.flush()
        completed = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        fh.write(completed.stdout)
        fh.write(f"\nRC={completed.returncode}\n")

    convert_cmd = [
        sys.executable,
        "cucumber_test/tools/convert_behave_json.py",
        "--behave-json",
        str(behave_json),
        "--evidence-index",
        str(report_dir / "scenario_evidence_index.json"),
        "--out-dir",
        str(report_dir),
    ]
    convert = subprocess.run(convert_cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (report_dir / "convert.log").write_text("$ " + " ".join(convert_cmd) + "\n" + convert.stdout + f"\nRC={convert.returncode}\n", encoding="utf-8")

    meta = {
        "run_id": run_id,
        "behave_returncode": completed.returncode,
        "convert_returncode": convert.returncode,
        "feature": rel(FEATURE),
        "report_dir": rel(report_dir),
        "evidence_dir": rel(evidence_dir),
        "behave_json": rel(behave_json),
        "case_results": rel(report_dir / "case_results.json"),
        "suite_report": rel(report_dir / "suite_report.md"),
        "plain_log": rel(plain_log),
        "run_log": rel(run_log),
    }
    (report_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return completed.returncode or convert.returncode


if __name__ == "__main__":
    raise SystemExit(main())
