#!/usr/bin/env python
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import serial

SCRIPT_DIR = Path(__file__).resolve().parent
AUDIO_DIR = SCRIPT_DIR.parent / "audio"
if str(AUDIO_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIO_DIR))

from fan_dual_capture import capture_sequence as dual_capture_sequence


ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ROOT / "result"

DEVICE_KEY = "VID_8765&PID_5678:8_804B35B_1_0000"
LOG_PORT = "COM38"
LOG_BAUD = 115200
PROTO_PORT = "COM36"
PROTO_BAUD = 9600
CTRL_PORT = "COM39"
CTRL_BAUD = 115200


class BatchRunner:
    def __init__(self) -> None:
        self.counter = 0
        self.summary: list[dict] = []

    def _result_dir(self, label: str) -> Path:
        self.counter += 1
        stamp = datetime.now().strftime("%m%d%H%M%S")
        return RESULT_ROOT / f"{stamp}_{self.counter:02d}_{label}"

    def _record(
        self,
        label: str,
        status: str,
        result_dir: Optional[Path] = None,
        detail: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        item = {
            "label": label,
            "status": status,
            "result_dir": str(result_dir.relative_to(ROOT)) if result_dir else None,
            "detail": detail or {},
            "error": error,
            "at": datetime.now().isoformat(timespec="seconds"),
        }
        self.summary.append(item)
        status_text = status.upper()
        suffix = f" -> {item['result_dir']}" if item["result_dir"] else ""
        if error:
            print(f"[{status_text}] {label}{suffix}: {error}", flush=True)
        else:
            print(f"[{status_text}] {label}{suffix}", flush=True)

    def run_dual(
        self,
        label: str,
        texts: list[str],
        *,
        rate: int = 0,
        between_max_wait_s: float = 4.5,
        between_min_wait_s: float = 0.8,
        quiet_window_s: float = 0.6,
        post_wait_s: float = 4.0,
    ) -> Optional[Path]:
        result_dir = self._result_dir(label)
        try:
            meta = dual_capture_sequence(
                texts=texts,
                device_key=DEVICE_KEY,
                log_port_name=LOG_PORT,
                log_baudrate=LOG_BAUD,
                proto_port_name=PROTO_PORT,
                proto_baudrate=PROTO_BAUD,
                result_dir=result_dir,
                between_max_wait_s=between_max_wait_s,
                between_min_wait_s=between_min_wait_s,
                quiet_window_s=quiet_window_s,
                post_wait_s=post_wait_s,
                send_loglevel4=True,
                voice="Microsoft Huihui Desktop",
                rate=rate,
            )
            self._record(
                label,
                "ok",
                result_dir=result_dir,
                detail={"texts": texts, "log_bytes": meta.get("log_bytes"), "proto_bytes": meta.get("proto_bytes")},
            )
            return result_dir
        except Exception as exc:  # pragma: no cover - serial/device runtime path
            self._record(label, "error", result_dir=result_dir, error=str(exc), detail={"texts": texts})
            return None

    def run_shell(self, label: str, command: str, *, capture_s: float = 10.0, ready_wait_s: float = 0.0) -> Optional[Path]:
        result_dir = self._result_dir(label)
        result_dir.mkdir(parents=True, exist_ok=True)
        raw_path = result_dir / "serial_raw.bin"
        text_path = result_dir / "serial_utf8.txt"
        meta_path = result_dir / "meta.json"
        chunks = bytearray()
        try:
            port = serial.Serial(LOG_PORT, baudrate=LOG_BAUD, timeout=0.05, write_timeout=0.5)
            try:
                port.reset_input_buffer()
                port.write((command + "\r\n").encode("ascii"))
                port.flush()
                deadline = time.time() + capture_s
                while time.time() < deadline:
                    data = port.read(4096)
                    if data:
                        chunks.extend(data)
                    time.sleep(0.02)
            finally:
                port.close()

            raw_path.write_bytes(chunks)
            text_path.write_text(chunks.decode("utf-8", errors="replace"), encoding="utf-8")
            meta = {
                "command": command,
                "log_port": LOG_PORT,
                "log_baudrate": LOG_BAUD,
                "capture_s": capture_s,
                "ready_wait_s": ready_wait_s,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "log_bytes": len(chunks),
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            if ready_wait_s > 0:
                time.sleep(ready_wait_s)
            self._record(label, "ok", result_dir=result_dir, detail={"command": command, "log_bytes": len(chunks)})
            return result_dir
        except Exception as exc:  # pragma: no cover - serial/device runtime path
            self._record(label, "error", result_dir=result_dir, error=str(exc), detail={"command": command})
            return None

    def run_powercycle(
        self,
        label: str,
        *,
        commands: Optional[list[str]] = None,
        cmd_delay_s: float = 0.35,
        capture_s: float = 10.0,
        ready_wait_s: float = 8.0,
    ) -> Optional[Path]:
        if commands is None:
            commands = ["uut-switch1.off", "uut-switch2.off", "uut-switch1.on"]
        result_dir = self._result_dir(label)
        result_dir.mkdir(parents=True, exist_ok=True)
        raw_path = result_dir / "boot_log_raw.bin"
        text_path = result_dir / "boot_log_utf8.txt"
        meta_path = result_dir / "meta.json"
        chunks = bytearray()
        try:
            log_port = serial.Serial(LOG_PORT, baudrate=LOG_BAUD, timeout=0.05, write_timeout=0.5)
            ctrl_port = serial.Serial(CTRL_PORT, baudrate=CTRL_BAUD, timeout=0.05, write_timeout=0.5)
            try:
                log_port.reset_input_buffer()
                ctrl_port.reset_input_buffer()
                for cmd in commands:
                    ctrl_port.write((cmd + "\r\n").encode("ascii"))
                    ctrl_port.flush()
                    time.sleep(cmd_delay_s)
                deadline = time.time() + capture_s
                while time.time() < deadline:
                    data = log_port.read(4096)
                    if data:
                        chunks.extend(data)
                    time.sleep(0.02)
            finally:
                ctrl_port.close()
                log_port.close()

            raw_path.write_bytes(chunks)
            text_path.write_text(chunks.decode("utf-8", errors="replace"), encoding="utf-8")
            meta = {
                "commands": commands,
                "ctrl_port": CTRL_PORT,
                "ctrl_baudrate": CTRL_BAUD,
                "log_port": LOG_PORT,
                "log_baudrate": LOG_BAUD,
                "cmd_delay_s": cmd_delay_s,
                "capture_s": capture_s,
                "ready_wait_s": ready_wait_s,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "log_bytes": len(chunks),
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            if ready_wait_s > 0:
                time.sleep(ready_wait_s)
            self._record(label, "ok", result_dir=result_dir, detail={"commands": commands, "log_bytes": len(chunks)})
            return result_dir
        except Exception as exc:  # pragma: no cover - serial/device runtime path
            self._record(label, "error", result_dir=result_dir, error=str(exc), detail={"commands": commands})
            return None

    def skip(self, label: str, reason: str) -> None:
        self._record(label, "skipped", error=reason)

    def reset_baseline(self, prefix: str) -> bool:
        clear_dir = self.run_shell(f"{prefix}_config_clear", "config.clear", capture_s=3.0, ready_wait_s=1.0)
        reboot_dir = self.run_shell(f"{prefix}_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0)
        return bool(clear_dir and reboot_dir)

    def save_summary(self) -> Path:
        out_path = self._result_dir("remaining_voice_reg_batch_summary") / "summary.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "started_at": self.summary[0]["at"] if self.summary else None,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "items": self.summary,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] summary -> {out_path.relative_to(ROOT)}", flush=True)
        return out_path


def run_branch(runner: BatchRunner, prefix: str, steps: Callable[[], None]) -> None:
    print(f"\n=== BRANCH {prefix} ===", flush=True)
    if not runner.reset_baseline(prefix):
        runner.skip(f"{prefix}_branch", "baseline reset failed")
        return
    steps()


def main() -> int:
    runner = BatchRunner()

    run_branch(
        runner,
        "reg_cmd_close",
        lambda: (
            runner.run_dual(
                "reg_tc_learn_cmd_close_sequence",
                ["小度小度", "学习命令词", "学习下一个", "笑逐颜开", "笑逐颜开"],
            ),
            runner.run_dual("reg_tc_learn_cmd_close_alias_recheck", ["小度小度", "笑逐颜开"]),
            runner.run_shell("reg_tc_learn_cmd_close_persist_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0),
            runner.run_dual("reg_tc_learn_cmd_close_after_reboot_alias", ["小度小度", "笑逐颜开"]),
            runner.run_dual("reg_delete_cmd_exit_keep", ["小度小度", "删除命令词", "退出删除"]),
            runner.run_dual("reg_delete_cmd_exit_keep_alias_recheck", ["小度小度", "笑逐颜开"]),
            runner.run_dual("reg_delete_cmd_confirm_sequence", ["小度小度", "删除命令词", "删除命令词"]),
            runner.run_dual("reg_delete_cmd_confirm_alias_blocked", ["小度小度", "笑逐颜开"]),
            runner.run_dual("reg_delete_cmd_confirm_default_close_ok", ["小度小度", "关闭电风扇"]),
        ),
    )

    run_branch(
        runner,
        "reg_voice001_open",
        lambda: (
            runner.run_dual("reg_voice001_learn_cmd_open_sequence", ["小度小度", "学习命令词", "笑逐颜开", "笑逐颜开"]),
            runner.run_dual("reg_voice001_learn_cmd_open_alias_recheck", ["小度小度", "笑逐颜开"]),
        ),
    )

    run_branch(
        runner,
        "reg_voice003_retry_recover",
        lambda: (
            runner.run_dual(
                "reg_voice003_cmd_retry_recover_sequence",
                ["小度小度", "学习命令词", "学习下一个", "心想事成", "万事大吉", "心想事成", "心想事成"],
            ),
            runner.run_dual("reg_voice003_cmd_retry_recover_alias_recheck", ["小度小度", "心想事成"]),
        ),
    )

    run_branch(
        runner,
        "reg_voice005_retry_exhaust",
        lambda: (
            runner.run_dual(
                "reg_voice005_cmd_retry_exhaust_sequence",
                ["小度小度", "学习命令词", "学习下一个", "万事大吉", "心想事成", "打开电风扇", "笑逐颜开"],
            ),
            runner.run_dual("reg_voice005_cmd_retry_exhaust_failed_alias_probe", ["小度小度", "万事大吉"]),
        ),
    )

    run_branch(
        runner,
        "reg_voice007_conflict",
        lambda: (
            runner.run_dual("reg_voice007_cmd_conflict_volume_word_sequence", ["小度小度", "学习命令词", "增大音量", "增大音量"]),
            runner.run_dual("reg_voice007_cmd_conflict_volume_word_recheck", ["小度小度", "增大音量"]),
        ),
    )

    run_branch(
        runner,
        "reg_voice009_reserved_cmd",
        lambda: runner.run_dual(
            "reg_voice009_cmd_reserved_learn_wakeup_word",
            ["小度小度", "学习命令词", "学习唤醒词", "学习唤醒词"],
        ),
    )

    run_branch(
        runner,
        "reg_learn_boundary",
        lambda: (
            runner.run_dual(
                "reg_tc_learn_prev_boundary",
                ["小度小度", "学习命令词", "重新学习上一个", "退出学习"],
                rate=-2,
            ),
            runner.run_dual(
                "reg_tc_learn_next_boundary_full",
                ["小度小度", "学习命令词", "学习下一个", "学习下一个", "退出学习"],
            ),
        ),
    )

    run_branch(
        runner,
        "reg_wakeup_success_delete",
        lambda: (
            runner.run_dual("reg_voice002_learn_wakeup_sequence", ["小度小度", "学习唤醒词", "晴空万里", "晴空万里"]),
            runner.run_dual("reg_voice002_learned_wake_recheck_open", ["晴空万里", "打开电风扇"]),
            runner.run_dual("reg_voice002_default_wake_still_open_ok", ["小度小度", "打开电风扇"]),
            runner.run_shell("reg_voice002_persist_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0),
            runner.run_dual("reg_voice002_after_reboot_learned_wake_open", ["晴空万里", "打开电风扇"]),
            runner.run_dual("reg_voice014_delete_wakeup_exit_keep", ["小度小度", "删除唤醒词", "退出删除"]),
            runner.run_dual("reg_voice014_delete_wakeup_exit_keep_recheck", ["晴空万里", "打开电风扇"]),
            runner.run_dual("reg_voice013_delete_wakeup_confirm_sequence", ["小度小度", "删除唤醒词", "删除唤醒词"]),
            runner.run_dual("reg_voice013_delete_wakeup_confirm_learned_wake_blocked", ["晴空万里", "打开电风扇"]),
            runner.run_dual("reg_voice013_delete_wakeup_confirm_default_wake_ok", ["小度小度", "打开电风扇"]),
        ),
    )

    run_branch(
        runner,
        "reg_voice004_retry_recover",
        lambda: (
            runner.run_dual(
                "reg_voice004_wakeup_retry_recover_sequence",
                ["小度小度", "学习唤醒词", "小树小树", "小熊维尼", "小树小树", "小树小树"],
            ),
            runner.run_dual("reg_voice004_wakeup_retry_recover_recheck_open", ["小树小树", "打开电风扇"]),
            runner.run_dual("reg_voice004_wakeup_retry_recover_default_wake_ok", ["小度小度", "打开电风扇"]),
        ),
    )

    run_branch(
        runner,
        "reg_voice006_retry_exhaust",
        lambda: (
            runner.run_dual(
                "reg_voice006_wakeup_retry_exhaust_sequence",
                ["小度小度", "学习唤醒词", "小熊维尼", "小树小树", "小度小度", "晴空万里"],
            ),
            runner.run_dual("reg_voice006_wakeup_retry_exhaust_failed_wake_probe", ["小熊维尼", "打开电风扇"]),
            runner.run_dual("reg_voice006_wakeup_retry_exhaust_default_wake_ok", ["小度小度", "打开电风扇"]),
        ),
    )

    run_branch(
        runner,
        "reg_voice008_default_conflict",
        lambda: runner.run_dual(
            "reg_voice008_wakeup_conflict_default_xiaodu",
            ["小度小度", "学习唤醒词", "小度小度", "小度小度"],
        ),
    )

    run_branch(
        runner,
        "reg_voice010_reserved_wakeup",
        lambda: runner.run_dual(
            "reg_voice010_wakeup_reserved_learn_cmd_word",
            ["小度小度", "学习唤醒词", "学习命令词", "学习命令词"],
        ),
    )

    run_branch(
        runner,
        "reg_tc_learn003",
        lambda: (
            runner.run_dual("reg_tc_learn003_learn_wakeup_sequence", ["小度小度", "学习唤醒词", "小树小树", "小树小树"]),
            runner.run_dual(
                "reg_tc_learn003_learn_cmd_full_sequence",
                ["小度小度", "学习命令词", "笑逐颜开", "笑逐颜开", "心想事成", "心想事成"],
            ),
            runner.run_dual(
                "reg_tc_learn003_pre_powercycle_recheck",
                ["小树小树", "打开电风扇", "小度小度", "笑逐颜开", "小度小度", "心想事成"],
            ),
            runner.run_powercycle("reg_tc_learn003_powercycle_boot"),
            runner.run_dual(
                "reg_tc_learn003_post_powercycle_recheck",
                ["小树小树", "打开电风扇", "小度小度", "笑逐颜开", "小度小度", "心想事成"],
            ),
        ),
    )

    runner.save_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
