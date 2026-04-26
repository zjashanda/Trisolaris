#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path

from run_post_restructure_fullflow import (
    ROOT,
    FullflowRunner,
    count_occurrences,
    evidence_has_frames,
    has_all_markers,
    parse_boot_config,
    proto_frames_from_hex,
)


def has_playback(log_text: str) -> bool:
    return any(marker in log_text for marker in ["play start", "play id :", "play stop"])


def has_no_playback(log_text: str) -> bool:
    return not has_playback(log_text)


def contains_any(log_text: str, markers: list[str]) -> bool:
    return any(marker in log_text for marker in markers)


def add_result(
    runner: FullflowRunner,
    case_id: str,
    module: str,
    status: str,
    summary: str,
    evidence: list[Path],
    detail: dict | None = None,
) -> None:
    runner.add_case_result(case_id, module, status, summary, evidence, detail or {})


def write_supplement_meta(runner: FullflowRunner) -> None:
    meta_path = runner.bundle_dir / "supplement_meta.json"
    payload = {
        "mode": "missing_nonreg_cases",
        "burn_skipped": True,
        "case_count": len(runner.case_results),
    }
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    runner = FullflowRunner()
    runner.prepare_static_assets()
    words = runner.spec["words"]
    requirements = runner.spec["requirements"]

    wake_proto = words["小度小度"]["发送协议"]
    xiaoai_proto = words["小爱同学"]["发送协议"]
    open_proto = words["打开电风扇"]["发送协议"]
    close_proto = words["关闭电风扇"]["发送协议"]
    power_on_proto = words["开机"]["发送协议"]
    power_off_proto = words["关机"]["发送协议"]
    vol_up_proto = words["大声点"]["发送协议"]
    vol_down_proto = words["小声点"]["发送协议"]
    vol_max_proto = words["最大音量"]["发送协议"]
    vol_min_proto = words["最小音量"]["发送协议"]
    report_on_proto = words["开启播报"]["发送协议"]
    report_off_proto = words["关闭播报"]["发送协议"]
    voice_off_proto = words["关闭语音"]["发送协议"]
    passive_report_proto = words["播报语"]["接收协议"]
    exit_proto = words["退出识别"]["发送协议"]
    voice_on_proto = "A5 FB 0A CC"

    runner.open_ports()
    try:
        runner.log_event("supplement_start", {"mode": "missing_nonreg_cases", "burn_skipped": True})

        runner.run_shell_step("basic_baseline_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("basic_baseline_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)

        sess_default_open = runner.run_voice_sequence("sess_default_wake_open", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        sess_timeout = runner.run_wake_timeout_probe(
            "sess_timeout_probe",
            "小度小度",
            wait_s=float(requirements["wake_timeout_s"] + 18),
        )
        sess_timeout_blocked = runner.run_voice_sequence("sess_timeout_open_blocked", ["打开电风扇"], post_wait_s=3.0)
        sess_exit_blocked = runner.run_voice_sequence("sess_exit_then_open_blocked", ["小度小度", "退出识别", "打开电风扇"], post_wait_s=3.0)
        ctrl_close = runner.run_voice_sequence("ctrl_close", ["小度小度", "关闭电风扇"], post_wait_s=3.0)
        ctrl_power_on = runner.run_voice_sequence("ctrl_power_on", ["小度小度", "开机"], post_wait_s=3.0)
        ctrl_power_off = runner.run_voice_sequence("ctrl_power_off", ["小度小度", "关机"], post_wait_s=3.0)
        vol_up_down = runner.run_voice_sequence("vol_up_down", ["小度小度", "大声点", "小声点"], post_wait_s=3.0)
        vol_max = runner.run_voice_sequence("vol_max", ["小度小度", "最大音量"], post_wait_s=3.0)
        vol_min = runner.run_voice_sequence("vol_min", ["小度小度", "最小音量"], post_wait_s=3.0)

        sess002_ok = evidence_has_frames(sess_default_open, [wake_proto, open_proto])
        add_result(
            runner,
            "SESS-002",
            "默认唤醒",
            "PASS" if sess002_ok else "FAIL",
            f"默认唤醒后协议链路={proto_frames_from_hex(sess_default_open.proto_hex)}",
            [sess_default_open.step_dir],
        )
        add_result(
            runner,
            "CTRL-001",
            "基础控制",
            "PASS" if sess002_ok else "FAIL",
            f"打开电风扇协议链路={proto_frames_from_hex(sess_default_open.proto_hex)}",
            [sess_default_open.step_dir],
        )

        timeout_markers = sess_timeout.detail.get("markers", {})
        sess003_ok = (
            timeout_markers.get("timeout_marker_s") is not None
            and timeout_markers.get("mode_zero_s") is not None
            and sess_timeout.detail.get("timeout_from_response_end_s") is not None
        )
        add_result(
            runner,
            "SESS-003",
            "会话超时",
            "PASS" if sess003_ok else "FAIL",
            (
                f"纯唤醒后 `TIME_OUT`={timeout_markers.get('timeout_marker_s')}s，"
                f"`MODE=0`={timeout_markers.get('mode_zero_s')}s"
            ),
            [sess_timeout.step_dir],
            sess_timeout.detail,
        )

        sess004_ok = not proto_frames_from_hex(sess_timeout_blocked.proto_hex)
        add_result(
            runner,
            "SESS-004",
            "会话超时",
            "PASS" if sess004_ok else "FAIL",
            f"超时后直说控制词协议链路={proto_frames_from_hex(sess_timeout_blocked.proto_hex)}",
            [sess_timeout.step_dir, sess_timeout_blocked.step_dir],
        )

        sess_exit_frames = proto_frames_from_hex(sess_exit_blocked.proto_hex)
        sess005_ok = exit_proto in sess_exit_frames and open_proto not in sess_exit_frames
        add_result(
            runner,
            "SESS-005",
            "退出识别",
            "PASS" if sess005_ok else "FAIL",
            f"退出识别后阻断链路={sess_exit_frames}",
            [sess_exit_blocked.step_dir],
        )

        for case_id, module, evidence, expected in [
            ("CTRL-002", "基础控制", ctrl_close, close_proto),
            ("CTRL-003", "基础控制", ctrl_power_on, power_on_proto),
            ("CTRL-004", "基础控制", ctrl_power_off, power_off_proto),
        ]:
            frames = proto_frames_from_hex(evidence.proto_hex)
            ok = expected in frames
            add_result(
                runner,
                case_id,
                module,
                "PASS" if ok else "FAIL",
                f"协议链路={frames}",
                [evidence.step_dir],
                {"frames": frames},
            )

        vol_frames = proto_frames_from_hex(vol_up_down.proto_hex)
        vol001_ok = vol_up_proto in vol_frames and vol_down_proto in vol_frames
        add_result(
            runner,
            "VOL-001",
            "音量控制",
            "PASS" if vol001_ok else "FAIL",
            f"大小声协议链路={vol_frames}",
            [vol_up_down.step_dir],
        )

        # The second boundary command can execute inside the existing wake session,
        # so the wake frame is supporting evidence only; the boundary command frame
        # is the functional assertion.
        vol002_ok = vol_max_proto in proto_frames_from_hex(vol_max.proto_hex) and vol_min_proto in proto_frames_from_hex(vol_min.proto_hex)
        add_result(
            runner,
            "VOL-002",
            "音量控制",
            "PASS" if vol002_ok else "FAIL",
            f"最大音量链路={proto_frames_from_hex(vol_max.proto_hex)}；最小音量链路={proto_frames_from_hex(vol_min.proto_hex)}",
            [vol_max.step_dir, vol_min.step_dir],
        )

        runner.run_shell_step("report_baseline_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("report_baseline_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        report_passive_baseline = runner.run_protocol_step("report_passive_baseline", passive_report_proto, post_wait_s=4.0, pre_wait_s=0.3)
        report_off_set = runner.run_voice_sequence("report_off_set", ["小度小度", "关闭播报"], post_wait_s=3.0)
        report_off_then_open = runner.run_voice_sequence("report_off_then_open", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        report_passive_after_off = runner.run_protocol_step("report_passive_after_off", passive_report_proto, post_wait_s=4.0, pre_wait_s=0.3)
        report_on_set = runner.run_voice_sequence("report_on_set", ["小度小度", "开启播报"], post_wait_s=3.0)
        report_on_then_open = runner.run_voice_sequence("report_on_then_open", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        report_passive_after_on = runner.run_protocol_step("report_passive_after_on", passive_report_proto, post_wait_s=4.0, pre_wait_s=0.3)
        report_off_before_powercycle = runner.run_voice_sequence("report_off_before_powercycle", ["小度小度", "关闭播报"], post_wait_s=3.0)
        report_powercycle = runner.run_powercycle_step("report_powercycle_boot")
        report_after_powercycle_open = runner.run_voice_sequence("report_after_powercycle_open", ["小度小度", "打开电风扇"], post_wait_s=3.0)

        report001_ok = (
            evidence_has_frames(report_off_set, [wake_proto, report_off_proto])
            and evidence_has_frames(report_off_then_open, [wake_proto, open_proto])
            and has_no_playback(report_off_then_open.log_text)
        )
        add_result(
            runner,
            "REPORT-001",
            "播报开关",
            "PASS" if report001_ok else "FAIL",
            f"关播报后主动控制协议={proto_frames_from_hex(report_off_then_open.proto_hex)}，播报链路={'无' if has_no_playback(report_off_then_open.log_text) else '仍存在'}",
            [report_off_set.step_dir, report_off_then_open.step_dir],
        )

        report002_ok = (
            has_all_markers(report_passive_baseline.log_text, ["receive msg:: A5 FB 12 CC", "play start"])
            and "receive msg:: A5 FB 12 CC" in report_passive_after_off.log_text
            and has_no_playback(report_passive_after_off.log_text)
        )
        add_result(
            runner,
            "REPORT-002",
            "播报开关",
            "PASS" if report002_ok else "FAIL",
            "关播报后被动播报收到协议但未再播放",
            [report_passive_baseline.step_dir, report_off_set.step_dir, report_passive_after_off.step_dir],
        )

        report003_ok = (
            evidence_has_frames(report_on_set, [wake_proto, report_on_proto])
            and evidence_has_frames(report_on_then_open, [wake_proto, open_proto])
            and has_playback(report_on_then_open.log_text)
            and has_all_markers(report_passive_after_on.log_text, ["receive msg:: A5 FB 12 CC", "play start"])
        )
        add_result(
            runner,
            "REPORT-003",
            "播报开关",
            "PASS" if report003_ok else "FAIL",
            "开播报后主动 / 被动播报都恢复",
            [report_on_set.step_dir, report_on_then_open.step_dir, report_passive_after_on.step_dir],
        )

        report004_ok = evidence_has_frames(report_after_powercycle_open, [wake_proto, open_proto]) and has_playback(report_after_powercycle_open.log_text)
        add_result(
            runner,
            "REPORT-004",
            "播报开关",
            "PASS" if report004_ok else "FAIL",
            f"关播报掉电后主动控制播报{'已恢复' if report004_ok else '未恢复'}",
            [report_off_before_powercycle.step_dir, report_powercycle.step_dir, report_after_powercycle_open.step_dir],
            {"boot_config": parse_boot_config(report_powercycle.log_text)},
        )

        runner.run_shell_step("voice_baseline_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("voice_baseline_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        voice_off_set = runner.run_voice_sequence("voice_off_set", ["小度小度", "关闭语音"], post_wait_s=3.0)
        voice_blocked = runner.run_voice_sequence("voice_blocked_after_off", ["小度小度", "打开电风扇", "大声点"], post_wait_s=3.0)
        voice_off_powercycle = runner.run_powercycle_step("voice_off_powercycle_boot")
        voice_blocked_after_powercycle = runner.run_voice_sequence("voice_blocked_after_powercycle", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        voice_on_proto_step = runner.run_protocol_step("voice_valid_proto_open", voice_on_proto, post_wait_s=3.0, pre_wait_s=0.5)
        voice_open_after_proto = runner.run_voice_sequence("voice_open_after_proto", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        voice_on_powercycle = runner.run_powercycle_step("voice_on_powercycle_boot")
        voice_open_after_powercycle = runner.run_voice_sequence("voice_open_after_powercycle", ["小度小度", "打开电风扇"], post_wait_s=3.0)

        voice001_ok = evidence_has_frames(voice_off_set, [wake_proto, voice_off_proto]) and not proto_frames_from_hex(voice_blocked.proto_hex)
        add_result(
            runner,
            "VOICE-001",
            "语音开关",
            "PASS" if voice001_ok else "FAIL",
            f"关语音后主动协议链路={proto_frames_from_hex(voice_blocked.proto_hex)}",
            [voice_off_set.step_dir, voice_blocked.step_dir],
        )

        voice002_ok = (
            voice_on_proto_step.detail.get("payload_hex") == voice_on_proto
            and "receive msg:: A5 FB 0A CC" in voice_on_proto_step.log_text
            and evidence_has_frames(voice_open_after_proto, [wake_proto, open_proto])
        )
        add_result(
            runner,
            "VOICE-002",
            "语音开关",
            "PASS" if voice002_ok else "FAIL",
            "协议开语音后默认唤醒与基础控制恢复",
            [voice_on_proto_step.step_dir, voice_open_after_proto.step_dir],
        )

        voice_off_cfg = parse_boot_config(voice_off_powercycle.log_text)
        voice_on_cfg = parse_boot_config(voice_on_powercycle.log_text)
        voice004_ok = (
            voice_off_cfg.get("voice") == 0
            and not proto_frames_from_hex(voice_blocked_after_powercycle.proto_hex)
            and voice_on_cfg.get("voice") == 1
            and evidence_has_frames(voice_open_after_powercycle, [wake_proto, open_proto])
        )
        add_result(
            runner,
            "VOICE-004",
            "语音开关",
            "PASS" if voice004_ok else "FAIL",
            f"关语音掉电后 voice={voice_off_cfg.get('voice')}；开语音掉电后 voice={voice_on_cfg.get('voice')}",
            [
                voice_off_set.step_dir,
                voice_off_powercycle.step_dir,
                voice_blocked_after_powercycle.step_dir,
                voice_on_proto_step.step_dir,
                voice_on_powercycle.step_dir,
                voice_open_after_powercycle.step_dir,
            ],
            {"voice_off_boot_config": voice_off_cfg, "voice_on_boot_config": voice_on_cfg},
        )

        runner.run_shell_step("swake_baseline_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("swake_baseline_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        switch_wake = runner.run_voice_sequence("switch_wake_to_xiaoai", ["小度小度", "切换唤醒词"], post_wait_s=3.0)
        switch_idle_current = runner.run_idle_wait_step("switch_idle_before_xiaoai", duration_s=22.0)
        swake_current = runner.run_voice_sequence("switch_xiaoai_open", ["小爱同学", "打开电风扇"], post_wait_s=3.0)
        switch_idle_default = runner.run_idle_wait_step("switch_idle_before_default", duration_s=22.0)
        swake_default = runner.run_voice_sequence("switch_default_open", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        swake_powercycle = runner.run_powercycle_step("switch_powercycle_boot")
        switch_idle_current_after_power = runner.run_idle_wait_step("switch_idle_before_xiaoai_after_power", duration_s=22.0)
        swake_current_after_power = runner.run_voice_sequence("switch_xiaoai_after_power_open", ["小爱同学", "打开电风扇"], post_wait_s=3.0)
        switch_idle_default_after_power = runner.run_idle_wait_step("switch_idle_before_default_after_power", duration_s=22.0)
        swake_default_after_power = runner.run_voice_sequence("switch_default_after_power_open", ["小度小度", "打开电风扇"], post_wait_s=3.0)

        swake001_ok = evidence_has_frames(swake_current, [xiaoai_proto, open_proto])
        add_result(
            runner,
            "SWAKE-001",
            "切换唤醒词",
            "PASS" if swake001_ok else "FAIL",
            f"当前切换唤醒词协议链路={proto_frames_from_hex(swake_current.proto_hex)}",
            [switch_wake.step_dir, switch_idle_current.step_dir, swake_current.step_dir],
        )

        swake002_ok = evidence_has_frames(swake_default, [wake_proto, open_proto])
        add_result(
            runner,
            "SWAKE-002",
            "切换唤醒词",
            "PASS" if swake002_ok else "FAIL",
            f"默认唤醒词协议链路={proto_frames_from_hex(swake_default.proto_hex)}",
            [switch_wake.step_dir, switch_idle_default.step_dir, swake_default.step_dir],
        )

        swake006_ok = evidence_has_frames(swake_current_after_power, [xiaoai_proto, open_proto]) and evidence_has_frames(swake_default_after_power, [wake_proto, open_proto])
        add_result(
            runner,
            "SWAKE-006",
            "切换唤醒词",
            "PASS" if swake006_ok else "FAIL",
            "切换结果掉电后仍保持，默认唤醒词仍常驻可用",
            [
                switch_wake.step_dir,
                swake_powercycle.step_dir,
                switch_idle_current_after_power.step_dir,
                swake_current_after_power.step_dir,
                switch_idle_default_after_power.step_dir,
                swake_default_after_power.step_dir,
            ],
            {"boot_config": parse_boot_config(swake_powercycle.log_text)},
        )

        runner.run_shell_step("reg_entry_cmd_baseline_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("reg_entry_cmd_baseline_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        reg_entry_cmd = runner.run_voice_sequence("reg_entry_cmd_only", ["小度小度", "学习命令词"], post_wait_s=3.0)
        reg_entry_cmd_ok = contains_any(reg_entry_cmd.log_text, ["keyword:xue xi ming ling ci", "xue xi ming ling ci"])
        add_result(
            runner,
            "REG-ENTRY-001",
            "语音注册",
            "PASS" if reg_entry_cmd_ok else "FAIL",
            "命令词学习入口已进入学习态",
            [reg_entry_cmd.step_dir],
        )

        runner.run_shell_step("reg_exit_baseline_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("reg_exit_baseline_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        reg_exit = runner.run_voice_sequence("reg_exit_learning_then_recover", ["小度小度", "学习命令词", "退出学习"], post_wait_s=3.0)
        reg_exit_recover = runner.run_voice_sequence("reg_exit_default_open_recover", ["小度小度", "打开电风扇"], post_wait_s=3.0)
        reg_exit_ok = contains_any(reg_exit.log_text, ["keyword:tui chu xue xi", "tui chu xue xi", "退出学习"]) and open_proto in proto_frames_from_hex(reg_exit_recover.proto_hex)
        add_result(
            runner,
            "REG-EXIT-001",
            "语音注册",
            "PASS" if reg_exit_ok else "FAIL",
            "退出学习后默认控制恢复",
            [reg_exit.step_dir, reg_exit_recover.step_dir],
        )

        runner.run_shell_step("reg_entry_wake_baseline_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        runner.run_shell_step("reg_entry_wake_baseline_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        reg_entry_wake = runner.run_voice_sequence("reg_entry_wake_only", ["小度小度", "学习唤醒词"], post_wait_s=3.0)
        reg_entry_wake_ok = contains_any(reg_entry_wake.log_text, ["keyword:xue xi huan xing ci", "xue xi huan xing ci"])
        add_result(
            runner,
            "REG-ENTRY-002",
            "语音注册",
            "PASS" if reg_entry_wake_ok else "FAIL",
            "唤醒词学习入口已进入学习态",
            [reg_entry_wake.step_dir],
        )

    finally:
        runner.close_ports()

    runner.save_streams()
    runner.write_case_results()
    write_supplement_meta(runner)
    runner.sync_bundle_root_artifacts()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
