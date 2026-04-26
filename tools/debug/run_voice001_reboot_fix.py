#!/usr/bin/env python
from run_remaining_voice_reg_batch import BatchRunner, run_branch


def main() -> int:
    runner = BatchRunner()
    run_branch(
        runner,
        "fix_voice001_reboot",
        lambda: (
            runner.run_dual(
                "fix_voice001_learn_open_with_exit",
                ["小度小度", "学习命令词", "笑逐颜开", "笑逐颜开", "退出学习"],
            ),
            runner.run_shell("fix_voice001_reboot_after_exit", "reboot", capture_s=10.0, ready_wait_s=8.0),
            runner.run_dual(
                "fix_voice001_alias_recheck_after_reboot",
                ["小度小度", "笑逐颜开"],
            ),
        ),
    )
    runner.save_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
