---
name: trisolaris
description: 面向 D:\revolution4s\Trisolaris 的离线语音验证 skill。用于读取需求、拆解功能点、设计测试方案、执行好太太晾衣机 CSK3022 验证、烧录固件、控制 COM36/COM38/COM39、验证主动/被动协议和播报 ID、沉淀结果文档并同步 plan.md。
---

# Trisolaris 离线语音验证 Skill

## 启动要求

1. 进入 `D:\revolution4s\Trisolaris` 后先读取 `plan.md`；如果不存在就创建。
2. 每完成一个有意义的步骤，都要把已执行、执行中、待执行同步回 `plan.md`。
3. 判断协议、播报、持久化、PASS/FAIL/BLOCKED 前，优先读取 `references/evidence-rules.md`。
4. 当前项目主线是 `CSK3022 好太太晾衣机`，历史 CSK5062 风扇运行产物不再作为当前验证输入。

## 当前输入

- 需求目录：`项目需求/好太太晾衣机/`
- 需求文档：`好太太晾衣机需求迭代.md`
- 词表协议：`电控词表协议--小好晾衣机语音词条协议-20260309.xlsx`
- 状态图：`语音关闭逻辑.png`
- 固件：`fw-csk3022-htt-clothes-airer-v1.0.9.bin`
- 需求设计方法参考：`references/需求功能验证设计方法.md`

需求目录只放输入材料，不放执行日志、报告 bundle、音频缓存或临时脚本。

## 当前输出

- 最终方案/矩阵/缺陷文档：`deliverables/csk3022_htt_clothes_airer/plan/`
- 稳定用例定义：`deliverables/csk3022_htt_clothes_airer/cases/`
- 原始运行证据：`result/`，仅本地使用，不提交 Git。
- 报告 bundle：`deliverables/*/reports/`，仅本地使用，不提交 Git。

## 固定硬件口径

- `COM36 @ 9600`：协议串口，作为主动/被动协议正式证据。
- `COM38 @ 115200`：日志/烧录串口，用于识别、播报、play id、超时、启动配置等证据。
- `COM39 @ 115200`：上下电和 boot 控制。
- 音频播放设备必须先确认路由；音频链路异常不能直接判固件 FAIL。

## 当前脚本入口

优先使用仓库内脚本，不要临时复制散落脚本：

- `tools/debug/run_htt_handshake_formal_suite.py`：握手仿真 + 主链正式验证。
- `tools/debug/run_htt_numeric_probe.py`：唤醒超时、默认音量、音量档位和边界探测。
- `tools/debug/run_htt_active_passive_playid_sweep.py`：主动协议、被动协议、播报 ID sweep。
- `tools/debug/run_htt_followup_checks.py`：稳定 FAIL follow-up 复测。
- `tools/debug/run_htt_voice_restricted_probe.py`：语音关闭受限态、10s 窗口、play id 77/123。
- `tools/debug/run_htt_active_only_remaining.py`：active-only 命令全量/复测。
- `tools/debug/run_htt_active_only_phrase_probe.py`：active-only 别名排查。
- `tools/debug/run_htt_pyaudio_route_probe.py`：音频路由排查。
- `tools/debug/run_listenai_endpoint_meter_probe.py`：播放设备链路探测。
- `tools/serial/fan_proto_handshake_probe.py`：品牌应答、心跳应答、MCU 查询握手仿真。
- `tools/serial/fan_serial_maintenance.py`：串口维护与上电抓取辅助。

## 烧录规则

烧录只走仓库包装入口：

- Windows：`tools/burn_bundle/run_fan_burn.ps1`
- Linux：`tools/burn_bundle/run_fan_burn.sh`

规则：

1. wrapper 负责删除旧 `app.bin`。
2. wrapper 负责把目标固件复制为 staging `app.bin`。
3. 烧录后必须同时看烧录日志成功标记和 `COM38` 启动版本。
4. `tools/burn_bundle/windows/app.bin`、`burn.log`、`burn_tool.log` 是运行产物，不提交。

## 需求拆解原则

每个需求点都要落到可验证结构：

- 需求解析：需求是什么、来自哪个文档/变更口径。
- 验证方案：用什么入口、什么状态、什么证据链。
- 用例：前置条件、步骤、正例、反例、异常场景。
- 断言：主断言和辅助断言分开。
- 执行结果：PASS/FAIL/BLOCKED 必须有证据，不能只贴日志路径。

## 数值验证原则

数值类参数必须先实测再比对需求，禁止“按需求等待固定时间后反推”。

- 唤醒超时：分别验证纯唤醒不说命令、唤醒后说命令且播报结束后的超时；起点可取唤醒发送协议、唤醒识别日志或唤醒响应播报结束，终点必须结合 `TIME_OUT` 和 `MODE=0`。
- 音量默认值：恢复出厂后通过逐步增大/减小刺探到边界，再结合总档位反推出默认位置。
- 音量档位：从下边界逐步调到上边界，再从上边界逐步调到下边界，按有效步进数确认档位。
- 被动播报 ID：注入 MCU -> CSK 的 `0x81` 帧后，必须同时断言播报行为和 play id。

## 好太太握手基线

正式验证前必须先让 CSK 进入 ready：

1. CSK 发品牌查询 `A5 FA 7F 01 02 21 FB`，MCU/仿真器回 `A5 FA 81 00 20 40 FB`。
2. CSK 发心跳 `A5 FA 7F 5A 5A D2 FB`，MCU/仿真器回 `A5 FA 83 5A 5A D6 FB`。
3. MCU 可周期发 `A5 FA 83 A5 A5 6C FB`，CSK 应回 `A5 FA 7F A5 A5 68 FB`。
4. 若 `COM38` 持续出现 `MCU is not ready!`，先修握手，不进入功能结论。

## 结论规则

- `PASS`：功能路径执行完成，主断言和关键辅助证据一致。
- `FAIL`：路径可执行，但固件行为与需求冲突。
- `BLOCKED`：端口、音频、烧录、ready 状态等条件不足，不能判断功能。
- `TODO`：已规划但未执行。

不要把“没抓到日志”直接写成“功能不存在”；必须先排除端口占用、窗口过短、状态不对、握手未 ready、音频路由异常。

## 清理与同步规则

- 保留当前有效需求输入、最终方案/用例/缺陷文档、当前 HTT 脚本和共享工具。
- 删除或忽略历史报告、运行结果、音频缓存、烧录 staging、重复方案版本和旧项目专用逻辑。
- 提交前执行 `git status --short`、必要脚本的 `py_compile`、目录体积统计。
