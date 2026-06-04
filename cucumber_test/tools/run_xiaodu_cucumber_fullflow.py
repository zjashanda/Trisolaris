#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURE = ROOT / "cucumber_test" / "runtime" / "features" / "xiaodu_formal_fullflow.feature"
GENERATOR = ROOT / "cucumber_test" / "tools" / "generate_xiaodu_formal_feature.py"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Xiaodu 5062 formal fullflow through Cucumber/behave.")
    parser.add_argument("--log-port", default=os.environ.get("TRISOLARIS_LOG_PORT", "/dev/ttyACM0"))
    parser.add_argument("--proto-port", default=os.environ.get("TRISOLARIS_PROTO_PORT", "/dev/ttyACM2"))
    parser.add_argument("--ctrl-port", default=os.environ.get("TRISOLARIS_CTRL_PORT", "/dev/ttyACM4"))
    parser.add_argument("--burn-port", default=os.environ.get("TRISOLARIS_BURN_PORT", ""))
    parser.add_argument("--device-key", default=os.environ.get("TRISOLARIS_DEVICE_KEY", "VID_8765&PID_5678:USB_0_4_3_1_0"))
    parser.add_argument("--pre-burn-wait-ms", default=os.environ.get("TRISOLARIS_PRE_BURN_WAIT_MS", "6000"))
    parser.add_argument("--tag", default="xiaodu_cucumber_formal")
    parser.add_argument("--reuse-fullflow", action="store_true", help="Reuse an existing formal_fullflow_meta.json in the report dir if present.")
    parser.add_argument("--reuse-formal-meta", type=Path, help="Copy and reuse an existing formal_fullflow_meta.json instead of running the inner formal suite again.")
    args = parser.parse_args()

    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.tag}"
    report_dir = ROOT / "cucumber_test" / "debug" / "reports" / run_id
    evidence_dir = ROOT / "cucumber_test" / "debug" / "evidence" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    gen = subprocess.run([sys.executable, str(GENERATOR)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (report_dir / "feature_generate.log").write_text(gen.stdout + f"\nRC={gen.returncode}\n", encoding="utf-8")
    if gen.returncode != 0:
        print(gen.stdout, file=sys.stderr)
        return gen.returncode

    behave_json = report_dir / "cucumber.json"
    plain_log = report_dir / "behave_plain.txt"
    formal_meta = report_dir / "formal_fullflow_meta.json"
    if args.reuse_formal_meta:
        if not args.reuse_formal_meta.exists():
            print(f"reuse formal meta not found: {args.reuse_formal_meta}", file=sys.stderr)
            return 2
        shutil.copy2(args.reuse_formal_meta, formal_meta)
        args.reuse_fullflow = True
    inner_tag = f"{args.tag}_inner_formal"
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "TRISOLARIS_CUCUMBER_RUN_ID": run_id,
        "TRISOLARIS_CUCUMBER_REPORT_DIR": str(report_dir),
        "TRISOLARIS_CUCUMBER_EVIDENCE_DIR": str(evidence_dir),
        "TRISOLARIS_CUCUMBER_FULLFLOW_META": str(formal_meta),
        "TRISOLARIS_CUCUMBER_INNER_TAG": inner_tag,
        "TRISOLARIS_LOG_PORT": args.log_port,
        "TRISOLARIS_PROTO_PORT": args.proto_port,
        "TRISOLARIS_CTRL_PORT": args.ctrl_port,
        "TRISOLARIS_DEVICE_KEY": args.device_key,
        "TRISOLARIS_PRE_BURN_WAIT_MS": str(args.pre_burn_wait_ms),
    }
    if args.burn_port:
        env["TRISOLARIS_BURN_PORT"] = args.burn_port
    if args.reuse_fullflow:
        env["TRISOLARIS_CUCUMBER_REUSE_FULLFLOW"] = "1"

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

    if not formal_meta.exists():
        print(f"formal meta missing; behave rc={completed.returncode}; log={rel(run_log)}", file=sys.stderr)
        return completed.returncode or 1

    convert_cmd = [
        sys.executable,
        "cucumber_test/tools/convert_xiaodu_cucumber_fullflow.py",
        "--behave-json",
        str(behave_json),
        "--formal-meta",
        str(formal_meta),
        "--out-dir",
        str(report_dir),
    ]
    convert = subprocess.run(convert_cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (report_dir / "convert.log").write_text("$ " + " ".join(convert_cmd) + "\n" + convert.stdout + f"\nRC={convert.returncode}\n", encoding="utf-8")

    meta = json.loads(formal_meta.read_text(encoding="utf-8"))
    run_meta = {
        "run_id": run_id,
        "behave_returncode": completed.returncode,
        "convert_returncode": convert.returncode,
        "feature": rel(FEATURE),
        "report_dir": rel(report_dir),
        "evidence_dir": rel(evidence_dir),
        "behave_json": rel(behave_json),
        "formal_meta": rel(formal_meta),
        "case_results": rel(report_dir / "case_results.json"),
        "suite_report": rel(report_dir / "suite_report.md"),
        "inner_suite_dir": meta.get("inner_suite_dir"),
        "aggregate_case_results": meta.get("aggregate_case_results"),
        "aggregate_report": meta.get("aggregate_report"),
    }
    (report_dir / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(run_meta, ensure_ascii=False, indent=2))

    # Cucumber scenario failures are test results, not infrastructure failures.
    return convert.returncode


if __name__ == "__main__":
    raise SystemExit(main())
