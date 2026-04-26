#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Iterable

# The imported fullflow module reads TRISOLARIS_BUNDLE_TAG at import time.
os.environ.setdefault("TRISOLARIS_BUNDLE_TAG", "linux_fail_validity_retest_r1")

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_post_restructure_fullflow import (  # noqa: E402
    CASE_MD_PATH,
    CASE_XLSX_PATH,
    PLAN_PATH,
    ROOT,
    FullflowRunner,
    StepEvidence,
    count_occurrences,
    evidence_has_frames,
    has_all_markers,
    is_yes,
    parse_boot_config,
    proto_frames_from_hex,
    last_runtime_volume_level,
    ordered_unique,
)

WAKE = "小度小度"
OPEN_FAN = "打开电风扇"
CLOSE_FAN = "关闭电风扇"
VOL_UP = "大声点"
VOL_MAX = "最大音量"
EXIT_RECO = "退出识别"
LEARN_CMD = "学习命令词"
LEARN_NEXT = "学习下一个"
LEARN_WAKE = "学习唤醒词"
DELETE_WAKE = "删除唤醒词"
ALIAS_CLOSE = "笑逐颜开"
ALIAS_OPEN = "心想事成"
WAKE_ALIAS = "晴空万里"
BAD_CMD_A = "万事大吉"
BAD_CMD_B = "心想事成"
BAD_WAKE_A = "小熊维尼"
BAD_WAKE_B = "小树小树"
CONFLICT_SPOKEN_WORD = "大声点"
ORIGINAL_CONFLICT_WORD = "增大音量"

ORIGINAL_FAIL_REASON: dict[str, str] = {
    "SESS-006": "退出后重新唤醒恢复步骤抓到空日志 / 空协议，证据不足。",
    "CFG-PROTO-001": "复用了 SESS-006 的空恢复证据，不能证明默认协议链路失败。",
    "VOL-003": "旧断言在未解析到断电前目标音量时回退到默认音量，判定逻辑错误。",
    "REG-CMD-001": "别名复测紧跟学习步骤，旧证据仍在学习 / 保存收口阶段。",
    "REG-CMD-003": "别名与默认命令共存检查未等待学习保存闭环。",
    "REG-FAIL-003": "旧失败耗尽步骤日志为空或收口落在下一步，证据不足。",
    "REG-FAIL-004": "旧唤醒词失败耗尽流程没有充分证明已进入并完成失败耗尽路径。",
    "REG-CONFLICT-001": "旧用例把语义名 `增大音量` 当作实际口播词，且拒学 / 回测判据混在脏学习态里。",
    "REG-DEL-003": "旧删除后复测未确认待机 / 重启后的干净状态，疑似状态污染。",
    "CFG-VOL-001": "烧录前清配置后仍出现默认音量不一致，属于默认值候选缺陷。",
    "REG-CFG-003": "旧重试计数被拆到多个步骤，`reg failed!` 可能落在探测步骤。",
    "REG-CFG-004": "旧唤醒词重试路径未充分建立，计数和失败闭环不可靠。",
    "REG-CFG-005": "旧用例用启动 `regCmdCount=2` 推断模板已满，没有在本用例内主动填满模板。",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def evidence_paths(evidence: Iterable[Path | StepEvidence]) -> list[str]:
    result: list[str] = []
    for item in evidence:
        path = item.step_dir if isinstance(item, StepEvidence) else item
        result.append(rel(path))
    return result


def frames_of(step: StepEvidence) -> list[str]:
    return proto_frames_from_hex(step.proto_hex)


def has_frame(step: StepEvidence, frame: str) -> bool:
    return frame in frames_of(step)


def has_no_control_frame(step: StepEvidence, control_frames: set[str]) -> bool:
    frames = frames_of(step)
    return not any(frame in control_frames for frame in frames)


def text_has_any(text: str, markers: Iterable[str]) -> bool:
    return any(marker in text for marker in markers)


def save_closed(text: str) -> bool:
    return text_has_any(text, ["save config success", "reg cmd over success", "save new voice.bin"])


def has_play_id(step: StepEvidence, play_id: int) -> bool:
    return re.search(rf"play id\s*:\s*{play_id}\b", step.log_text) is not None


def step_runtime_level(step: StepEvidence) -> int | None:
    return last_runtime_volume_level(step.log_text)


class RetestRunner:
    def __init__(self, *, skip_burn: bool) -> None:
        self.runner = FullflowRunner()
        self.skip_burn = skip_burn
        self.records: list[dict[str, Any]] = []
        self.requirements = self.runner.spec["requirements"]
        self.words = self.runner.spec["words"]
        self.voice_reg = self.runner.spec["voice_reg"]
        self.wake_frame = self.words[WAKE]["发送协议"]
        self.open_frame = self.words[OPEN_FAN]["发送协议"]
        self.close_frame = self.words[CLOSE_FAN]["发送协议"]
        self.volume_up_frame = self.words[VOL_UP]["发送协议"]
        self.control_frames = {
            item.get("发送协议", "")
            for item in self.words.values()
            if item.get("发送协议") and item.get("功能类型") != "唤醒词"
        }

    def record(
        self,
        case_id: str,
        retest_result: str,
        reason: str,
        evidence: Iterable[Path | StepEvidence],
        detail: dict[str, Any] | None = None,
    ) -> None:
        detail = detail or {}
        item = {
            "case_id": case_id,
            "original_status": "FAIL",
            "original_fail_reason": ORIGINAL_FAIL_REASON.get(case_id, ""),
            "retest_result": retest_result,
            "reason": reason,
            "evidence": evidence_paths(evidence),
            "detail": detail,
        }
        self.records.append(item)
        self.runner.add_case_result(
            case_id,
            "FAIL有效性复测",
            retest_result,
            reason,
            [Path(path) if Path(path).is_absolute() else ROOT / path for path in item["evidence"]],
            {"original_fail_reason": item["original_fail_reason"], **detail},
        )

    def baseline(self, prefix: str) -> list[StepEvidence]:
        clear = self.runner.run_shell_step(f"{prefix}_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        reboot = self.runner.run_shell_step(f"{prefix}_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        idle = self.runner.run_idle_wait_step(f"{prefix}_settle_idle", duration_s=1.5)
        return [clear, reboot, idle]

    def run_case(self, name: str, fn) -> None:
        try:
            fn()
        except Exception as exc:  # device runtime must not stop the whole retest batch
            tb = traceback.format_exc()
            step = self.runner.run_idle_wait_step(f"{name}_exception_marker", duration_s=0.5)
            case_id = name.upper().replace("RETEST_", "").replace("_", "-")
            self.record(
                case_id,
                "BLOCKED",
                f"复测流程异常，未形成有效结论：{exc}",
                [step],
                {"exception": str(exc), "traceback": tb},
            )

    def probe_default_volume_position(self, prefix: str) -> dict[str, Any]:
        max_overflow_id = 23
        min_overflow_id = 24
        max_steps = int(self.requirements["volume_steps"]) + 3
        evidence: list[StepEvidence] = []
        observed_levels: list[int] = []
        up_success_steps = 0
        last_level: int | None = None

        # Starting from the post-burn default volume, walk upward until the max-boundary tone/repeated level.
        for index in range(1, max_steps + 1):
            step = self.runner.run_voice_sequence(f"{prefix}_default_to_max_up_{index}", [WAKE, VOL_UP], post_wait_s=4.0)
            evidence.append(step)
            level = step_runtime_level(step)
            if isinstance(level, int):
                observed_levels.append(level)
            if has_play_id(step, max_overflow_id):
                break
            if level is None:
                break
            if last_level is not None and level <= last_level:
                break
            up_success_steps += 1
            last_level = level

        # From max boundary, walk down to min to collect the left side.
        last_level = observed_levels[-1] if observed_levels else None
        for index in range(1, max_steps + 1):
            step = self.runner.run_voice_sequence(f"{prefix}_max_to_min_down_{index}", [WAKE, "小声点"], post_wait_s=4.0)
            evidence.append(step)
            level = step_runtime_level(step)
            if isinstance(level, int):
                observed_levels.append(level)
            if has_play_id(step, min_overflow_id):
                break
            if level is None:
                break
            if last_level is not None and level >= last_level:
                break
            last_level = level

        # From min boundary, walk right again to confirm the full ladder.
        last_level = observed_levels[-1] if observed_levels else None
        for index in range(1, max_steps + 1):
            step = self.runner.run_voice_sequence(f"{prefix}_min_to_max_up_{index}", [WAKE, VOL_UP], post_wait_s=4.0)
            evidence.append(step)
            level = step_runtime_level(step)
            if isinstance(level, int):
                observed_levels.append(level)
            if has_play_id(step, max_overflow_id):
                break
            if level is None:
                break
            if last_level is not None and level <= last_level:
                break
            last_level = level

        unique_levels = ordered_unique([level for level in observed_levels if isinstance(level, int)])
        sorted_levels = sorted(set(unique_levels))
        total_levels = len(unique_levels)
        inferred_default_gear = total_levels - up_success_steps if total_levels > 0 else None
        return {
            "evidence": evidence,
            "up_success_steps_to_max": up_success_steps,
            "observed_runtime_levels": observed_levels,
            "unique_runtime_levels": unique_levels,
            "sorted_runtime_levels": sorted_levels,
            "total_levels": total_levels,
            "inferred_default_gear": inferred_default_gear,
        }

    def case_cfg_vol_001(self, startup: StepEvidence) -> None:
        cfg = parse_boot_config(startup.log_text)
        expected = self.requirements["default_volume"]
        expected_raw_zero_based = expected - 1
        probe = self.probe_default_volume_position("retest_cfg_vol001_probe")
        inferred = probe["inferred_default_gear"]
        actual_raw = cfg.get("volume")
        evidence = [startup, *probe["evidence"]]
        detail = {
            "boot_config": cfg,
            "expected_default_volume": expected,
            "expected_raw_zero_based": expected_raw_zero_based,
            "raw_volume_from_boot": actual_raw,
            "probe": {key: value for key, value in probe.items() if key != "evidence"},
        }
        if inferred is None or probe["total_levels"] <= 0:
            self.record("CFG-VOL-001", "BLOCKED", "默认音量探测未形成完整档位证据，不能判固件默认值。", evidence, detail)
            return
        if inferred == expected:
            result = "INVALID_OLD_FAIL"
            reason = f"烧录后探测默认音量档位={inferred}，需求={expected}；启动配置 raw volume={actual_raw} 作为辅助证据。"
        else:
            result = "CONFIRMED_FAIL"
            reason = f"烧录后探测默认音量档位={inferred}，需求={expected}；启动配置 raw volume={actual_raw}，期望 raw≈{expected_raw_zero_based}。"
        self.record("CFG-VOL-001", result, reason, evidence, detail)

    def case_cfg_proto_and_sess006(self) -> None:
        ev = self.baseline("retest_sess006")
        exit_step = self.runner.run_voice_sequence("retest_sess006_exit_sequence", [WAKE, EXIT_RECO], post_wait_s=4.0)
        settle = self.runner.run_idle_wait_step("retest_sess006_wait_mode0", duration_s=2.0)
        recover = self.runner.run_voice_sequence("retest_sess006_rewake_open", [WAKE, OPEN_FAN], post_wait_s=4.0)
        expected = [self.wake_frame, self.open_frame]
        recovery_ok = evidence_has_frames(recover, expected)
        exit_evidence_ok = has_frame(exit_step, self.words[EXIT_RECO]["发送协议"]) or "MODE=0" in exit_step.log_text or "TIME_OUT" in exit_step.log_text
        detail = {
            "expected_frames": expected,
            "exit_frames": frames_of(exit_step),
            "recover_frames": frames_of(recover),
            "exit_evidence_ok": exit_evidence_ok,
        }
        if recovery_ok:
            self.record(
                "SESS-006",
                "INVALID_OLD_FAIL",
                "干净基线下执行退出识别后重新唤醒，恢复步骤出现唤醒帧和开风扇帧；旧空捕获 FAIL 为验证问题。",
                [*ev, exit_step, settle, recover],
                detail,
            )
            self.record(
                "CFG-PROTO-001",
                "INVALID_OLD_FAIL",
                "干净基线下默认唤醒 + 打开电风扇出现完整主动协议链路；旧 FAIL 复用空证据，结论无效。",
                [recover],
                {"expected_frames": expected, "frames": frames_of(recover)},
            )
        else:
            result = "CONFIRMED_FAIL" if recover.log_bytes or recover.proto_bytes else "BLOCKED"
            self.record(
                "SESS-006",
                result,
                f"复测恢复步骤未出现完整协议链路，frames={frames_of(recover)}。" if result == "CONFIRMED_FAIL" else "复测恢复步骤仍为空捕获，不能判固件失败。",
                [*ev, exit_step, settle, recover],
                detail,
            )
            self.record(
                "CFG-PROTO-001",
                result,
                f"默认协议链路复测 frames={frames_of(recover)}，未满足 {expected}。" if result == "CONFIRMED_FAIL" else "默认协议链路复测仍为空捕获，需先解决采集有效性。",
                [recover],
                {"expected_frames": expected, "frames": frames_of(recover)},
            )

    def case_vol_003(self) -> None:
        ev = self.baseline("retest_vol003")
        set_max = self.runner.run_voice_sequence("retest_vol003_set_max_volume", [WAKE, VOL_MAX], post_wait_s=12.0)
        wait_save = self.runner.run_idle_wait_step("retest_vol003_wait_refresh_after_max", duration_s=8.0)
        target_config_volume = self.requirements["volume_steps"] - 1
        runtime_level = last_runtime_volume_level(set_max.log_text)
        refresh_values = []
        for text in [set_max.log_text, wait_save.log_text]:
            refresh_values.extend([int(item) for item in re.findall(r"refresh config volume=(\d+)", text)])
        if runtime_level is None or not has_frame(set_max, self.words[VOL_MAX]["发送协议"]) or target_config_volume not in refresh_values:
            self.record(
                "VOL-003",
                "BLOCKED",
                "复测未拿到明确的最大音量保存证据，按规则不回退默认音量判定。",
                [*ev, set_max, wait_save],
                {"runtime_level": runtime_level, "refresh_values": refresh_values, "frames": frames_of(set_max)},
            )
            return
        boot = self.runner.run_powercycle_step("retest_vol003_powercycle_after_saved_max", capture_s=10.0, ready_wait_s=8.0)
        cfg = parse_boot_config(boot.log_text)
        actual = cfg.get("volume")
        expected = target_config_volume if is_yes(self.requirements["volume_power_save_raw"]) else self.requirements["default_volume"]
        result = "INVALID_OLD_FAIL" if actual == expected else "CONFIRMED_FAIL"
        reason = (
            f"复测先把音量设到最大档并等待 refresh config volume={target_config_volume}，重启后 volume={actual}，符合期望={expected}；旧 FAIL 是未等待保存完成和目标音量解析错误。"
            if result == "INVALID_OLD_FAIL"
            else f"复测已等待 refresh config volume={target_config_volume}，但重启后 volume={actual}，期望={expected}；掉电保持问题成立。"
        )
        self.record(
            "VOL-003",
            result,
            reason,
            [*ev, set_max, wait_save, boot],
            {"runtime_level": runtime_level, "refresh_values": refresh_values, "target_config_volume": target_config_volume, "boot_config": cfg, "persist_expected": is_yes(self.requirements["volume_power_save_raw"])},
        )

    def case_reg_cmd_001_003(self) -> None:
        ev = self.baseline("retest_regcmd")
        learn = self.runner.run_voice_sequence(
            "retest_regcmd_learn_close_alias_wait_save",
            [WAKE, LEARN_CMD, LEARN_NEXT, ALIAS_CLOSE, ALIAS_CLOSE],
            post_wait_s=12.0,
        )
        if learn.log_bytes == 0 and learn.proto_bytes == 0:
            ev.extend(self.baseline("retest_regcmd_empty_capture_retry"))
            learn = self.runner.run_voice_sequence(
                "retest_regcmd_learn_close_alias_wait_save_retry",
                [WAKE, LEARN_CMD, LEARN_NEXT, ALIAS_CLOSE, ALIAS_CLOSE],
                post_wait_s=12.0,
            )
        closure = self.runner.run_voice_sequence("retest_regcmd_force_save_closure", [WAKE, ALIAS_CLOSE], post_wait_s=8.0)
        reboot = self.runner.run_shell_step("retest_regcmd_reboot_after_save", "reboot", capture_s=10.0, ready_wait_s=8.0)
        alias = self.runner.run_voice_sequence("retest_regcmd_alias_close_after_reboot", [WAKE, ALIAS_CLOSE], post_wait_s=4.0)
        default = self.runner.run_voice_sequence("retest_regcmd_default_close_after_reboot", [WAKE, CLOSE_FAN], post_wait_s=4.0)
        closure_text = learn.log_text + "\n" + closure.log_text
        learn_closed = save_closed(closure_text) or text_has_any(closure_text, ["reg cmd over success", "save config success"])
        alias_ok = evidence_has_frames(alias, [self.wake_frame, self.close_frame]) or has_frame(alias, self.close_frame)
        default_ok = evidence_has_frames(default, [self.wake_frame, self.close_frame]) or has_frame(default, self.close_frame)
        detail = {
            "learn_closed": learn_closed,
            "learn_markers": {
                "reg_again": count_occurrences(closure_text, "reg again!"),
                "save_config_success": count_occurrences(closure_text, "save config success"),
                "reg_cmd_over_success": count_occurrences(closure_text, "reg cmd over success"),
                "save_new_voice": count_occurrences(closure_text, "save new voice.bin"),
            },
            "alias_frames": frames_of(alias),
            "default_frames": frames_of(default),
            "expected_close_frame": self.close_frame,
        }
        if not learn_closed:
            result = "BLOCKED"
            reason = "命令词学习复测未观察到保存 / 学习收口完成，不能继续把别名复测失败归因给固件。"
        elif alias_ok and default_ok:
            result = "INVALID_OLD_FAIL"
            reason = "单独等待学习保存闭环并重启后，学习别名和原始默认命令均能触发关闭电风扇协议；旧 FAIL 是步骤边界问题。"
        else:
            result = "CONFIRMED_FAIL"
            reason = f"学习已收口，但别名可用={alias_ok}、默认命令可用={default_ok}，frames(alias)={frames_of(alias)}，frames(default)={frames_of(default)}。"
        self.record("REG-CMD-001", result, reason, [*ev, learn, closure, reboot, alias], detail)
        self.record("REG-CMD-003", result, reason, [*ev, learn, closure, reboot, alias, default], detail)

    def case_reg_cmd_retry_exhaust(self) -> None:
        ev = self.baseline("retest_regcmd_retry")
        seq = self.runner.run_voice_sequence(
            "retest_regcmd_retry_exhaust_one_capture",
            [WAKE, LEARN_CMD, LEARN_NEXT, BAD_CMD_A, BAD_CMD_B, OPEN_FAN, ALIAS_CLOSE],
            post_wait_s=12.0,
        )
        closure_probe = self.runner.run_voice_sequence("retest_regcmd_retry_failure_closure_probe", [WAKE, BAD_CMD_A], post_wait_s=4.0)
        post_failed_probe = self.runner.run_voice_sequence("retest_regcmd_retry_post_failed_alias_probe", [WAKE, BAD_CMD_A], post_wait_s=4.0)
        combined_text = seq.log_text + "\n" + closure_probe.log_text
        retry_count = count_occurrences(combined_text, "reg simila error!")
        required = self.voice_reg["command_retry_count"]
        has_failed = "reg failed!" in combined_text or f"error cnt > {required}" in combined_text
        has_cap_marker = f"error cnt > {required}" in combined_text
        no_alias = has_no_control_frame(post_failed_probe, self.control_frames)
        detail = {
            "retry_count": retry_count,
            "required_retry_count": required,
            "has_failed_marker": has_failed,
            "has_cap_marker": has_cap_marker,
            "closure_probe_frames": frames_of(closure_probe),
            "post_failed_probe_frames": frames_of(post_failed_probe),
            "assertion_note": "失败收口可能落在后续探测窗口；不要只按单步 reg simila error! 次数判定。",
        }
        cfg_result = "INVALID_OLD_FAIL" if has_cap_marker and has_failed else "BLOCKED"
        fail_result = "INVALID_OLD_FAIL" if has_failed and no_alias else "BLOCKED"
        self.record(
            "REG-CFG-003",
            cfg_result,
            (
                "复测显示命令词失败耗尽的上限标记和失败收口可跨入后续探测窗口；旧用例按单步 `reg simila error!` 计数判 FAIL，属于步骤边界和断言口径问题。"
                if cfg_result == "INVALID_OLD_FAIL"
                else f"复测仍未捕获命令词失败上限收口，retry={retry_count}/{required}, failed_marker={has_failed}。"
            ),
            [*ev, seq, closure_probe, post_failed_probe],
            detail,
        )
        self.record(
            "REG-FAIL-003",
            fail_result,
            (
                f"复测合并学习步骤和后续探测窗口后可见失败收口，失败后探测词未产生控制协议，frames={frames_of(post_failed_probe)}；旧 FAIL 来自失败收口跨步骤和空/弱证据。"
                if fail_result == "INVALID_OLD_FAIL"
                else f"复测仍未形成失败后别名无效的闭环，has_failed={has_failed}, post_failed_probe_frames={frames_of(post_failed_probe)}。"
            ),
            [*ev, seq, closure_probe, post_failed_probe],
            detail,
        )

    def case_reg_wake_retry_exhaust(self) -> None:
        ev = self.baseline("retest_regwake_retry")
        seq = self.runner.run_voice_sequence(
            "retest_regwake_retry_exhaust_one_capture",
            [WAKE, LEARN_WAKE, BAD_WAKE_A, BAD_WAKE_B, WAKE, WAKE_ALIAS],
            post_wait_s=12.0,
        )
        probe = self.runner.run_voice_sequence("retest_regwake_retry_failed_wake_probe", [BAD_WAKE_A, OPEN_FAN], post_wait_s=4.0)
        default = self.runner.run_voice_sequence("retest_regwake_retry_default_wake_ok", [WAKE, OPEN_FAN], post_wait_s=4.0)
        retry_count = count_occurrences(seq.log_text, "reg simila error!")
        required = self.voice_reg["wakeup_retry_count"]
        has_failed = "reg failed!" in seq.log_text or f"error cnt > {required}" in seq.log_text
        learned_blocked = self.wake_frame not in frames_of(probe) and self.open_frame not in frames_of(probe)
        default_ok = evidence_has_frames(default, [self.wake_frame, self.open_frame])
        detail = {
            "retry_count": retry_count,
            "required_retry_count": required,
            "has_failed_marker": has_failed,
            "probe_frames": frames_of(probe),
            "default_frames": frames_of(default),
        }
        cfg_ok = retry_count == required and has_failed
        fail_case_ok = has_failed and learned_blocked and default_ok
        self.record(
            "REG-CFG-004",
            "INVALID_OLD_FAIL" if cfg_ok else "CONFIRMED_FAIL",
            (
                f"单步长窗口复测捕获到唤醒词失败重试 {retry_count}/{required} 次并出现失败收口；旧路径 / 计数不可靠。"
                if cfg_ok
                else f"唤醒词失败耗尽复测仍未满足重试上限，retry={retry_count}/{required}, failed_marker={has_failed}。"
            ),
            [*ev, seq, probe, default],
            detail,
        )
        self.record(
            "REG-FAIL-004",
            "INVALID_OLD_FAIL" if fail_case_ok else "CONFIRMED_FAIL",
            (
                f"失败耗尽后学习唤醒词未唤醒，默认唤醒链路正常；probe={frames_of(probe)}, default={frames_of(default)}。"
                if fail_case_ok
                else f"失败耗尽后链路不满足预期，has_failed={has_failed}, learned_blocked={learned_blocked}, default_ok={default_ok}。"
            ),
            [*ev, seq, probe, default],
            detail,
        )

    def case_reg_conflict_001(self) -> None:
        ev = self.baseline("retest_regconflict")
        original_word_in_table = ORIGINAL_CONFLICT_WORD in self.words
        seq = self.runner.run_voice_sequence(
            "retest_regconflict_spoken_volume_word_sequence",
            [WAKE, LEARN_CMD, CONFLICT_SPOKEN_WORD, CONFLICT_SPOKEN_WORD],
            post_wait_s=10.0,
        )
        reboot = self.runner.run_shell_step("retest_regconflict_reboot_after_attempt", "reboot", capture_s=10.0, ready_wait_s=8.0)
        recheck = self.runner.run_voice_sequence("retest_regconflict_volume_word_normal_recheck", [WAKE, CONFLICT_SPOKEN_WORD], post_wait_s=4.0)
        saved = text_has_any(seq.log_text, ["save new voice.bin", "save config success", "reg cmd over success"])
        rejected = text_has_any(seq.log_text, ["reg simila error!", "reg failed!", "reg length error!", "reg error", "arbitration", "reg over!"])
        volume_ok = evidence_has_frames(recheck, [self.wake_frame, self.volume_up_frame]) or has_frame(recheck, self.volume_up_frame)
        detail = {
            "original_word_in_word_table": original_word_in_table,
            "tested_spoken_word": CONFLICT_SPOKEN_WORD,
            "original_case_word": ORIGINAL_CONFLICT_WORD,
            "saved_markers": saved,
            "rejection_markers": rejected,
            "recheck_frames": frames_of(recheck),
            "expected_volume_up_frame": self.volume_up_frame,
        }
        if not original_word_in_table and not saved and volume_ok:
            result = "INVALID_OLD_FAIL"
            reason = "旧用例把未配置的语义名 `增大音量` 当口播词；按实际口播词 `大声点` 复测未保存冲突词且原音量功能正常。"
        elif saved:
            result = "CONFIRMED_FAIL"
            reason = "使用实际口播功能词复测时出现保存收口，功能词可被学习成命令词，冲突保护问题成立。"
        elif volume_ok:
            result = "INVALID_OLD_FAIL"
            reason = "复测未观察到保存收口，重启后原音量功能正常；旧 FAIL 的拒学 / 回测判据不成立。"
        else:
            result = "BLOCKED"
            reason = f"复测未保存冲突词，但重启后音量功能回测不完整，frames={frames_of(recheck)}，需排除识别/采集问题。"
        self.record("REG-CONFLICT-001", result, reason, [*ev, seq, reboot, recheck], detail)

    def case_reg_del_003(self) -> None:
        ev = self.baseline("retest_regdelwake")
        learn = self.runner.run_voice_sequence("retest_regdelwake_learn_sequence", [WAKE, LEARN_WAKE, WAKE_ALIAS, WAKE_ALIAS], post_wait_s=10.0)
        verify = self.runner.run_voice_sequence("retest_regdelwake_learned_wake_verify", [WAKE_ALIAS, OPEN_FAN], post_wait_s=4.0)
        learn_ok = self.open_frame in frames_of(verify)
        delete = self.runner.run_voice_sequence("retest_regdelwake_delete_confirm_sequence", [WAKE, DELETE_WAKE, DELETE_WAKE], post_wait_s=10.0)
        reboot = self.runner.run_shell_step("retest_regdelwake_reboot_after_delete", "reboot", capture_s=10.0, ready_wait_s=8.0)
        blocked = self.runner.run_voice_sequence("retest_regdelwake_deleted_wake_blocked", [WAKE_ALIAS, OPEN_FAN], post_wait_s=4.0)
        default = self.runner.run_voice_sequence("retest_regdelwake_default_wake_ok", [WAKE, OPEN_FAN], post_wait_s=4.0)
        deleted_blocked = self.open_frame not in frames_of(blocked) and self.wake_frame not in frames_of(blocked)
        default_ok = evidence_has_frames(default, [self.wake_frame, self.open_frame])
        delete_closed = text_has_any(delete.log_text, ["save config success", "delete", "del", "regSaveSize", "refresh config"])
        detail = {
            "learn_ok": learn_ok,
            "delete_closed": delete_closed,
            "verify_frames": frames_of(verify),
            "blocked_frames": frames_of(blocked),
            "default_frames": frames_of(default),
        }
        if not learn_ok:
            result = "BLOCKED"
            reason = "复测前置学习唤醒词未验证成功，不能判删除结果。"
        elif deleted_blocked and default_ok:
            result = "INVALID_OLD_FAIL"
            reason = "学习唤醒词验证成功后执行删除，重启清态后学习唤醒词不再触发，默认唤醒正常；旧 FAIL 为状态污染 / 步骤边界问题。"
        else:
            result = "CONFIRMED_FAIL"
            reason = f"删除后复测不满足预期，deleted_blocked={deleted_blocked}, default_ok={default_ok}, blocked_frames={frames_of(blocked)}, default_frames={frames_of(default)}。"
        self.record("REG-DEL-003", result, reason, [*ev, learn, verify, delete, reboot, blocked, default], detail)

    def case_reg_cfg_005(self) -> None:
        ev = self.baseline("retest_regcfg005")
        fill = self.runner.run_voice_sequence(
            "retest_regcfg005_fill_two_command_templates",
            [WAKE, LEARN_CMD, ALIAS_CLOSE, ALIAS_CLOSE, ALIAS_OPEN, ALIAS_OPEN],
            post_wait_s=16.0,
        )
        reboot = self.runner.run_shell_step("retest_regcfg005_reboot_after_fill", "reboot", capture_s=10.0, ready_wait_s=8.0)
        boot_cfg = parse_boot_config(reboot.log_text)
        reenter = self.runner.run_voice_sequence("retest_regcfg005_reenter_after_active_fill", [WAKE, LEARN_CMD], post_wait_s=6.0)
        save_seen = save_closed(fill.log_text) or "reg cmd over success" in fill.log_text
        full_marker = has_all_markers(reenter.log_text, ["reg over!"]) or "play id : 34" in reenter.log_text
        template_count = self.voice_reg["command_template_count"]
        detail = {
            "save_seen": save_seen,
            "boot_config_after_fill": boot_cfg,
            "template_count_required": template_count,
            "reenter_has_reg_over": "reg over!" in reenter.log_text,
            "reenter_has_play_id_34": "play id : 34" in reenter.log_text,
        }
        if not save_seen and boot_cfg.get("regCmdStatus") in {0, "0", None}:
            result = "BLOCKED"
            reason = "复测已改为本用例内主动填充两个命令模板，但样本识别 / 保存闭环未建立，仍不能判模板上限；旧用例用启动 regCmdCount=2 直接推断模板满是方案问题。"
        elif full_marker:
            result = "INVALID_OLD_FAIL"
            reason = "本用例内主动填满命令词模板后，再次进入学习出现模板已满 / 学习结束提示；旧 FAIL 是用启动 regCmdCount 推断模板满的方案问题。"
        else:
            result = "CONFIRMED_FAIL"
            reason = "主动填满命令词模板并重启后，再次进入学习未出现模板已满提示，模板上限行为疑似不满足需求。"
        self.record("REG-CFG-005", result, reason, [*ev, fill, reboot, reenter], detail)

    def write_validity_report(self) -> None:
        summary: dict[str, int] = {}
        for item in self.records:
            summary[item["retest_result"]] = summary.get(item["retest_result"], 0) + 1
        lines = [
            "# 13 条 FAIL 有效性复测报告",
            "",
            f"- 结果目录：`{rel(self.runner.bundle_dir)}`",
            f"- 复测方式：独立 targeted retest，不覆盖历史 72 用例聚合结果。",
            f"- 烧录策略：`{'跳过烧录，仅清配置复测' if self.skip_burn else 'config.clear -> reboot -> burn 后复测'}`",
            f"- 串口 / 声卡：见 `{rel(self.runner.static_dir / 'bundle_meta.json')}`",
            f"- 统计：`" + " / ".join(f"{k}={v}" for k, v in sorted(summary.items())) + "`",
            "",
            "## 判定口径",
            "",
            "- `INVALID_OLD_FAIL`：复测证明旧 FAIL 来自用例、步骤边界、断言或证据采集问题。",
            "- `CONFIRMED_FAIL`：复测在前置条件成立、证据充分时仍违背需求。",
            "- `BLOCKED`：复测仍缺少前置条件或有效证据，不转换成固件缺陷。",
            "",
            "## 明细",
            "",
            "| 用例ID | 原 FAIL 风险点 | 复测结论 | 复测原因 | 证据 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for item in self.records:
            evidence = "<br>".join(f"`{path}`" for path in item["evidence"])
            lines.append(
                f"| `{item['case_id']}` | {item['original_fail_reason']} | `{item['retest_result']}` | {item['reason']} | {evidence} |"
            )
        lines.extend([
            "",
            "## 机器可读结果",
            "",
            f"- JSON：`{rel(self.runner.bundle_dir / 'validity_results.json')}`",
        ])
        (self.runner.bundle_dir / "validity_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
        (self.runner.bundle_dir / "validity_results.json").write_text(
            json.dumps({"summary": summary, "records": self.records}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # Keep the conventional root artifacts close to the targeted report.
        for src in [PLAN_PATH, CASE_MD_PATH, CASE_XLSX_PATH]:
            if src.exists():
                dst_dir = self.runner.static_dir / ("plan" if src == PLAN_PATH else "cases")
                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst_dir / src.name)

    def run(self) -> Path:
        self.runner.prepare_static_assets()
        if not self.skip_burn:
            self.runner.burn_firmware()
        self.runner.open_ports()
        try:
            startup = self.runner.run_powercycle_step("retest_startup_powercycle_capture", capture_s=10.0, ready_wait_s=8.0)
            self.case_cfg_vol_001(startup)
            self.run_case("retest_cfg_proto_and_sess006", self.case_cfg_proto_and_sess006)
            self.run_case("retest_vol_003", self.case_vol_003)
            self.run_case("retest_reg_cmd_001_003", self.case_reg_cmd_001_003)
            self.run_case("retest_reg_cmd_retry_exhaust", self.case_reg_cmd_retry_exhaust)
            self.run_case("retest_reg_wake_retry_exhaust", self.case_reg_wake_retry_exhaust)
            self.run_case("retest_reg_conflict_001", self.case_reg_conflict_001)
            self.run_case("retest_reg_del_003", self.case_reg_del_003)
            self.run_case("retest_reg_cfg_005", self.case_reg_cfg_005)
            final_clear = self.runner.run_shell_step("retest_final_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
            final_reboot = self.runner.run_shell_step("retest_final_reboot_clean", "reboot", capture_s=10.0, ready_wait_s=8.0)
            self.runner.log_event("final_cleanup", {"evidence": [rel(final_clear.step_dir), rel(final_reboot.step_dir)]})
        finally:
            self.runner.save_streams()
            self.runner.close_ports()
        self.write_validity_report()
        self.runner.write_case_results()
        self.runner.sync_bundle_root_artifacts()
        print(self.runner.bundle_dir)
        return self.runner.bundle_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run targeted validity retests for the current 13 FAIL items.")
    parser.add_argument("--skip-burn", action="store_true", help="Skip firmware burn and only reset config before case branches.")
    args = parser.parse_args()
    runner = RetestRunner(skip_burn=args.skip_burn)
    runner.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
