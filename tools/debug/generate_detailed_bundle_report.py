#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def find_requirement_md(bundle_dir: Path) -> Path:
    files = sorted((bundle_dir / "01_static" / "requirement").glob("*.md"))
    if not files:
        raise FileNotFoundError("未找到需求文档")
    return files[0]


def find_case_md(bundle_dir: Path) -> Path:
    files = sorted((bundle_dir / "01_static" / "cases").glob("*.md"))
    if not files:
        raise FileNotFoundError("未找到用例文档")
    return files[0]


def parse_requirement_text(text: str) -> dict[str, Any]:
    def expect(pattern: str, cast=str, default: Any = None) -> Any:
        match = re.search(pattern, text)
        if not match:
            return default
        value = match.group(1).strip()
        return cast(value) if cast is not str else value

    return {
        "project_name": expect(r"项目名称[:：]\s*([^\n]+)", default="未知项目"),
        "branch_name": expect(r"分支名称[:：]\s*([^\n]+)", default="未知分支"),
        "chip": expect(r"芯片型号[:：]\s*([^\n]+)", default="未知芯片"),
        "version": expect(r"固件版本[:：]\s*([^\n]+)", default="未知版本"),
        "wake_timeout_s": expect(r"唤醒时长[:：]\s*(\d+)s", int, 0),
        "volume_steps": expect(r"音量档位[:：]\s*(\d+)", int, 0),
        "default_volume": expect(r"初始化默认音量[:：]\s*(\d+)", int, 0),
        "mic_analog_gain_db": expect(r"mic模拟增益[:：]\s*(\d+)", int, 0),
        "mic_digital_gain_db": expect(r"mic数字增益[:：]\s*(\d+)", int, 0),
        "proto_baud": expect(r"协议串口[:：]\s*UART1、波特率(\d+)", int, 0),
        "log_baud": expect(r"日志串口[:：]\s*UART0、波特率(\d+)", int, 0),
        "wake_power_save": expect(r"唤醒词掉电保存[:：]\s*([^\n]+)", default="未知"),
        "volume_power_save": expect(r"音量掉电保存[:：]\s*([^\n]+)", default="未知"),
    }


def parse_case_markdown(path: Path) -> dict[str, dict[str, str]]:
    case_map: dict[str, dict[str, str]] = {}
    for line in read_text(path).splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line[1:-1].split("|")]
        if len(cells) != 10:
            continue
        case_id = cells[0].strip("`")
        case_map[case_id] = {
            "module": cells[1],
            "case_type": cells[2],
            "test_point": cells[3],
            "precondition": cells[4],
            "steps": cells[5],
            "main_assertion": cells[6],
            "aux_assertion": cells[7],
        }
    return case_map


def html_lines(text: str) -> list[str]:
    if not text:
        return []
    return [line.strip() for line in text.replace("<br>", "\n").splitlines() if line.strip()]


def load_case_results(bundle_dir: Path) -> list[dict[str, Any]]:
    path = bundle_dir / "03_execution" / "case_results.json"
    if not path.exists():
        return []
    return json.loads(read_text(path)).get("case_results", [])


def load_gate(bundle_dir: Path) -> dict[str, Any]:
    for path in [bundle_dir / "testability_gate.json", bundle_dir / "03_execution" / "testability_gate.json"]:
        if path.exists():
            return json.loads(read_text(path))
    return {}


def load_bundle_meta(bundle_dir: Path) -> dict[str, Any]:
    path = bundle_dir / "01_static" / "bundle_meta.json"
    if not path.exists():
        return {}
    return json.loads(read_text(path))


def firmware_name(bundle_dir: Path) -> str:
    bins = sorted((bundle_dir / "01_static" / "requirement").glob("*.bin"))
    return bins[0].name if bins else "未知固件"


def status_label(status: str) -> str:
    return {
        "PASS": "通过",
        "FAIL": "失败",
        "BLOCKED": "阻塞",
        "TODO": "待人工",
    }.get(status, status)


def extract_startup_gain_fragment(bundle_dir: Path) -> str:
    path = bundle_dir / "03_execution" / "steps" / "01_assist_startup_powercycle_capture" / "com38_utf8.txt"
    if not path.exists():
        return "未找到启动日志"
    text = read_text(path)
    match = re.search(r"AGAIN=(\d+)dB.*?=+(\d+)dB", text, re.S)
    if match:
        return f"{match.group(1)}/{match.group(2)}dB"
    line_match = re.search(r"AADC: AGAIN=.*", text)
    if line_match:
        return line_match.group(0).strip()
    return "未稳定提取到增益片段"


def summarize_fail_reason(case_id: str, item: dict[str, Any], req: dict[str, Any]) -> list[str]:
    detail = item.get("detail", {}) or {}
    if case_id == "CFG-VOL-001":
        actual = detail.get("boot_config", {}).get("volume", "missing")
        return [
            f"首次启动默认音量为 {actual}，与需求默认音量 {req.get('default_volume')} 不一致。",
            "优先检查默认配置表、config.clear 后的初始化值、以及首次上电配置恢复路径。",
        ]
    if case_id == "CFG-WAKE-001":
        return [
            f"从响应播报结束到 MODE=0 的实测超时约为 {detail.get('timeout_from_response_end_s', detail.get('measured_upper_bound_s'))}s，从唤醒到 TIME_OUT 约为 {detail.get('wake_to_timeout_s')}s，与需求 {req.get('wake_timeout_s')}s 不一致。",
            "优先检查唤醒超时配置值、超时状态机收口逻辑，以及 TIME_OUT / MODE=0 触发条件。",
        ]
    if case_id == "CFG-VOL-002":
        asc_levels = detail.get("asc_unique_levels") or detail.get("values")
        desc_levels = detail.get("desc_unique_levels")
        return [
            f"实测上行档位序列={asc_levels}，下行档位序列={desc_levels}，与需求档位数 {req.get('volume_steps')} 不一致。",
            "优先检查音量边界值、逐档映射表、最大/最小音量落点，以及运行时 mini player set vol 的档位换算。",
        ]
    if case_id == "CFG-PROTO-003":
        return [
            "被动播报协议未完整形成“接收协议 -> 触发播报 -> 播放结束”的闭环。",
            "优先检查 A5 FB 12 CC 的协议映射、资源绑定以及被动播报分支的播放收口逻辑。",
        ]
    if case_id == "REG-CONFLICT-001":
        return [
            "保留功能词冲突保护未生效，功能词被错误学习或回测时原始功能未保持。",
            "优先检查学习黑名单、保留词过滤规则以及学习后原始命令回归逻辑。",
        ]
    return [item.get("summary", "当前结果与需求不一致。"), "请结合对应证据目录继续定位。"]


def render_overview(case_results: list[dict[str, Any]]) -> list[str]:
    pass_count = sum(1 for item in case_results if item["status"] == "PASS")
    fail_count = sum(1 for item in case_results if item["status"] == "FAIL")
    blocked_count = sum(1 for item in case_results if item["status"] == "BLOCKED")
    todo_count = sum(1 for item in case_results if item["status"] == "TODO")
    return [
        f"- 已记录用例数：`{len(case_results)}`",
        f"- 通过：`{pass_count}`",
        f"- 失败：`{fail_count}`",
        f"- 阻塞：`{blocked_count}`",
        f"- 待人工：`{todo_count}`",
    ]


def add_case_detail(lines: list[str], item: dict[str, Any], meta: dict[str, str], title_status: str, req: dict[str, Any] | None = None) -> None:
    lines.extend(
        [
            f"### `{item['case_id']}` {meta.get('test_point', item.get('module', '未命名测试点'))}",
            "",
            f"- 结果：`{title_status}`",
            f"- 模块：`{item.get('module', meta.get('module', '未知模块'))}`",
            f"- 用例类型：`{meta.get('case_type', '未标注')}`",
        ]
    )

    preconditions = html_lines(meta.get("precondition", ""))
    if preconditions:
        lines.append("- 前置条件：")
        for line in preconditions:
            lines.append(f"  - {line}")

    lines.append("- 执行步骤：")
    for line in html_lines(meta.get("steps", "")) or ["详见执行证据目录。"]:
        lines.append(f"  - {line}")

    lines.append("- 功能断言：")
    for line in html_lines(meta.get("main_assertion", "")) or ["未在正式用例表中找到主断言。"]:
        lines.append(f"  - {line}")

    aux = html_lines(meta.get("aux_assertion", ""))
    if aux:
        lines.append("- 辅助断言：")
        for line in aux:
            lines.append(f"  - {line}")

    lines.append(f"- 实际结果：{item.get('summary', '无结果摘要')}")

    if req is not None and title_status == "失败":
        lines.append("- 可能原因：")
        for reason in summarize_fail_reason(item["case_id"], item, req):
            lines.append(f"  - {reason}")

    lines.append("- 测试证据：")
    for evidence in item.get("evidence", []):
        lines.append(f"  - `{evidence}`")
    lines.append("")


def build_report(bundle_dir: Path) -> str:
    req = parse_requirement_text(read_text(find_requirement_md(bundle_dir)))
    case_map = parse_case_markdown(find_case_md(bundle_dir))
    case_results = load_case_results(bundle_dir)
    gate = load_gate(bundle_dir)
    bundle_meta = load_bundle_meta(bundle_dir)
    ports = bundle_meta.get("ports", {}) if isinstance(bundle_meta, dict) else {}
    fw_name = firmware_name(bundle_dir)
    startup_gain_fragment = extract_startup_gain_fragment(bundle_dir)
    proto_exec = ports.get("proto", "unknown")
    log_exec = ports.get("log", "unknown")
    ctrl_exec = ports.get("ctrl", "unknown")
    burn_exec = ports.get("burn", "unknown")
    device_key = bundle_meta.get("device_key", "unknown")

    lines: list[str] = []
    lines.extend(
        [
            f"# {fw_name} 测试报告（详细）",
            "",
            "## 1. 测试对象",
            "",
            f"- 结果目录：`{rel(bundle_dir)}`",
            f"- 固件文件：`{fw_name}`",
            f"- 项目名称：`{req.get('project_name')}`",
            f"- 分支名称：`{req.get('branch_name')}`",
            f"- 芯片型号：`{req.get('chip')}`",
            f"- 需求文档版本字段：`{req.get('version')}`",
            f"- 执行平台：`{bundle_meta.get('platform', 'unknown')}`",
            f"- 播报声卡：`{device_key}`",
            "",
            "## 2. 当前需求基线",
            "",
            f"- 唤醒时长：`{req.get('wake_timeout_s')}s`",
            f"- 音量档位：`{req.get('volume_steps')}`",
            f"- 默认音量：`{req.get('default_volume')}`",
            f"- mic 增益：`{req.get('mic_analog_gain_db')}` / `{req.get('mic_digital_gain_db')}` dB",
            f"- 协议串口（需求）：`UART1 @ {req.get('proto_baud')}`",
            f"- 日志串口（需求）：`UART0 @ {req.get('log_baud')}`",
            f"- 本轮执行协议口：`{proto_exec}`",
            f"- 本轮执行日志口：`{log_exec}`",
            f"- 本轮执行控制 / boot 口：`{ctrl_exec}`",
            f"- 本轮执行烧录口：`{burn_exec}`",
            f"- 唤醒词掉电保存：`{req.get('wake_power_save')}`",
            f"- 音量掉电保存：`{req.get('volume_power_save')}`",
            "",
            "## 3. 本轮执行流程",
            "",
            "- 读取当前需求文档、测试方案与正式用例。",
            "- 烧录目标固件，并通过启动版本日志确认烧录闭环。",
            "- 每个固件执行前都先跑可测性门禁。",
            "- 只有门禁通过后才继续执行正式验证。",
            f"- 协议结论统一以 `{proto_exec}` 为准，`{log_exec}` 仅作为状态/日志辅助证据。",
            "",
            "## 4. 可测性门禁",
            "",
        ]
    )

    if gate:
        lines.extend(
            [
                "- 门禁是否执行：`是`",
                f"- 门禁结果：`{status_label('PASS' if gate.get('passed') else 'FAIL')}`",
                f"- 烧录后首次启动默认音量：`{gate.get('first_boot_config', {}).get('volume', 'missing')}`",
                f"- 启动观察窗 Running Config 次数：`{gate.get('startup_running_config_count', 0)}`",
                f"- 启动观察窗 RESET 次数：`{gate.get('startup_reset_count', 0)}`",
                f"- 待机观察窗 Running Config 次数：`{gate.get('idle_running_config_count', 0)}`",
                f"- 待机观察窗 RESET 次数：`{gate.get('idle_reset_count', 0)}`",
                f"- 门禁阶段算法报错次数：`{gate.get('algo_fail_count', 0)}`",
                f"- 默认唤醒 + 普通命令协议链路：`{gate.get('interaction_frames', [])}`",
            ]
        )
        if gate.get("reasons"):
            lines.append("- 门禁判定原因：")
            for reason in gate.get("reasons", []):
                lines.append(f"  - {reason}")
        else:
            lines.append("- 门禁结论：固件满足继续执行正式验证的最基本条件。")
    else:
        lines.append("- 门禁记录：未找到。")
    lines.append("")

    if gate and not gate.get("passed", True):
        lines.extend(
            [
                "## 5. 固件不可测原因",
                "",
                "- 当前固件不满足需求验证的最小前置条件，因此在门禁阶段即终止正式验证。",
                "- 可测固件的最低要求为：不上电循环重启、默认唤醒词可用、唤醒后普通命令可正常交互。",
                "- 在门禁问题修复前，继续执行后续 PASS / FAIL 判断都没有意义。",
                "",
                "## 6. 已执行范围",
                "",
            ]
        )
        lines.extend(render_overview(case_results))
        lines.extend(["", "## 7. 关键证据", ""])
        for path in [
            bundle_dir / "burn.log",
            bundle_dir / "com38.log",
            bundle_dir / "com36.log",
            bundle_dir / "testability_gate.json",
            bundle_dir / "03_execution" / "failure_analysis.md",
        ]:
            if path.exists():
                lines.append(f"- `{rel(path)}`")
        lines.append("")
        return "\n".join(lines)

    lines.extend(["## 5. 执行结果概览", ""])
    lines.extend(render_overview(case_results))
    lines.extend(
        [
            "",
            "## 6. 关键参数结论",
            "",
            f"- 默认音量按烧录后首次启动判定：实测 `{gate.get('first_boot_config', {}).get('volume', 'missing') if gate else 'missing'}`，需求 `{req.get('default_volume')}`",
        ]
    )
    wake_case = next((item for item in case_results if item["case_id"] == "CFG-WAKE-001"), None)
    if wake_case:
        detail = wake_case.get("detail", {}) or {}
        lines.append(
            f"- 唤醒超时探测：响应播报结束到 `MODE=0` 约 `{detail.get('timeout_from_response_end_s', detail.get('measured_upper_bound_s', 'missing'))}s`，"
            f"唤醒到 `TIME_OUT` 约 `{detail.get('wake_to_timeout_s', 'missing')}s`，需求 `{req.get('wake_timeout_s')}s`"
        )
    audio_case = next((item for item in case_results if item["case_id"] == "CFG-AUDIO-001"), None)
    if audio_case:
        lines.append(f"- mic 增益当前保持人工确认口径：{audio_case.get('summary', '')}")
        lines.append(f"- 启动日志增益片段：`{startup_gain_fragment}`")
    lines.append("")

    lines.extend(
        [
            "## 7. 用例结果总表",
            "",
            "| 用例ID | 模块 | 测试点 | 结果 | 当前结论 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in case_results:
        meta = case_map.get(item["case_id"], {})
        lines.append(
            f"| `{item['case_id']}` | {item.get('module', meta.get('module', '未知模块'))} | "
            f"{meta.get('test_point', '未命名测试点')} | `{status_label(item['status'])}` | {item.get('summary', '')} |"
        )
    lines.append("")

    pass_items = [item for item in case_results if item["status"] == "PASS"]
    fail_items = [item for item in case_results if item["status"] == "FAIL"]
    pending_items = [item for item in case_results if item["status"] in {"TODO", "BLOCKED"}]

    lines.extend(["## 8. 通过项详细结果", ""])
    if not pass_items:
        lines.extend(["- 本轮没有通过项。", ""])
    else:
        for item in pass_items:
            meta = case_map.get(item["case_id"], {})
            add_case_detail(lines, item, meta, "通过")

    lines.extend(["## 9. 失败项详细分析", ""])
    if not fail_items:
        lines.extend(["- 本轮没有失败项。", ""])
    else:
        for item in fail_items:
            meta = case_map.get(item["case_id"], {})
            add_case_detail(lines, item, meta, "失败", req=req)

    lines.extend(["## 10. 待人工 / 阻塞项", ""])
    if not pending_items:
        lines.extend(["- 本轮没有待人工或阻塞项。", ""])
    else:
        for item in pending_items:
            meta = case_map.get(item["case_id"], {})
            add_case_detail(lines, item, meta, status_label(item["status"]))

    lines.extend(["## 11. 关键证据", ""])
    for path in [
        bundle_dir / "03_execution" / "case_results.json",
        bundle_dir / "03_execution" / "failure_analysis.md",
        bundle_dir / "02_burn" / "burn.log",
        bundle_dir / "03_execution" / "streams" / "com38.log",
        bundle_dir / "03_execution" / "streams" / "com36.log",
        bundle_dir / "03_execution" / "testability_gate.json",
    ]:
        if path.exists():
            lines.append(f"- `{rel(path)}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="为单个结果目录生成中文详细测试报告")
    parser.add_argument("--bundle-dir", required=True, help="单次 fullflow 结果目录")
    parser.add_argument("--output", default="测试报告-详细.md", help="输出报告文件名")
    args = parser.parse_args()
    bundle_dir = Path(args.bundle_dir)
    if not bundle_dir.is_absolute():
        bundle_dir = (ROOT / bundle_dir).resolve()
    output_path = bundle_dir / args.output
    output_path.write_text(build_report(bundle_dir) + "\n", encoding="utf-8-sig")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
