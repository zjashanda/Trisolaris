#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FEATURE = ROOT / "cucumber_test" / "runtime" / "features" / "xiaodu_minimal.feature"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Xiaodu 5062 minimal Cucumber/behave validation.")
    parser.add_argument("--feature", type=Path, default=DEFAULT_FEATURE)
    parser.add_argument("--log-port", default=os.environ.get("TRISOLARIS_LOG_PORT", "/dev/ttyACM0"))
    parser.add_argument("--proto-port", default=os.environ.get("TRISOLARIS_PROTO_PORT", "/dev/ttyACM2"))
    parser.add_argument("--ctrl-port", default=os.environ.get("TRISOLARIS_CTRL_PORT", "/dev/ttyACM4"))
    parser.add_argument("--device-key", default=os.environ.get("TRISOLARIS_DEVICE_KEY", "VID_8765&PID_5678:USB_0_4_3_1_0"))
    parser.add_argument("--tag", default="xiaodu_cucumber_minimal")
    args = parser.parse_args()

    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.tag}"
    report_dir = ROOT / "cucumber_test" / "debug" / "reports" / run_id
    evidence_dir = ROOT / "cucumber_test" / "debug" / "evidence" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    behave_json = report_dir / "cucumber.json"
    plain_log = report_dir / "behave_plain.txt"
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "TRISOLARIS_CUCUMBER_RUN_ID": run_id,
        "TRISOLARIS_CUCUMBER_REPORT_DIR": str(report_dir),
        "TRISOLARIS_CUCUMBER_EVIDENCE_DIR": str(evidence_dir),
        "TRISOLARIS_LOG_PORT": args.log_port,
        "TRISOLARIS_PROTO_PORT": args.proto_port,
        "TRISOLARIS_CTRL_PORT": args.ctrl_port,
        "TRISOLARIS_DEVICE_KEY": args.device_key,
    }
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
        str(args.feature),
    ]
    run_log = report_dir / "run_command.log"
    with run_log.open("w", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(cmd) + "\n")
        fh.flush()
        completed = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        fh.write(completed.stdout)
        fh.write(f"\nRC={completed.returncode}\n")

    evidence_index = report_dir / "scenario_evidence_index.json"
    convert_cmd = [
        sys.executable,
        "cucumber_test/tools/convert_behave_json.py",
        "--behave-json",
        str(behave_json),
        "--evidence-index",
        str(evidence_index),
        "--out-dir",
        str(report_dir),
    ]
    convert_completed = subprocess.run(convert_cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (report_dir / "convert.log").write_text("$ " + " ".join(convert_cmd) + "\n" + convert_completed.stdout + f"\nRC={convert_completed.returncode}\n", encoding="utf-8")

    meta = {
        "run_id": run_id,
        "returncode": completed.returncode,
        "convert_returncode": convert_completed.returncode,
        "feature": rel(args.feature),
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
    if completed.returncode != 0:
        return completed.returncode
    return convert_completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
