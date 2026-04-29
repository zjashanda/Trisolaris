---
module_id: burn-and-gates
title: 烧录、健康检查和最小可测性门禁
tags: [烧录, boot, 上电, 下电, app.bin, pretest, 门禁, ready, loglevel, MCU is not ready]
source_projects: [mars-moon, mars-belt, csk3022-htt, csk5062-xiaodu]
---

# 烧录、健康检查和最小可测性门禁

## 适用需求特征

- 输入含固件并要求全链路验证。
- 设备需要控制串口上下电和 boot 控制。
- 运行前需要确认日志、协议、声卡和 MCU/设备 ready。

## 变体维度

- 烧录时序：不同项目 boot 保持时长不同；Trisolaris 当前统一为上电后保持 boot 6s 再出 boot。
- ready 口径：MCU 握手仿真 / 平台 pretest / 日志 shell + loglevel / 最小唤醒命令。
- 健康检查：启动 20s 无异常重启 / 有调试日志 / 有协议心跳 / 有版本号。

## 需求解析字段

- 固件路径、烧录工具、烧录口、控制口、boot 控制命令、等待时间。
- 日志口和协议口波特率。
- ready 标志和禁止继续的异常标志。

## 验证方案模板

1. 若有 `config.clear`，先清配置再烧录，用固件默认值作为基线。
2. 烧录文件必须复制到工具目录并唯一命名为 `app.bin`。
3. 执行完整时序：断电 -> 进 boot -> 上电 -> 保持 boot -> 下 boot -> 烧录。
4. 烧录前后都做控制口验活：控制口必须实际触发断电/上电/boot，不能只看串口可打开。
5. 烧录后重新上电，做健康检查。
6. 通过最小可测性门禁后才允许跑正式用例。

## 用例模板

- `GATE-BURN-001`：烧录成功标记闭环。
- `GATE-BOOT-001`：启动健康检查。
- `GATE-READY-001`：协议/MCU/日志 ready。
- `GATE-SMOKE-001`：默认唤醒和基础命令 smoke。

## 断言与证据

- 烧录不能只看 exit code，必须看工具成功标记和启动日志版本。
- 用户给出的端口映射若导致 power-cycle 或 boot 不生效，先做端口控制变量探测并更新执行映射；该类问题归验证环境/门禁，不归固件 FAIL。
- pretest 失败必须停止，不得用 `--skip-pretest` 绕过。
- 持续出现 `MCU is not ready!` 时不得下正式功能结论。
- 非预期重启优先级最高，不能被后续 PASS 吞掉。

## 执行器映射

- Trisolaris：`tools/burn_bundle/run_fan_burn.sh` / `.ps1`。
- mars-moon：`scripts/mars_moon_pipeline.py burn`。
- mars-belt：`scripts/mars_belt.py burn/full`。

## 回灌规则

- 新项目出现新的烧录时序、ready 标志或健康检查标志时，增加变体，不覆盖现有项目规则。
