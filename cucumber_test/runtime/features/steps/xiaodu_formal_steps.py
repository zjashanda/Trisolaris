from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from behave import given, then, when

ROOT = Path(__file__).resolve().parents[4]
META_ENV = "TRISOLARIS_CUCUMBER_FULLFLOW_META"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def meta_path(context) -> Path:
    value = os.environ.get(META_ENV)
    if value:
        return Path(value).resolve()
    return context.report_dir / "formal_fullflow_meta.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def newest_matching(root: Path, pattern: str, before: set[Path] | None = None) -> Path | None:
    before = before or set()
    matches = [p for p in root.glob(pattern) if p not in before]
    if not matches:
        matches = list(root.glob(pattern))
    return max(matches, key=lambda p: p.stat().st_mtime) if matches else None


def case_results_from_meta(meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    path = ROOT / meta["aggregate_case_results"]
    payload = load_json(path)
    return {item["case_id"]: item for item in payload.get("case_results", [])}


def run_command(cmd: list[str], log_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(cmd) + "\n")
        fh.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert proc.stdout is not None
        lines: list[str] = []
        for line in proc.stdout:
            fh.write(line)
            fh.flush()
            print(line, end="", flush=True)
            lines.append(line)
        returncode = proc.wait()
    return subprocess.CompletedProcess(cmd, returncode, "".join(lines), None)


@given("当前小度正式 Cucumber 环境已准备")
def step_formal_env_ready(context):
    context.project_id = "csk5062_xiaodu_fan"
    context.fullflow_meta_path = meta_path(context)
    context.fullflow_meta_path.parent.mkdir(parents=True, exist_ok=True)


@when("通过 Cucumber 执行小度正式全集")
def step_run_xiaodu_formal_fullflow(context):
    if context.fullflow_meta_path.exists() and os.environ.get("TRISOLARIS_CUCUMBER_REUSE_FULLFLOW") == "1":
        return

    tag = os.environ.get("TRISOLARIS_CUCUMBER_INNER_TAG") or f"xiaodu5062_cucumber_inner_{context.run_id}"
    cmd = [
        sys.executable,
        "tools/suite/run_formal_suite.py",
        "--req-dir",
        "项目需求/CSK5062小度风扇需求",
        "--project",
        "csk5062_xiaodu_fan",
        "--execution-mode",
        "formal",
        "--tag",
        tag,
    ]
    for env_key, flag in [
        ("TRISOLARIS_LOG_PORT", "--log-port"),
        ("TRISOLARIS_PROTO_PORT", "--proto-port"),
        ("TRISOLARIS_CTRL_PORT", "--ctrl-port"),
        ("TRISOLARIS_BURN_PORT", "--burn-port"),
        ("TRISOLARIS_DEVICE_KEY", "--device-key"),
        ("TRISOLARIS_PRE_BURN_WAIT_MS", "--pre-burn-wait-ms"),
    ]:
        value = os.environ.get(env_key)
        if value:
            cmd.extend([flag, value])

    report_root = ROOT / "deliverables" / "formal_suite_runs"
    before = set(report_root.glob("*"))
    completed = run_command(cmd, context.report_dir / "inner_formal_suite.log", {**os.environ, "PYTHONUNBUFFERED": "1"})
    if completed.returncode != 0:
        raise AssertionError(f"正式全集执行命令失败 rc={completed.returncode}; log={rel(context.report_dir / 'inner_formal_suite.log')}")

    suite_dir: Path | None = None
    for line in reversed(completed.stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        candidate = Path(line)
        if candidate.exists() and candidate.is_dir():
            suite_dir = candidate.resolve()
            break
        candidate = ROOT / line
        if candidate.exists() and candidate.is_dir():
            suite_dir = candidate.resolve()
            break
    if suite_dir is None:
        suite_dir = newest_matching(report_root, f"*{tag}", before=before)
    if suite_dir is None:
        raise AssertionError("无法定位 inner formal suite 结果目录")

    suite_summary = load_json(suite_dir / "suite_summary.json")
    artifacts = suite_summary.get("artifacts") or {}
    aggregate_case_results = artifacts.get("aggregate_case_results")
    aggregate_report = artifacts.get("aggregate_report")
    if not aggregate_case_results:
        raise AssertionError(f"inner formal suite 未输出 aggregate_case_results: {rel(suite_dir)}")

    meta = {
        "run_id": context.run_id,
        "inner_tag": tag,
        "inner_suite_dir": rel(suite_dir),
        "inner_suite_summary": rel(suite_dir / "suite_summary.json"),
        "inner_suite_report": rel(suite_dir / "suite_report.md"),
        "aggregate_case_results": aggregate_case_results,
        "aggregate_report": aggregate_report,
        "counts": suite_summary.get("counts") or {},
        "nonpass": suite_summary.get("nonpass") or [],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    write_json(context.fullflow_meta_path, meta)


@then("正式聚合结果应包含 {expected_count:d} 条用例")
def step_formal_count(context, expected_count):
    assert context.fullflow_meta_path.exists(), f"缺少正式全集 meta: {context.fullflow_meta_path}"
    meta = load_json(context.fullflow_meta_path)
    cases = case_results_from_meta(meta)
    actual = len(cases)
    assert actual == expected_count, f"正式聚合用例数不符: actual={actual}, expected={expected_count}"


@given("小度 Cucumber 正式全集结果已存在")
def step_formal_result_exists(context):
    assert context.fullflow_meta_path.exists(), f"缺少正式全集 meta: {context.fullflow_meta_path}"
    context.fullflow_meta = load_json(context.fullflow_meta_path)
    context.fullflow_cases = case_results_from_meta(context.fullflow_meta)


@then('正式用例 "{case_id}" 的实际状态应为 "{expected_status}"')
def step_formal_case_status(context, case_id, expected_status):
    item = context.fullflow_cases.get(case_id)
    assert item is not None, f"正式聚合结果缺少用例: {case_id}"
    actual = item.get("status")
    if actual != expected_status:
        evidence = item.get("evidence", [])
        evidence_text = ", ".join(evidence[:3]) if isinstance(evidence, list) else str(evidence)
        raise AssertionError(
            f"{case_id} 状态不符合期望: actual={actual}, expected={expected_status}; "
            f"summary={item.get('summary')}; evidence={evidence_text}"
        )
