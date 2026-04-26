#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path

from run_post_restructure_fullflow import (
    FullflowRunner,
    evidence_has_frames,
    proto_frames_from_hex,
)

WAKE = "小度小度"
XIAOAI = "小爱同学"
OPEN_FAN = "打开电风扇"
CLOSE_FAN = "关闭电风扇"
VOL_UP = "大声点"
LEARN_CMD = "学习命令词"
LEARN_NEXT = "学习下一个"
LEARN_WAKE = "学习唤醒词"
DELETE_CMD = "删除命令词"
EXIT_DELETE = "退出删除"
ALIAS_CLOSE = "笑逐颜开"
WAKE_ALIAS = "晴空万里"


def frames(step) -> list[str]:
    return proto_frames_from_hex(step.proto_hex)


def has_frame(step, frame: str) -> bool:
    return frame in frames(step)


def save_closed(text: str) -> bool:
    return any(marker in text for marker in ["save new voice.bin", "reg cmd over success", "save config success"])


def add(runner: FullflowRunner, case_id: str, module: str, status: str, summary: str, evidence: list, detail: dict | None = None) -> None:
    paths = [item.step_dir if hasattr(item, "step_dir") else item for item in evidence]
    runner.add_case_result(case_id, module, status, summary, paths, detail or {})


def baseline(runner: FullflowRunner, prefix: str) -> list:
    clear = runner.run_shell_step(f"{prefix}_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
    reboot = runner.run_shell_step(f"{prefix}_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
    return [clear, reboot]


def main() -> int:
    runner = FullflowRunner()
    runner.prepare_static_assets()
    words = runner.spec["words"]
    wake_frame = words[WAKE]["发送协议"]
    xiaoai_frame = words[XIAOAI]["发送协议"]
    open_frame = words[OPEN_FAN]["发送协议"]
    close_frame = words[CLOSE_FAN]["发送协议"]
    vol_up_frame = words[VOL_UP]["发送协议"]

    runner.open_ports()
    try:
        # SWAKE-005: main run had an empty volume capture. Rebuild the exact
        # precondition and assert the functional frames, not the incidental wake frame.
        ev = baseline(runner, "closure_swake005")
        switch = runner.run_voice_sequence("closure_swake005_switch_to_xiaoai", [WAKE, "切换唤醒词"], post_wait_s=3.0)
        idle_open = runner.run_idle_wait_step("closure_swake005_idle_before_default_open", duration_s=22.0)
        default_open = runner.run_voice_sequence("closure_swake005_default_open", [WAKE, OPEN_FAN], post_wait_s=4.0)
        idle_vol = runner.run_idle_wait_step("closure_swake005_idle_before_default_volume", duration_s=22.0)
        default_vol = runner.run_voice_sequence("closure_swake005_default_volume", [WAKE, VOL_UP], post_wait_s=4.0)
        swake_ok = has_frame(default_open, wake_frame) and has_frame(default_open, open_frame) and has_frame(default_vol, vol_up_frame)
        add(
            runner,
            "SWAKE-005",
            "切换唤醒词",
            "PASS" if swake_ok else "FAIL",
            f"切换到 `{XIAOAI}` 后默认唤醒词控制/音量复测 frames(open)={frames(default_open)} frames(volume)={frames(default_vol)}",
            [*ev, switch.step_dir, idle_open.step_dir, default_open.step_dir, idle_vol.step_dir, default_vol.step_dir],
            {"switch_frames": frames(switch), "default_open_frames": frames(default_open), "default_volume_frames": frames(default_vol), "xiaoai_frame": xiaoai_frame},
        )

        # REG-CMD-001/002/003 and REG-DEL-002: use one clean learning branch so
        # alias save, reboot persistence, original command coexistence, and exit-delete keep are judged from the same state.
        ev = baseline(runner, "closure_regcmd")
        learn = runner.run_voice_sequence(
            "closure_regcmd_learn_close_alias",
            [WAKE, LEARN_CMD, LEARN_NEXT, ALIAS_CLOSE, ALIAS_CLOSE],
            post_wait_s=12.0,
        )
        if not save_closed(learn.log_text):
            learn_retry_base = baseline(runner, "closure_regcmd_retry")
            learn = runner.run_voice_sequence(
                "closure_regcmd_learn_close_alias_retry",
                [WAKE, LEARN_CMD, LEARN_NEXT, ALIAS_CLOSE, ALIAS_CLOSE],
                post_wait_s=12.0,
            )
            ev.extend(learn_retry_base)
        closure = runner.run_voice_sequence("closure_regcmd_force_save_closure", [WAKE, ALIAS_CLOSE], post_wait_s=8.0)
        reboot = runner.run_shell_step("closure_regcmd_reboot_after_save", "reboot", capture_s=10.0, ready_wait_s=8.0)
        alias_after = runner.run_voice_sequence("closure_regcmd_alias_after_reboot", [WAKE, ALIAS_CLOSE], post_wait_s=4.0)
        default_after = runner.run_voice_sequence("closure_regcmd_default_after_reboot", [WAKE, CLOSE_FAN], post_wait_s=4.0)
        delete_exit = runner.run_voice_sequence("closure_regcmd_delete_exit_keep", [WAKE, DELETE_CMD, EXIT_DELETE], post_wait_s=4.0)
        alias_after_exit = runner.run_voice_sequence("closure_regcmd_alias_after_delete_exit", [WAKE, ALIAS_CLOSE], post_wait_s=4.0)

        combined_save = learn.log_text + "\n" + closure.log_text
        cmd_saved = save_closed(combined_save)
        alias_ok = has_frame(alias_after, close_frame)
        default_ok = has_frame(default_after, close_frame)
        alias_kept = has_frame(alias_after_exit, close_frame)
        cmd_evidence = [*ev, learn.step_dir, closure.step_dir, reboot.step_dir, alias_after.step_dir, default_after.step_dir]
        add(
            runner,
            "REG-CMD-001",
            "语音注册-命令词",
            "PASS" if cmd_saved and alias_ok else "FAIL",
            f"命令词学习保存闭环={cmd_saved}，重启后别名 frames={frames(alias_after)}",
            cmd_evidence,
            {"save_closed": cmd_saved, "alias_frames": frames(alias_after), "expected_close_frame": close_frame},
        )
        add(
            runner,
            "REG-CMD-002",
            "语音注册-命令词",
            "PASS" if cmd_saved and alias_ok else "FAIL",
            f"命令词学习保存后重启复测别名 frames={frames(alias_after)}",
            cmd_evidence,
            {"save_closed": cmd_saved, "alias_frames": frames(alias_after), "expected_close_frame": close_frame},
        )
        add(
            runner,
            "REG-CMD-003",
            "语音注册-命令词",
            "PASS" if cmd_saved and alias_ok and default_ok else "FAIL",
            f"命令词别名与默认命令共存：alias={frames(alias_after)} default={frames(default_after)}",
            cmd_evidence,
            {"save_closed": cmd_saved, "alias_frames": frames(alias_after), "default_frames": frames(default_after), "expected_close_frame": close_frame},
        )
        add(
            runner,
            "REG-DEL-002",
            "语音注册-删除",
            "PASS" if cmd_saved and alias_kept else "FAIL",
            f"退出删除命令词后别名仍保留 frames={frames(alias_after_exit)}",
            [*cmd_evidence, delete_exit.step_dir, alias_after_exit.step_dir],
            {"save_closed": cmd_saved, "delete_exit_frames": frames(delete_exit), "alias_after_exit_frames": frames(alias_after_exit)},
        )

        # REG-WAKE-001/002: rebuild clean wake-word learning evidence.
        ev = baseline(runner, "closure_regwake")
        wake_learn = runner.run_voice_sequence("closure_regwake_learn_sequence", [WAKE, LEARN_WAKE, WAKE_ALIAS, WAKE_ALIAS], post_wait_s=12.0)
        wake_verify = runner.run_voice_sequence("closure_regwake_new_wake_open", [WAKE_ALIAS, OPEN_FAN], post_wait_s=4.0)
        default_verify = runner.run_voice_sequence("closure_regwake_default_open", [WAKE, OPEN_FAN], post_wait_s=4.0)
        wake_saved = save_closed(wake_learn.log_text)
        learned_ok = has_frame(wake_verify, open_frame)
        default_ok = has_frame(default_verify, open_frame)
        add(
            runner,
            "REG-WAKE-001",
            "语音注册-唤醒词",
            "PASS" if wake_saved and learned_ok else "FAIL",
            f"唤醒词学习保存闭环={wake_saved}，学习唤醒词复测 frames={frames(wake_verify)}",
            [*ev, wake_learn.step_dir, wake_verify.step_dir],
            {"save_closed": wake_saved, "learned_frames": frames(wake_verify)},
        )
        add(
            runner,
            "REG-WAKE-002",
            "语音注册-唤醒词",
            "PASS" if wake_saved and default_ok else "FAIL",
            f"学习唤醒词后默认唤醒词复测 frames={frames(default_verify)}",
            [*ev, wake_learn.step_dir, default_verify.step_dir],
            {"save_closed": wake_saved, "default_frames": frames(default_verify)},
        )

        # REG-CONFLICT-002: confirm whether default wake word is incorrectly saved as a learned wake word.
        ev = baseline(runner, "closure_conflict_default_wake")
        default_conflict = runner.run_voice_sequence(
            "closure_conflict_default_wake_sequence",
            [WAKE, LEARN_WAKE, WAKE, WAKE],
            post_wait_s=12.0,
        )
        conflict_saved = save_closed(default_conflict.log_text)
        add(
            runner,
            "REG-CONFLICT-002",
            "语音注册-冲突词",
            "FAIL" if conflict_saved else "PASS",
            (
                "默认唤醒词作为学习唤醒词样本时出现保存闭环，违背冲突拒学预期"
                if conflict_saved
                else "默认唤醒词作为学习唤醒词样本时未保存，符合冲突拒学预期"
            ),
            [*ev, default_conflict.step_dir],
            {"save_closed": conflict_saved, "frames": frames(default_conflict)},
        )
    finally:
        runner.save_streams()
        runner.close_ports()

    runner.write_case_results()
    runner.sync_bundle_root_artifacts()
    print(runner.bundle_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
