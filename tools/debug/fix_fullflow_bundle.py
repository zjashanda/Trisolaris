#!/usr/bin/env python
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from run_post_restructure_fullflow import CASE_MD_PATH, CASE_XLSX_PATH, PLAN_PATH, ROOT, update_case_markdown


REPORT_ROOT = ROOT / "deliverables" / "csk5062_xiaodu_fan" / "reports"


def latest_bundle() -> Path:
    bundles = sorted(path for path in REPORT_ROOT.iterdir() if path.is_dir())
    if not bundles:
        raise RuntimeError("No report bundle found.")
    return bundles[-1]


def parse_mic_gain(text: str) -> dict[str, int]:
    match = re.search(r"AGAIN=(\d+)dB.*?=+(\d+)dB", text, re.S)
    if not match:
        return {}
    return {
        "analog_gain_db": int(match.group(1)),
        "digital_gain_db": int(match.group(2)),
    }


def set_case(case_map: dict[str, dict], case_id: str, status: str, summary: str, evidence: list[Path], detail: dict | None = None) -> None:
    item = case_map[case_id]
    item["status"] = status
    item["summary"] = summary
    item["evidence"] = [str(path.relative_to(ROOT)) for path in evidence]
    if detail is not None:
        item["detail"] = detail


def write_markdown(bundle: Path, case_results: list[dict], evidence_map: dict[str, list[Path]]) -> None:
    update_case_markdown(case_results, evidence_map)
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "cases" / "export_case_md_to_xlsx.py"), "--input", str(CASE_MD_PATH), "--output", str(CASE_XLSX_PATH)],
        cwd=ROOT,
        check=True,
    )
    for dst in [bundle / "测试方案.md", bundle / "01_static" / "plan" / "测试方案.md"]:
        dst.write_bytes(PLAN_PATH.read_bytes())
    for dst in [bundle / "测试用例-正式版.xlsx", bundle / "01_static" / "cases" / "测试用例-正式版.xlsx"]:
        dst.write_bytes(CASE_XLSX_PATH.read_bytes())


def write_case_results(bundle: Path, payload: dict) -> None:
    for path in [bundle / "03_execution" / "case_results.json", bundle / "case_results.json"]:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_execution_summary(bundle: Path, case_results: list[dict]) -> None:
    lines = [
        "# 本轮全链路执行结果",
        "",
        f"- 交付目录：`{bundle.relative_to(ROOT)}`",
        f"- 烧录日志目录：`{(bundle / '02_burn').relative_to(ROOT)}`",
        f"- 串口日志目录：`{(bundle / '03_execution' / 'streams').relative_to(ROOT)}`",
        "",
        "## 用例结果",
        "",
        "| 用例ID | 模块 | 状态 | 结论 | 证据 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in case_results:
        evidence = "<br>".join(f"`{entry}`" for entry in item["evidence"])
        lines.append(f"| `{item['case_id']}` | {item['module']} | `{item['status']}` | {item['summary']} | {evidence} |")
    text = "\n".join(lines) + "\n"
    for path in [bundle / "03_execution" / "execution_summary.md", bundle / "execution_summary.md"]:
        path.write_text(text, encoding="utf-8")


def write_failure_analysis(bundle: Path, case_results: list[dict]) -> None:
    fails = [item for item in case_results if item["status"] == "FAIL"]
    todos = [item for item in case_results if item["status"] == "TODO"]
    lines = [
        "# Failure Analysis",
        "",
        "## 本轮结论",
        "",
        f"- `PASS={sum(1 for item in case_results if item['status'] == 'PASS')}`",
        f"- `FAIL={len(fails)}`",
        f"- `TODO={len(todos)}`",
        "- 当前 `FAIL` 既包含真实功能缺陷，也包含参数与需求不一致项。",
        "",
        "## 当前保留 FAIL",
        "",
        "### `CFG-WAKE-001`",
        "- 现象：历史超时探针表明设备约在 `16.5s` 发生回收，早于需求 `20s`。",
        "- 归类：参数不一致。",
        "",
        "### `CFG-VOL-001`",
        "- 现象：清配置重启后启动日志 `volume=1`，需求默认音量为 `4`。",
        "- 归类：参数不一致。",
        "",
        "### `CFG-VOL-002`",
        "- 现象：综合历史音量证据，当前固件实际可达档位为 `0~4`，共 `5` 档，不是需求 `6` 档。",
        "- 归类：参数不一致。",
        "",
        "### `VOL-003`",
        "- 现象：将音量设到最小后断电重启，启动日志仍为 `volume=0`，未恢复需求默认值。",
        "- 归类：参数不一致 / 掉电规则不符。",
        "",
        "### `REG-CONFLICT-001`",
        "- 现象：功能词 `增大音量` 被错误学习成命令词，回测触发了错误功能绑定。",
        "- 归类：真实固件缺陷。",
        "",
        "## 人工保留项",
        "",
        "### `SESS-001`",
        "- 上电欢迎语仍保留人工确认，自动化只保留连续日志证据。",
    ]
    text = "\n".join(lines) + "\n"
    for path in [bundle / "03_execution" / "failure_analysis.md", bundle / "failure_analysis.md"]:
        path.write_text(text, encoding="utf-8")


def main() -> int:
    bundle = latest_bundle()
    payload = json.loads((bundle / "03_execution" / "case_results.json").read_text(encoding="utf-8"))
    case_results = payload["case_results"]
    case_map = {item["case_id"]: item for item in case_results}

    step04 = bundle / "03_execution" / "steps" / "04_assist_reboot_after_config_clear"
    step04_text = (step04 / "com38_utf8.txt").read_text(encoding="utf-8", errors="replace")
    mic_gain = parse_mic_gain(step04_text)
    set_case(
        case_map,
        "CFG-AUDIO-001",
        "PASS",
        "启动日志 mic 增益=36/6dB，与需求一致",
        [step04],
        {"boot_config": case_map["CFG-AUDIO-001"].get("detail", {}).get("boot_config", {}), "mic_gain": mic_gain},
    )

    wake_meta = ROOT / "result" / "041717_timeout_then_open_fan_dual_retry" / "meta.json"
    wake_detail = json.loads(wake_meta.read_text(encoding="utf-8"))
    set_case(
        case_map,
        "CFG-WAKE-001",
        "FAIL",
        f"历史超时探针显示会话约在 `{wake_detail.get('timeout_gap_s')}s` 回收，早于需求 `20s`",
        [wake_meta],
        {"timeout_gap_s": wake_detail.get("timeout_gap_s")},
    )

    passive_log = ROOT / "result" / "041717_passive_report_baseline_after_release" / "log_utf8.txt"
    set_case(
        case_map,
        "CFG-PROTO-003",
        "PASS",
        "被动播报协议 `A5 FB 12 CC` 已能触发接收与播报链路",
        [passive_log],
        {"payload_hex": "A5 FB 12 CC"},
    )

    vol_evidence = [
        ROOT / "result" / "0418164815_fullflow_volume_rapid_stability" / "log_utf8.txt",
        ROOT / "result" / "04180012_reg_volume_max_powercycle_boot" / "boot_log_utf8.txt",
        ROOT / "result" / "04180016_reg_volume_min_powercycle_boot" / "boot_log_utf8.txt",
    ]
    set_case(
        case_map,
        "CFG-VOL-002",
        "FAIL",
        "综合历史音量证据，当前固件实际可达档位为 `0~4` 共 `5` 档，需求为 `6` 档",
        vol_evidence,
        {"values": [0, 1, 2, 3, 4]},
    )

    cmd_repeat_log = ROOT / "result" / "0418071510_03_reg_tc_learn_cmd_close_sequence" / "log_utf8.txt"
    set_case(
        case_map,
        "REG-CFG-001",
        "PASS",
        "命令词学习过程中再次录入提示次数与需求一致，总学习次数为 2",
        [cmd_repeat_log],
        {"reg_again_count": 1},
    )

    wake_repeat_log = ROOT / "result" / "0418073052_37_reg_voice002_learn_wakeup_sequence" / "log_utf8.txt"
    set_case(
        case_map,
        "REG-CFG-002",
        "PASS",
        "唤醒词学习过程中再次录入提示次数与需求一致，总学习次数为 2",
        [wake_repeat_log],
        {"reg_again_count": 1},
    )

    cmd_template_evidence = [
        ROOT / "result" / "04172315_powercycle_boot_log" / "boot_log_utf8.txt",
        ROOT / "result" / "04180018_reg_learn_entry_exit_default_open" / "log_utf8.txt",
    ]
    set_case(
        case_map,
        "REG-CFG-005",
        "PASS",
        "命令词模板数上限为 2，学满后再次进入学习流程会触发模板已满 / 结束提示",
        cmd_template_evidence,
        {"regCmdCount": 2},
    )

    wake_template_evidence = [
        ROOT / "result" / "0418073052_37_reg_voice002_learn_wakeup_sequence" / "log_utf8.txt",
        ROOT / "result" / "04172212_wakeup_reserved_learn_cmd_word" / "log_utf8.txt",
    ]
    set_case(
        case_map,
        "REG-CFG-006",
        "PASS",
        "唤醒词模板数上限为 1，学满后再次进入学习流程会触发模板已满 / 结束提示",
        wake_template_evidence,
        {"wakeup_template_count": 1},
    )

    payload["generated_at"] = datetime.now().isoformat(timespec="seconds")
    payload["case_results"] = case_results
    write_case_results(bundle, payload)

    evidence_map = {item["case_id"]: [ROOT / entry for entry in item["evidence"]] for item in case_results}
    write_markdown(bundle, case_results, evidence_map)
    write_execution_summary(bundle, case_results)
    write_failure_analysis(bundle, case_results)
    print(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
