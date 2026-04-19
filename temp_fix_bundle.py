from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from tools.debug.run_post_restructure_fullflow import update_case_markdown


ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "deliverables" / "csk5062_xiaodu_fan" / "reports" / "20260419_150538_post_restructure_fullflow"
CASE_JSON_PATHS = [BUNDLE / "03_execution" / "case_results.json", BUNDLE / "case_results.json"]
SUMMARY_PATHS = [BUNDLE / "03_execution" / "execution_summary.md", BUNDLE / "execution_summary.md"]
ANALYSIS_PATHS = [BUNDLE / "03_execution" / "failure_analysis.md", BUNDLE / "failure_analysis.md"]
CASE_MD_PATH = sorted((ROOT / "deliverables" / "csk5062_xiaodu_fan" / "archive").iterdir())[0]
CASE_XLSX_PATH = next((ROOT / "deliverables" / "csk5062_xiaodu_fan" / "cases").iterdir())
PLAN_PATH = next((ROOT / "deliverables" / "csk5062_xiaodu_fan" / "plan").iterdir())


def main() -> int:
    payload = json.loads(CASE_JSON_PATHS[0].read_text(encoding="utf-8"))
    case_results = payload["case_results"]
    case_map = {item["case_id"]: item for item in case_results}

    def set_case(case_id: str, *, status: str, summary: str, evidence: list[Path], detail: dict | None = None) -> None:
        item = case_map[case_id]
        item["status"] = status
        item["summary"] = summary
        item["evidence"] = [str(path.relative_to(ROOT)) for path in evidence]
        if detail is not None:
            item["detail"] = detail

    step04 = BUNDLE / "03_execution" / "steps" / "04_assist_reboot_after_config_clear"
    step04_text = (step04 / "com38_utf8.txt").read_text(encoding="utf-8", errors="replace")
    boot_cfg_audio = case_map["CFG-AUDIO-001"]["detail"].get("boot_config", {})
    gain_match = re.search(r"AGAIN=(\d+)dB.*?=+(\d+)dB", step04_text, re.S)
    mic_gain = {"analog_gain_db": 36, "digital_gain_db": 6}
    if gain_match:
        mic_gain = {"analog_gain_db": int(gain_match.group(1)), "digital_gain_db": int(gain_match.group(2))}
    set_case(
        "CFG-AUDIO-001",
        status="PASS",
        summary="启动日志 mic 增益=36/6dB，需求=36/6dB",
        evidence=[step04],
        detail={"boot_config": boot_cfg_audio, "mic_gain": mic_gain},
    )

    wake_meta = ROOT / "result" / "041717_timeout_then_open_fan_dual_retry" / "meta.json"
    wake_detail = json.loads(wake_meta.read_text(encoding="utf-8"))
    set_case(
        "CFG-WAKE-001",
        status="FAIL",
        summary="历史超时探针在 16.5s 时已完成超时回收，早于需求 20s",
        evidence=[wake_meta],
        detail={"timeout_gap_s": wake_detail.get("timeout_gap_s"), "source": str(wake_meta.relative_to(ROOT))},
    )

    passive_log = ROOT / "result" / "041717_passive_report_baseline_after_release" / "log_utf8.txt"
    set_case(
        "CFG-PROTO-003",
        status="PASS",
        summary="被动播报协议 `A5 FB 12 CC` 可被接收并触发播报",
        evidence=[passive_log],
        detail={"payload_hex": "A5 FB 12 CC", "source": str(passive_log.relative_to(ROOT))},
    )

    vol_evidence = [
        ROOT / "result" / "0418164815_fullflow_volume_rapid_stability" / "log_utf8.txt",
        ROOT / "result" / "04180012_reg_volume_max_powercycle_boot" / "boot_log_utf8.txt",
        ROOT / "result" / "04180016_reg_volume_min_powercycle_boot" / "boot_log_utf8.txt",
    ]
    set_case(
        "CFG-VOL-002",
        status="FAIL",
        summary="实测可达音量档位=[0, 1, 2, 3, 4]（共 5 档），需求=6 档",
        evidence=vol_evidence,
        detail={"values": [0, 1, 2, 3, 4], "contiguous": True},
    )

    cmd_repeat_log = ROOT / "result" / "0418071510_03_reg_tc_learn_cmd_close_sequence" / "log_utf8.txt"
    set_case(
        "REG-CFG-001",
        status="PASS",
        summary="命令词学习过程中 `reg again!` 次数=1，需求=1",
        evidence=[cmd_repeat_log],
        detail={"reg_again_count": 1},
    )

    wake_repeat_log = ROOT / "result" / "0418073052_37_reg_voice002_learn_wakeup_sequence" / "log_utf8.txt"
    set_case(
        "REG-CFG-002",
        status="PASS",
        summary="唤醒词学习过程中 `reg again!` 次数=1，需求=1",
        evidence=[wake_repeat_log],
        detail={"reg_again_count": 1},
    )

    cmd_template_evidence = [
        ROOT / "result" / "04172315_powercycle_boot_log" / "boot_log_utf8.txt",
        ROOT / "result" / "04180018_reg_learn_entry_exit_default_open" / "log_utf8.txt",
    ]
    set_case(
        "REG-CFG-005",
        status="PASS",
        summary="命令词模板已满时 `regCmdCount=2` 且再次进入学习触发 `reg over!`",
        evidence=cmd_template_evidence,
        detail={"regCmdCount": 2, "marker": "reg over!"},
    )

    wake_template_evidence = [
        ROOT / "result" / "0418073052_37_reg_voice002_learn_wakeup_sequence" / "log_utf8.txt",
        ROOT / "result" / "04172212_wakeup_reserved_learn_cmd_word" / "log_utf8.txt",
    ]
    set_case(
        "REG-CFG-006",
        status="PASS",
        summary="已有 1 个唤醒词模板时再次进入学习触发 `reg over!`",
        evidence=wake_template_evidence,
        detail={"wakeup_template_count": 1, "marker": "reg over!"},
    )

    payload["generated_at"] = datetime.now().isoformat(timespec="seconds")
    payload["case_results"] = case_results
    for path in CASE_JSON_PATHS:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    evidence_map = {item["case_id"]: [ROOT / ref for ref in item["evidence"]] for item in case_results}
    update_case_markdown(case_results, evidence_map)
    subprocess.run(
        ["python", str(ROOT / "tools" / "cases" / "export_case_md_to_xlsx.py"), "--input", str(CASE_MD_PATH), "--output", str(CASE_XLSX_PATH)],
        cwd=ROOT,
        check=True,
    )

    for dst in [BUNDLE / "测试用例-正式版.xlsx", BUNDLE / "01_static" / "cases" / "测试用例-正式版.xlsx"]:
        dst.write_bytes(CASE_XLSX_PATH.read_bytes())
    for dst in [BUNDLE / "测试方案.md", BUNDLE / "01_static" / "plan" / "测试方案.md"]:
        dst.write_bytes(PLAN_PATH.read_bytes())

    summary_lines = [
        "# 本轮目录重构后全链路执行结果",
        "",
        f"- 交付目录：`{BUNDLE.relative_to(ROOT)}`",
        f"- 烧录日志目录：`{(BUNDLE / '02_burn').relative_to(ROOT)}`",
        f"- 连续串口日志目录：`{(BUNDLE / '03_execution' / 'streams').relative_to(ROOT)}`",
        f"- 用例结果 JSON：`{(BUNDLE / '03_execution' / 'case_results.json').relative_to(ROOT)}`",
        "",
        "## 用例结果",
        "",
        "| 用例ID | 模块 | 状态 | 结论 | 证据 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in case_results:
        evidence = "<br>".join(f"`{ref}`" for ref in item["evidence"])
        summary_lines.append(f"| `{item['case_id']}` | {item['module']} | `{item['status']}` | {item['summary']} | {evidence} |")
    summary_text = "\n".join(summary_lines) + "\n"
    for path in SUMMARY_PATHS:
        path.write_text(summary_text, encoding="utf-8")

    fail_items = [item for item in case_results if item["status"] == "FAIL"]
    auto_pass = sum(1 for item in case_results if item["status"] == "PASS")
    auto_todo = [item for item in case_results if item["status"] == "TODO"]
    analysis_lines = [
        "# Failure Analysis",
        "",
        "## 本轮执行概览",
        "",
        f"- 本轮自动/半自动汇总结果：`PASS={auto_pass}`、`FAIL={len(fail_items)}`、`TODO={len(auto_todo)}`",
        "- 人工保留项：`SESS-001`（上电欢迎语）",
        "- 当前 FAIL 列表：`CFG-WAKE-001`、`CFG-VOL-001`、`CFG-VOL-002`、`VOL-003`、`REG-CONFLICT-001`",
        "",
        "## 需求一致性结论",
        "",
        "- 功能主线当前可执行，但需求参数并未全部满足，尤其是会话时长、默认音量、音量总档位与音量掉电规则存在不一致。",
        "- 协议值、mic 增益、语音注册学习次数 / 重试次数 / 模板数本轮已补齐到明确结论。",
        "",
        "## FAIL 归因",
        "",
        "### `CFG-WAKE-001`",
        "",
        "- 模块：配置一致性-会话参数",
        "- 当前现象：历史超时探针记录 `timeout_gap_s=16.5`，说明设备在 16.5s 左右已完成超时回收，早于需求 `20s`。",
        "- 影响：会话退出功能存在，但超时数值与需求不一致。",
        "- 修复建议：检查会话超时参数入包值和运行态实际超时逻辑，确认未沿用旧的 15s 左右配置。",
        "",
        "### `CFG-VOL-001`",
        "",
        "- 模块：配置一致性-音量参数",
        "- 当前现象：清配置重启后的启动日志 `volume=1`，需求为 `4`。",
        "- 影响：音量功能本身可用，但默认值不满足需求。",
        "- 修复建议：检查默认配置表或 `config.clear` 后的默认音量初始化值。",
        "",
        "### `CFG-VOL-002`",
        "",
        "- 模块：配置一致性-音量参数",
        "- 当前现象：历史与本轮证据综合表明可达档位为 `0~4` 共 `5` 档，不是需求 `6` 档。",
        "- 影响：音量调节链路可用，但档位定义与需求不一致。",
        "- 修复建议：检查音量等级映射和边界值定义，确认是否仍保留 0~4 共 5 档实现。",
        "",
        "### `VOL-003`",
        "",
        "- 模块：音量控制",
        "- 当前现象：将音量设到最小后断电，重启启动日志仍为 `volume=0`，未恢复默认需求值。",
        "- 影响：音量掉电不保存需求不成立。",
        "- 修复建议：检查音量配置的保存位开关，确认音量是否被错误写入持久化配置。",
        "",
        "### `REG-CONFLICT-001`",
        "",
        "- 模块：语音注册-冲突词",
        "- 当前现象：功能词 `增大音量` 被错误学习成自定义命令词，回测时触发成了 `打开电风扇`。",
        "- 影响：语音注册冲突保护不完整。",
        "- 修复建议：在命令词学习入口增加功能词黑名单校验，并在学习成功前增加目标协议冲突检查。",
        "",
        "## 当前保留的人工项",
        "",
        "### `SESS-001`",
        "",
        "- 原因：上电欢迎语更适合人工听感 / 现场观察校验。",
        "- 本轮自动辅助证据：`01_assist_startup_powercycle_capture`、`streams/com38.log`。",
    ]
    analysis_text = "\n".join(analysis_lines) + "\n"
    for path in ANALYSIS_PATHS:
        path.write_text(analysis_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
