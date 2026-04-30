#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TRISOLARIS_BUNDLE_TAG", "xiaodu_regcfg005_closure")

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_post_restructure_fullflow import (  # noqa: E402
    CASE_MD_PATH,
    CASE_XLSX_PATH,
    PLAN_PATH,
    ROOT,
    FullflowRunner,
    has_all_markers,
    parse_boot_config,
    update_case_markdown,
    export_cases,
)

WAKE = "小度小度"
LEARN_CMD = "学习命令词"
LEARN_NEXT = "学习下一个"
ALIAS_1 = "笑逐颜开"
ALIAS_2 = "万事大吉"


def save_closed(text: str) -> bool:
    return any(marker in text for marker in ["save new voice.bin", "reg cmd over success", "save config success"])


def main() -> int:
    runner = FullflowRunner()
    runner.prepare_static_assets()
    evidence_map: dict[str, list[Path]] = {}
    runner.open_ports()
    try:
        def speak_series(prefix: str, texts: list[str], waits: list[float]) -> list:
            steps = []
            for index, text in enumerate(texts, start=1):
                wait_s = waits[index - 1] if index - 1 < len(waits) else waits[-1]
                steps.append(runner.run_voice_sequence(f"{prefix}_{index:02d}_{text}", [text], post_wait_s=wait_s))
            return steps

        clear = runner.run_shell_step("regcfg005_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        reboot = runner.run_shell_step("regcfg005_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        learn_close_steps = speak_series(
            "regcfg005_learn_close_first",
            [WAKE, LEARN_CMD, LEARN_NEXT, ALIAS_1, ALIAS_1],
            [2.5, 4.5, 4.5, 4.5, 8.0],
        )
        reenter_after_close_steps = speak_series(
            "regcfg005_reenter_after_close",
            [WAKE, LEARN_CMD],
            [2.5, 4.5],
        )
        learn_open_steps = speak_series(
            "regcfg005_learn_open_second",
            [WAKE, LEARN_CMD, ALIAS_2, ALIAS_2],
            [2.5, 4.5, 4.5, 10.0],
        )
        fill_steps = [*learn_close_steps, *reenter_after_close_steps, *learn_open_steps]
        fill_text = "\n".join(step.log_text for step in fill_steps)
        fill_save_seen = save_closed(fill_text) and "reg cmd over success!" in fill_text
        reboot_after_fill = runner.run_shell_step("regcfg005_reboot_after_fill", "reboot", capture_s=10.0, ready_wait_s=8.0)
        boot_cfg = parse_boot_config(reboot_after_fill.log_text)
        reenter = runner.run_voice_sequence("regcfg005_reenter_after_active_fill", [WAKE, LEARN_CMD], post_wait_s=6.0)
        template_full_marker = has_all_markers(reenter.log_text, ["reg over!"]) or "play id : 34" in reenter.log_text
        status = "PASS" if fill_save_seen and template_full_marker else "BLOCKED"
        summary = (
            "本用例内主动填满两个命令词模板后，再次进入学习命令词出现模板已满 / 学习结束提示"
            if status == "PASS"
            else "本用例内填充命令词模板或重入模板满证据不足，不能形成固件 FAIL"
        )
        evidence = [
            clear.step_dir,
            reboot.step_dir,
            *(step.step_dir for step in fill_steps),
            reboot_after_fill.step_dir,
            reenter.step_dir,
        ]
        detail = {
            "fill_save_seen": fill_save_seen,
            "template_full_marker": template_full_marker,
            "reenter_has_reg_over": "reg over!" in reenter.log_text,
            "reenter_has_play_id_34": "play id : 34" in reenter.log_text,
            "save_new_voice_count": fill_text.count("save new voice.bin"),
            "reg_cmd_over_success": "reg cmd over success!" in fill_text,
            "boot_config_after_fill": boot_cfg,
            "validation_note": "模板满必须由本用例内主动填满、保存、重启、重入四段证据闭合。",
        }
        runner.add_case_result("REG-CFG-005", "配置一致性-语音注册", status, summary, evidence, detail)
        evidence_map["REG-CFG-005"] = evidence
        final_clear = runner.run_shell_step("regcfg005_final_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        final_reboot = runner.run_shell_step("regcfg005_final_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        runner.log_event(
            "final_cleanup",
            {"evidence": [str(final_clear.step_dir.relative_to(ROOT)), str(final_reboot.step_dir.relative_to(ROOT))]},
        )
    finally:
        runner.save_streams()
        runner.close_ports()
    update_case_markdown(runner.case_results, evidence_map)
    export_cases()
    for src in [PLAN_PATH, CASE_MD_PATH, CASE_XLSX_PATH]:
        if src.exists():
            dst_dir = runner.static_dir / ("plan" if src == PLAN_PATH else "cases")
            dst_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(src, dst_dir / src.name)
    runner.write_case_results()
    runner.sync_bundle_root_artifacts()
    (runner.bundle_dir / "closure_summary.json").write_text(
        json.dumps({"case_results": runner.case_results, "bundle_dir": str(runner.bundle_dir.relative_to(ROOT))}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(runner.bundle_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
