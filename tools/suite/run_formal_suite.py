#!/usr/bin/env python3
"""Project-agnostic formal-suite dispatcher for Trisolaris.

The dispatcher owns common flow only: project detection, validation-pool
classification, phase execution, and final result collation. Project-specific
serial/protocol details stay in adapters or scripts referenced by profile JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "references" / "project-profiles"
SUITE_ROOT = ROOT / "deliverables" / "formal_suite_runs"


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sanitize(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return value or "suite"


def newest_matching(root: Path, pattern: str, before: set[Path] | None = None) -> Path | None:
    before = before or set()
    matches = [p for p in root.glob(pattern) if p not in before]
    if not matches:
        matches = list(root.glob(pattern))
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def counts_from_case_results(path: Path) -> dict[str, int]:
    payload = load_json(path)
    counts: dict[str, int] = {}
    for item in payload.get("case_results", []):
        status = item.get("status", "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    counts["TOTAL"] = sum(v for k, v in counts.items() if k != "TOTAL")
    return counts


def nonpass_from_case_results(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    return [item for item in payload.get("case_results", []) if item.get("status") != "PASS"]


@dataclass
class CommandResult:
    name: str
    cmd: list[str]
    returncode: int
    log_path: Path
    started_at: str
    finished_at: str
    stdout_tail: str


class CommandRunner:
    def __init__(self, suite_dir: Path, env: dict[str, str]) -> None:
        self.suite_dir = suite_dir
        self.env = env
        self.logs_dir = suite_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def run(self, name: str, cmd: list[str], *, allow_nonzero: bool = False) -> CommandResult:
        log_path = self.logs_dir / f"{len(list(self.logs_dir.glob('*.log'))) + 1:02d}_{sanitize(name)}.log"
        started_at = iso_now()
        print(f"[RUN] {name}: {' '.join(cmd)}", flush=True)
        tail_lines: list[str] = []
        with log_path.open("w", encoding="utf-8") as log:
            log.write(f"$ {' '.join(cmd)}\n")
            log.flush()
            proc = subprocess.Popen(
                cmd,
                cwd=ROOT,
                env={**os.environ, **self.env},
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
                tail_lines.append(line.rstrip("\n"))
                if len(tail_lines) > 80:
                    tail_lines.pop(0)
            returncode = proc.wait()
        finished_at = iso_now()
        result = CommandResult(name, cmd, returncode, log_path, started_at, finished_at, "\n".join(tail_lines))
        if returncode != 0 and not allow_nonzero:
            raise RuntimeError(f"phase {name} failed with returncode={returncode}, log={log_path}")
        return result


class ProfileRegistry:
    def __init__(self) -> None:
        self.profiles = [load_json(path) for path in sorted(PROFILE_DIR.glob("*.json"))]

    def detect(self, req_dir: Path, explicit_project: str | None = None) -> dict[str, Any] | None:
        if explicit_project:
            for profile in self.profiles:
                if profile.get("project_id") == explicit_project:
                    return profile
            raise RuntimeError(f"unknown project profile: {explicit_project}")
        req_dir = req_dir.resolve()
        files = [p.name for p in req_dir.iterdir() if p.is_file()] if req_dir.exists() else []
        haystack = " ".join([str(req_dir), *files]).lower()
        best: tuple[int, dict[str, Any]] | None = None
        for profile in self.profiles:
            detect = profile.get("detect", {})
            score = 0
            for keyword in detect.get("path_keywords", []):
                if keyword.lower() in haystack:
                    score += 3
            for filename in detect.get("required_any_files", []):
                if filename in files:
                    score += 4
            for keyword in detect.get("firmware_keywords", []):
                if keyword.lower() in haystack:
                    score += 2
            if score and (best is None or score > best[0]):
                best = (score, profile)
        return best[1] if best else None


def resolve_firmware(req_dir: Path, profile: dict[str, Any], explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser().resolve()
    for pattern in profile.get("firmware_globs", ["*.bin"]):
        matches = sorted(req_dir.glob(pattern))
        if matches:
            return matches[0].resolve()
    bins = sorted(req_dir.glob("*.bin"))
    return bins[0].resolve() if bins else None


def base_env(args: argparse.Namespace, req_dir: Path, firmware: Path | None) -> dict[str, str]:
    env = {
        "TRISOLARIS_REQ_DIR": str(req_dir),
        "PYTHONUNBUFFERED": "1",
    }
    if firmware:
        env["TRISOLARIS_FIRMWARE_BIN"] = str(firmware)
    for attr, key in [
        ("log_port", "TRISOLARIS_LOG_PORT"),
        ("proto_port", "TRISOLARIS_PROTO_PORT"),
        ("ctrl_port", "TRISOLARIS_CTRL_PORT"),
        ("burn_port", "TRISOLARIS_BURN_PORT"),
        ("device_key", "TRISOLARIS_DEVICE_KEY"),
        ("pre_burn_wait_ms", "TRISOLARIS_PRE_BURN_WAIT_MS"),
    ]:
        value = getattr(args, attr, None)
        if value is not None and str(value):
            env[key] = str(value)
    return env


def run_classify(runner: CommandRunner, profile: dict[str, Any], req_dir: Path, suite_dir: Path) -> Path | None:
    out = Path(profile.get("deliverable_root", "deliverables")) / "plan" / f"{stamp()}_formal_suite_模块化验证池匹配结果.md"
    result = runner.run(
        "validation_pool_classify",
        [
            "python3",
            "tools/pool/validation_pool.py",
            "classify",
            "--project-key",
            profile["project_id"],
            "--out",
            str(out),
            str(req_dir),
        ],
    )
    return out if out.exists() else None


def parse_printed_path(tail: str) -> Path | None:
    for line in reversed(tail.splitlines()):
        line = line.strip()
        if not line:
            continue
        path = Path(line)
        if path.exists():
            return path.resolve()
        candidate = ROOT / line
        if candidate.exists():
            return candidate.resolve()
    return None


def run_xiaodu_5062(args: argparse.Namespace, profile: dict[str, Any], req_dir: Path, firmware: Path | None, suite_dir: Path) -> dict[str, Any]:
    env = base_env(args, req_dir, firmware)
    if args.skip_burn:
        env["TRISOLARIS_SKIP_BURN"] = "1"
    runner = CommandRunner(suite_dir, env)
    phases: list[dict[str, Any]] = []
    classify_out = run_classify(runner, profile, req_dir, suite_dir)

    tag_base = sanitize(args.tag or f"{profile['project_id']}_formal_suite")
    report_root = ROOT / profile["deliverable_root"] / "reports"
    result_root = ROOT / profile["result_root"]
    result_root.mkdir(parents=True, exist_ok=True)

    env["TRISOLARIS_BUNDLE_TAG"] = f"{tag_base}_main_fullflow"
    main_result = runner.run("xiaodu_main_fullflow", ["python3", "tools/debug/run_post_restructure_fullflow.py"])
    phases.append(command_record(main_result))
    main_bundle = parse_printed_path(main_result.stdout_tail) or newest_matching(report_root, f"*{tag_base}_main_fullflow")
    if not main_bundle:
        raise RuntimeError("cannot locate xiaodu main fullflow bundle")
    main_case_results = main_bundle / "03_execution" / "case_results.json"

    env["TRISOLARIS_BUNDLE_TAG"] = f"{tag_base}_missing_nonreg"
    supplement_result = runner.run("xiaodu_missing_nonreg", ["python3", "tools/debug/run_missing_nonreg_cases.py"])
    phases.append(command_record(supplement_result))
    supplement_bundle = parse_printed_path(supplement_result.stdout_tail) or newest_matching(report_root, f"*{tag_base}_missing_nonreg")
    if not supplement_bundle:
        raise RuntimeError("cannot locate xiaodu missing-nonreg bundle")
    supplement_case_results = supplement_bundle / "03_execution" / "case_results.json"

    env["TRISOLARIS_BATCH_RESULT_ROOT"] = rel(result_root)
    voice_before = set(result_root.glob("*_remaining_voice_reg_batch_summary"))
    voice_result = runner.run("xiaodu_remaining_voice_reg", ["python3", "tools/debug/run_remaining_voice_reg_batch.py"])
    phases.append(command_record(voice_result))
    voice_summary_dir = newest_matching(result_root, "*_remaining_voice_reg_batch_summary", before=voice_before)
    if not voice_summary_dir:
        raise RuntimeError("cannot locate xiaodu voice registration summary")
    voice_summary = voice_summary_dir / "summary.json"

    env["TRISOLARIS_BUNDLE_TAG"] = f"{tag_base}_regcfg005_closure"
    closure_result = runner.run("xiaodu_regcfg005_closure", ["python3", "tools/debug/run_xiaodu_regcfg005_closure.py"])
    phases.append(command_record(closure_result))
    closure_bundle = parse_printed_path(closure_result.stdout_tail) or newest_matching(report_root, f"*{tag_base}_regcfg005_closure")
    if not closure_bundle:
        raise RuntimeError("cannot locate xiaodu REG-CFG-005 closure bundle")
    closure_case_results = closure_bundle / "03_execution" / "case_results.json"

    aggregate_tag = f"{tag_base}_formal_aggregate"
    aggregate_result = runner.run(
        "xiaodu_generate_72_aggregate",
        [
            "python3",
            "tools/debug/generate_full_formal_aggregate.py",
            "--main-case-results",
            rel(main_case_results),
            "--supplement-case-results",
            rel(supplement_case_results),
            "--voice-summary",
            rel(voice_summary),
            "--overlay-case-results",
            rel(closure_case_results),
            "--tag",
            aggregate_tag,
        ],
    )
    phases.append(command_record(aggregate_result))
    aggregate_dir = newest_matching(report_root, f"*{aggregate_tag}")
    if not aggregate_dir:
        raise RuntimeError("cannot locate xiaodu aggregate bundle")
    aggregate_case_results = aggregate_dir / "aggregate_case_results.json"
    aggregate_report = aggregate_dir / "aggregate_report.md"
    counts = counts_from_case_results(aggregate_case_results)
    nonpass = nonpass_from_case_results(aggregate_case_results)
    return {
        "project_id": profile["project_id"],
        "adapter": profile["adapter"],
        "req_dir": rel(req_dir),
        "firmware": rel(firmware) if firmware else None,
        "classification": rel(classify_out) if classify_out else None,
        "phases": phases,
        "artifacts": {
            "main_case_results": rel(main_case_results),
            "supplement_case_results": rel(supplement_case_results),
            "voice_summary": rel(voice_summary),
            "closure_case_results": rel(closure_case_results),
            "aggregate_case_results": rel(aggregate_case_results),
            "aggregate_report": rel(aggregate_report),
        },
        "counts": counts,
        "nonpass": summarize_nonpass(nonpass),
    }


def command_record(result: CommandResult) -> dict[str, Any]:
    return {
        "name": result.name,
        "cmd": result.cmd,
        "returncode": result.returncode,
        "log_path": rel(result.log_path),
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }


def summarize_nonpass(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summarized: list[dict[str, Any]] = []
    for item in items:
        evidence = item.get("evidence", [])
        if isinstance(evidence, str):
            evidence_out: Any = evidence
        else:
            evidence_out = evidence[:5]
        summarized.append(
            {
                "case_id": item.get("case_id"),
                "module": item.get("module"),
                "status": item.get("status"),
                "summary": item.get("summary") or item.get("title") or item.get("error"),
                "evidence": evidence_out,
            }
        )
    return summarized


def latest_summary_in_result_root(result_root: Path) -> Path | None:
    candidates = list(result_root.glob("*/summary.json"))
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def run_cucumber_smoke(args: argparse.Namespace, profile: dict[str, Any], req_dir: Path, firmware: Path | None, suite_dir: Path) -> dict[str, Any]:
    """Run the current executable Cucumber smoke subset through the suite entry.

    This mode is intentionally opt-in. It proves the Gherkin/step/result bridge
    without replacing the project's formal full-suite adapter.
    """
    env = base_env(args, req_dir, firmware)
    runner = CommandRunner(suite_dir, env)
    phases: list[dict[str, Any]] = []
    classify_out = run_classify(runner, profile, req_dir, suite_dir)
    tag_base = sanitize(args.tag or f"{profile['project_id']}_cucumber_smoke")
    report_root = ROOT / "cucumber_test" / "debug" / "reports"
    before_reports = set(report_root.glob("*"))

    if profile["adapter"] != "xiaodu-5062":
        raise RuntimeError(f"cucumber-smoke mode currently supports xiaodu-5062 only, got {profile['adapter']}")

    cmd = [
        "python3",
        "cucumber_test/tools/run_xiaodu_cucumber_minimal.py",
        "--tag",
        tag_base,
    ]
    for attr, flag in [
        ("log_port", "--log-port"),
        ("proto_port", "--proto-port"),
        ("ctrl_port", "--ctrl-port"),
        ("device_key", "--device-key"),
    ]:
        value = getattr(args, attr, None)
        if value:
            cmd.extend([flag, str(value)])
    result = runner.run("cucumber_xiaodu_minimal_smoke", cmd)
    phases.append(command_record(result))

    new_reports = [p for p in report_root.glob("*") if p not in before_reports and p.is_dir()]
    cucumber_dir = max(new_reports, key=lambda p: p.stat().st_mtime) if new_reports else newest_matching(report_root, f"*{tag_base}")
    if not cucumber_dir:
        raise RuntimeError("cannot locate cucumber smoke report directory")
    case_results = cucumber_dir / "case_results.json"
    suite_report = cucumber_dir / "suite_report.md"
    cucumber_json = cucumber_dir / "cucumber.json"
    evidence_index = cucumber_dir / "scenario_evidence_index.json"
    if not case_results.exists():
        raise RuntimeError(f"missing cucumber case results: {case_results}")

    counts = counts_from_case_results(case_results)
    nonpass = nonpass_from_case_results(case_results)
    return {
        "project_id": profile["project_id"],
        "adapter": profile["adapter"],
        "execution_mode": "cucumber-smoke",
        "req_dir": rel(req_dir),
        "firmware": rel(firmware) if firmware else None,
        "classification": rel(classify_out) if classify_out else None,
        "phases": phases,
        "artifacts": {
            "feature": "cucumber_test/runtime/features/xiaodu_minimal.feature",
            "cucumber_json": rel(cucumber_json),
            "cucumber_case_results": rel(case_results),
            "cucumber_suite_report": rel(suite_report),
            "cucumber_evidence_index": rel(evidence_index),
        },
        "counts": counts,
        "nonpass": summarize_nonpass(nonpass),
        "note": "Cucumber smoke 是可选验证模式，仅证明 Gherkin/step/硬件桥接；正式 72 条全集仍使用默认 formal 模式。",
    }


def run_cucumber_formal(args: argparse.Namespace, profile: dict[str, Any], req_dir: Path, firmware: Path | None, suite_dir: Path) -> dict[str, Any]:
    """Run the project formal fullflow with Cucumber as the top-level driver."""
    env = base_env(args, req_dir, firmware)
    runner = CommandRunner(suite_dir, env)
    phases: list[dict[str, Any]] = []
    classify_out = run_classify(runner, profile, req_dir, suite_dir)
    tag_base = sanitize(args.tag or f"{profile['project_id']}_cucumber_formal")
    report_root = ROOT / "cucumber_test" / "debug" / "reports"
    before_reports = set(report_root.glob("*"))

    if profile["adapter"] != "xiaodu-5062":
        raise RuntimeError(f"cucumber-formal mode currently supports xiaodu-5062 only, got {profile['adapter']}")

    cmd = [
        "python3",
        "cucumber_test/tools/run_xiaodu_cucumber_fullflow.py",
        "--tag",
        tag_base,
    ]
    for attr, flag in [
        ("log_port", "--log-port"),
        ("proto_port", "--proto-port"),
        ("ctrl_port", "--ctrl-port"),
        ("burn_port", "--burn-port"),
        ("device_key", "--device-key"),
        ("pre_burn_wait_ms", "--pre-burn-wait-ms"),
    ]:
        value = getattr(args, attr, None)
        if value:
            cmd.extend([flag, str(value)])
    result = runner.run("cucumber_xiaodu_formal_fullflow", cmd)
    phases.append(command_record(result))

    new_reports = [p for p in report_root.glob("*") if p not in before_reports and p.is_dir()]
    cucumber_dir = max(new_reports, key=lambda p: p.stat().st_mtime) if new_reports else newest_matching(report_root, f"*{tag_base}")
    if not cucumber_dir:
        raise RuntimeError("cannot locate cucumber formal report directory")
    case_results = cucumber_dir / "case_results.json"
    suite_report = cucumber_dir / "suite_report.md"
    cucumber_json = cucumber_dir / "cucumber.json"
    formal_meta = cucumber_dir / "formal_fullflow_meta.json"
    if not case_results.exists():
        raise RuntimeError(f"missing cucumber formal case results: {case_results}")

    payload = load_json(case_results)
    counts = payload.get("counts") or counts_from_case_results(case_results)
    cucumber_scenario_counts = payload.get("cucumber_scenario_counts") or {}
    nonpass = [item for item in payload.get("case_results", []) if item.get("status") != "PASS"]
    formal_meta_payload = load_json(formal_meta) if formal_meta.exists() else {}
    return {
        "project_id": profile["project_id"],
        "adapter": profile["adapter"],
        "execution_mode": "cucumber-formal",
        "req_dir": rel(req_dir),
        "firmware": rel(firmware) if firmware else None,
        "classification": rel(classify_out) if classify_out else None,
        "phases": phases,
        "artifacts": {
            "feature": "cucumber_test/runtime/features/xiaodu_formal_fullflow.feature",
            "cucumber_json": rel(cucumber_json),
            "cucumber_case_results": rel(case_results),
            "cucumber_suite_report": rel(suite_report),
            "formal_meta": rel(formal_meta),
            "inner_suite_dir": formal_meta_payload.get("inner_suite_dir"),
            "aggregate_case_results": formal_meta_payload.get("aggregate_case_results"),
            "aggregate_report": formal_meta_payload.get("aggregate_report"),
        },
        "counts": counts,
        "cucumber_scenario_counts": cucumber_scenario_counts,
        "nonpass": summarize_nonpass(nonpass),
        "note": "Cucumber formal 以 Feature/Examples 为顶层用例入口，step 调用已收敛的项目 runner/adapter；新增用例优先改 Feature，不改 step 执行逻辑。",
    }


def run_cucumber_native(args: argparse.Namespace, profile: dict[str, Any], req_dir: Path, firmware: Path | None, suite_dir: Path) -> dict[str, Any]:
    """Run Cucumber scenarios that directly drive hardware primitives.

    This mode does not call the legacy formal fullflow runner. Feature steps
    drive audio playback, serial capture, protocol injection and assertions
    through the Cucumber native step library.
    """
    env = base_env(args, req_dir, firmware)
    runner = CommandRunner(suite_dir, env)
    phases: list[dict[str, Any]] = []
    classify_out = run_classify(runner, profile, req_dir, suite_dir)
    tag_base = sanitize(args.tag or f"{profile['project_id']}_cucumber_native")
    report_root = ROOT / "cucumber_test" / "debug" / "reports"
    before_reports = set(report_root.glob("*"))

    if profile["adapter"] != "xiaodu-5062":
        raise RuntimeError(f"cucumber-native mode currently supports xiaodu-5062 only, got {profile['adapter']}")

    cmd = [
        "python3",
        "cucumber_test/tools/run_xiaodu_cucumber_native_core.py",
        "--tag",
        tag_base,
    ]
    for attr, flag in [
        ("log_port", "--log-port"),
        ("proto_port", "--proto-port"),
        ("ctrl_port", "--ctrl-port"),
        ("device_key", "--device-key"),
    ]:
        value = getattr(args, attr, None)
        if value:
            cmd.extend([flag, str(value)])
    # Behave returns non-zero when a requirement assertion fails. Keep running
    # the suite wrapper so FAIL can be reported as a validation result instead
    # of being collapsed into a dispatcher ERROR.
    result = runner.run("cucumber_xiaodu_native_core", cmd, allow_nonzero=True)
    phases.append(command_record(result))

    new_reports = [p for p in report_root.glob("*") if p not in before_reports and p.is_dir()]
    cucumber_dir = max(new_reports, key=lambda p: p.stat().st_mtime) if new_reports else newest_matching(report_root, f"*{tag_base}")
    if not cucumber_dir:
        raise RuntimeError("cannot locate cucumber native report directory")
    case_results = cucumber_dir / "case_results.json"
    suite_report = cucumber_dir / "suite_report.md"
    cucumber_json = cucumber_dir / "cucumber.json"
    evidence_index = cucumber_dir / "scenario_evidence_index.json"
    if not case_results.exists():
        raise RuntimeError(f"missing cucumber native case results: {case_results}")

    counts = counts_from_case_results(case_results)
    nonpass = nonpass_from_case_results(case_results)
    return {
        "project_id": profile["project_id"],
        "adapter": profile["adapter"],
        "execution_mode": "cucumber-native",
        "req_dir": rel(req_dir),
        "firmware": rel(firmware) if firmware else None,
        "classification": rel(classify_out) if classify_out else None,
        "phases": phases,
        "artifacts": {
            "feature": "cucumber_test/runtime/features/xiaodu_native_core.feature",
            "cucumber_json": rel(cucumber_json),
            "cucumber_case_results": rel(case_results),
            "cucumber_suite_report": rel(suite_report),
            "cucumber_evidence_index": rel(evidence_index),
        },
        "counts": counts,
        "nonpass": summarize_nonpass(nonpass),
        "note": "Cucumber native 由 Scenario step 直接驱动声卡、日志串口、协议串口和断言；当前覆盖小度核心链路，后续新增场景优先改 Feature/Examples 和通用 DSL。",
    }


def run_cucumber_all(args: argparse.Namespace, profile: dict[str, Any], req_dir: Path, firmware: Path | None, suite_dir: Path) -> dict[str, Any]:
    """Run all currently migrated Cucumber validation surfaces in one suite.

    Native scenarios run first to prove direct hardware execution. The formal
    Cucumber feature then drives the 72-case fullflow status matrix. The final
    PASS/FAIL/TODO/BLOCKED counts are the formal requirement counts, while the
    native counts remain attached as execution-coverage evidence.
    """
    if profile["adapter"] != "xiaodu-5062":
        raise RuntimeError(f"cucumber-all mode currently supports xiaodu-5062 only, got {profile['adapter']}")

    native_args = argparse.Namespace(**vars(args))
    native_args.tag = f"{sanitize(args.tag or profile['project_id'])}_native_core"
    native = run_cucumber_native(native_args, profile, req_dir, firmware, suite_dir)

    formal_args = argparse.Namespace(**vars(args))
    formal_args.tag = f"{sanitize(args.tag or profile['project_id'])}_formal_72"
    formal = run_cucumber_formal(formal_args, profile, req_dir, firmware, suite_dir)

    artifacts: dict[str, Any] = {}
    for key, value in (native.get("artifacts") or {}).items():
        artifacts[f"native_{key}"] = value
    for key, value in (formal.get("artifacts") or {}).items():
        artifacts[f"formal_{key}"] = value
    if native.get("classification"):
        artifacts["native_classification"] = native["classification"]
    if formal.get("classification"):
        artifacts["formal_classification"] = formal["classification"]

    return {
        "project_id": profile["project_id"],
        "adapter": profile["adapter"],
        "execution_mode": "cucumber-all",
        "req_dir": rel(req_dir),
        "firmware": rel(firmware) if firmware else None,
        "classification": formal.get("classification") or native.get("classification"),
        "phases": [*(native.get("phases") or []), *(formal.get("phases") or [])],
        "artifacts": artifacts,
        "counts": formal.get("counts") or {},
        "native_counts": native.get("counts") or {},
        "native_nonpass": native.get("nonpass") or [],
        "formal_cucumber_scenario_counts": formal.get("cucumber_scenario_counts") or {},
        "nonpass": formal.get("nonpass") or [],
        "note": (
            "Cucumber-all 先执行 native 场景，Scenario 直接驱动硬件原语；再执行 72 条正式 Cucumber Feature。"
            "最终需求统计以正式 72 条为准，native 场景作为直接硬件执行覆盖证据。"
        ),
    }


def run_script_pipeline(args: argparse.Namespace, profile: dict[str, Any], req_dir: Path, firmware: Path | None, suite_dir: Path) -> dict[str, Any]:
    env = base_env(args, req_dir, firmware)
    runner = CommandRunner(suite_dir, env)
    phases: list[dict[str, Any]] = []
    classify_out = run_classify(runner, profile, req_dir, suite_dir)
    result_root = ROOT / profile.get("result_root", "result")
    result_root.mkdir(parents=True, exist_ok=True)
    phase_summaries: list[dict[str, Any]] = []
    for stage in profile.get("stages", []):
        before = set(result_root.glob("*/summary.json"))
        cmd = [str(part) for part in stage["cmd"]]
        result = runner.run(stage["name"], cmd, allow_nonzero=bool(stage.get("allow_nonzero")))
        phases.append(command_record(result))
        after = set(result_root.glob("*/summary.json")) - before
        summary_path = max(after, key=lambda p: p.stat().st_mtime) if after else latest_summary_in_result_root(result_root)
        phase_summaries.append({"stage": stage["name"], "summary": rel(summary_path) if summary_path else None})
    return {
        "project_id": profile["project_id"],
        "adapter": profile["adapter"],
        "req_dir": rel(req_dir),
        "firmware": rel(firmware) if firmware else None,
        "classification": rel(classify_out) if classify_out else None,
        "phases": phases,
        "phase_summaries": phase_summaries,
        "counts": {},
        "nonpass": [],
        "note": "script-pipeline adapter 已统一执行项目阶段；项目最终口径由各阶段 summary/report 和项目收敛报告汇总。",
    }


def write_suite_report(suite_dir: Path, summary: dict[str, Any]) -> None:
    write_json(suite_dir / "suite_summary.json", summary)
    counts = summary.get("counts") or {}
    nonpass = summary.get("nonpass") or []
    lines = [
        "# Trisolaris 验证执行报告",
        "",
        f"- 项目：`{summary.get('project_id')}`",
        f"- Adapter：`{summary.get('adapter')}`",
        f"- 执行模式：`{summary.get('execution_mode', 'formal')}`",
        f"- 需求目录：`{summary.get('req_dir')}`",
        f"- 固件：`{summary.get('firmware')}`",
        f"- 结果目录：`{rel(suite_dir)}`",
    ]
    if counts:
        lines.append(
            f"- 统计：`PASS={counts.get('PASS', 0)} / FAIL={counts.get('FAIL', 0)} / TODO={counts.get('TODO', 0)} / BLOCKED={counts.get('BLOCKED', 0)} / TOTAL={counts.get('TOTAL', 0)}`"
        )
    native_counts = summary.get("native_counts") or {}
    if native_counts:
        lines.append(
            f"- Native Cucumber：`PASS={native_counts.get('PASS', 0)} / FAIL={native_counts.get('FAIL', 0)} / BLOCKED={native_counts.get('BLOCKED', 0)} / TOTAL={native_counts.get('TOTAL', 0)}`"
        )
    scenario_counts = summary.get("formal_cucumber_scenario_counts") or summary.get("cucumber_scenario_counts") or {}
    if scenario_counts:
        lines.append(
            f"- Formal Cucumber 场景：`passed={scenario_counts.get('passed', 0)} / failed={scenario_counts.get('failed', 0)} / blocked={scenario_counts.get('blocked', 0)} / total={scenario_counts.get('total', 0)}`"
        )
    lines.extend(["", "## 关键产物", ""])
    for key, value in (summary.get("artifacts") or {}).items():
        lines.append(f"- `{key}`：`{value}`")
    if summary.get("classification"):
        lines.append(f"- `classification`：`{summary['classification']}`")
    lines.extend(["", "## 非 PASS 项", ""])
    if nonpass:
        lines.extend(["| 用例ID | 状态 | 结论 |", "| --- | --- | --- |"])
        for item in nonpass:
            lines.append(f"| `{item.get('case_id')}` | `{item.get('status')}` | {item.get('summary')} |")
    else:
        lines.append("- 无")
    native_nonpass = summary.get("native_nonpass") or []
    if native_nonpass:
        lines.extend(["", "## Native Cucumber 非 PASS 项", ""])
        lines.extend(["| 用例ID | 状态 | 结论 |", "| --- | --- | --- |"])
        for item in native_nonpass:
            lines.append(f"| `{item.get('case_id')}` | `{item.get('status')}` | {item.get('summary') or item.get('error') or ''} |")
    lines.extend(["", "## 阶段日志", ""])
    for phase in summary.get("phases", []):
        lines.append(f"- `{phase['name']}` rc={phase['returncode']} log=`{phase['log_path']}`")
    (suite_dir / "suite_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def write_adapter_required(suite_dir: Path, req_dir: Path) -> dict[str, Any]:
    summary = {
        "project_id": "unknown",
        "adapter": None,
        "req_dir": rel(req_dir),
        "status": "ADAPTER_REQUIRED",
        "message": "未匹配到项目 profile。已完成输入识别门禁，但不能套用小度或好太太执行器；需新增 profile/adapter 后再跑正式全集。",
    }
    write_suite_report(suite_dir, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a project formal suite through a generic Trisolaris dispatcher.")
    parser.add_argument("--req-dir", required=True, type=Path)
    parser.add_argument("--project")
    parser.add_argument("--firmware-bin")
    parser.add_argument("--tag", default="formal_suite")
    parser.add_argument("--log-port")
    parser.add_argument("--proto-port")
    parser.add_argument("--ctrl-port")
    parser.add_argument("--burn-port")
    parser.add_argument("--device-key")
    parser.add_argument("--pre-burn-wait-ms", type=int, default=6000)
    parser.add_argument("--skip-burn", action="store_true")
    parser.add_argument(
        "--execution-mode",
        choices=["formal", "cucumber-smoke", "cucumber-formal", "cucumber-native", "cucumber-all"],
        default="formal",
        help="formal runs the project full-suite adapter; cucumber-smoke runs the Gherkin bridge smoke subset; cucumber-formal wraps the formal suite from Cucumber; cucumber-native drives hardware directly from Cucumber steps; cucumber-all runs native scenarios plus the 72-case Cucumber fullflow.",
    )
    args = parser.parse_args()

    req_dir = args.req_dir.expanduser().resolve()
    suite_dir = SUITE_ROOT / f"{stamp()}_{sanitize(args.tag)}"
    suite_dir.mkdir(parents=True, exist_ok=True)
    registry = ProfileRegistry()
    profile = registry.detect(req_dir, args.project)
    if not profile:
        summary = write_adapter_required(suite_dir, req_dir)
        write_json(suite_dir / "suite_summary.json", summary)
        print(suite_dir)
        return 2
    firmware = resolve_firmware(req_dir, profile, args.firmware_bin)
    try:
        if args.execution_mode == "cucumber-smoke":
            summary = run_cucumber_smoke(args, profile, req_dir, firmware, suite_dir)
        elif args.execution_mode == "cucumber-formal":
            summary = run_cucumber_formal(args, profile, req_dir, firmware, suite_dir)
        elif args.execution_mode == "cucumber-native":
            summary = run_cucumber_native(args, profile, req_dir, firmware, suite_dir)
        elif args.execution_mode == "cucumber-all":
            summary = run_cucumber_all(args, profile, req_dir, firmware, suite_dir)
        elif profile["adapter"] == "xiaodu-5062":
            summary = run_xiaodu_5062(args, profile, req_dir, firmware, suite_dir)
        elif profile["adapter"] == "script-pipeline":
            summary = run_script_pipeline(args, profile, req_dir, firmware, suite_dir)
        else:
            raise RuntimeError(f"unsupported adapter: {profile['adapter']}")
        summary["status"] = "DONE"
        summary["suite_dir"] = rel(suite_dir)
        write_suite_report(suite_dir, summary)
        print(suite_dir)
        return 0
    except Exception as exc:
        summary = {
            "status": "ERROR",
            "project_id": profile.get("project_id"),
            "adapter": profile.get("adapter"),
            "req_dir": rel(req_dir),
            "firmware": rel(firmware) if firmware else None,
            "suite_dir": rel(suite_dir),
            "error": str(exc),
        }
        write_suite_report(suite_dir, summary)
        print(f"ERROR: {exc}", file=sys.stderr)
        print(suite_dir)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
