#!/usr/bin/env python
from run_remaining_voice_reg_batch import BatchRunner, run_branch


def main() -> int:
    runner = BatchRunner()

    run_branch(
        runner,
        "repair_voice001",
        lambda: (
            runner.run_dual(
                "repair_voice001_learn_open_with_exit",
                ["小度小度", "学习命令词", "笑逐颜开", "笑逐颜开", "退出学习"],
            ),
            runner.run_dual(
                "repair_voice001_alias_recheck_after_exit",
                ["小度小度", "笑逐颜开"],
            ),
        ),
    )

    run_branch(
        runner,
        "repair_voice003",
        lambda: (
            runner.run_dual(
                "repair_voice003_retry_recover_sequence",
                ["小度小度", "学习命令词", "学习下一个", "心想事成", "万事大吉", "心想事成", "心想事成"],
            ),
            runner.run_shell("repair_voice003_retry_recover_reboot", "reboot", capture_s=10.0, ready_wait_s=8.0),
            runner.run_dual(
                "repair_voice003_alias_recheck_after_reboot",
                ["小度小度", "心想事成"],
            ),
        ),
    )

    run_branch(
        runner,
        "repair_voice011",
        lambda: (
            runner.run_dual(
                "repair_voice011_learn_close_sequence",
                ["小度小度", "学习命令词", "学习下一个", "笑逐颜开", "笑逐颜开"],
            ),
            runner.run_dual(
                "repair_voice011_delete_confirm_sequence",
                ["小度小度", "删除命令词", "删除命令词"],
            ),
            runner.run_dual(
                "repair_voice011_default_close_ok",
                ["小度小度", "关闭电风扇"],
            ),
        ),
    )

    runner.save_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
