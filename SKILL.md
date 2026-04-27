---
name: trisolaris
description: Trisolaris 多项目离线语音验证 skill。用于读取项目需求目录，解析需求和协议/词表，设计验证方案与正式用例，烧录固件，驱动声卡播放语音，采集协议/日志/控制串口证据，修正断言问题，执行全链路验证，并沉淀 CSK5062 小度风扇、CSK3022 好太太晾衣机及后续离线语音项目的可复用测试逻辑。
---

# Trisolaris 多项目离线语音验证

## 启动规则

1. 每次开始任务先读取仓库根目录 `plan.md`；不存在就创建。
2. 每完成一个有意义动作，及时把已完成、进行中、待执行同步到 `plan.md`。
3. 处理新需求、需求变更、全链路执行、断言收敛或 skill 发布前，先读 `references/fullflow-validation-method.md`。
4. 判断协议、播报、持久化、PASS/FAIL/BLOCKED、人工项前，先读 `references/evidence-rules.md`。
5. 根据用户给出的需求路径或项目名选择当前项目；不同项目的方案、用例、报告和运行证据不能互相覆盖。

## 目录规则

- 需求输入统一放在项目输入目录，例如 `项目需求/CSK5062小度风扇需求/`、`项目需求/好太太晾衣机/`。
- 稳定交付物按项目放在 `deliverables/<project_key>/plan/`、`deliverables/<project_key>/cases/`、`deliverables/<project_key>/archive/`。
- 运行证据只放本地：`result/` 或 `deliverables/<project_key>/reports/`；默认不提交原始日志、音频缓存、烧录 staging、临时固件。
- 新项目进入时，优先新增独立 `deliverables/<project_key>/`；只有共享 runner 无法安全参数化时，才新增项目专用 runner。

## 当前项目画像

### CSK5062 小度风扇

- 输入目录：`项目需求/CSK5062小度风扇需求/`
- 输出目录：`deliverables/csk5062_xiaodu_fan/`
- 主要脚本：
  - `tools/cases/generate_formal_assets.py`
  - `tools/cases/export_case_md_to_xlsx.py`
  - `tools/debug/run_post_restructure_fullflow.py`
  - `tools/debug/run_missing_nonreg_cases.py`
  - `tools/debug/run_remaining_voice_reg_batch.py`
  - `tools/debug/generate_full_formal_aggregate.py`
  - `tools/debug/apply_fresh_full_suite_convergence.py`
  - `tools/debug/run_fresh_closure_targets.py`
  - `tools/debug/run_timeout_volume_probe.py`
- 小度项目已包含语音注册专项：入口、命令词学习、唤醒词学习、删除、退出删除、失败重试、冲突词、模板上限、掉电保持和配置一致性。
- Linux 端口以用户输入为准；最近本地映射为：日志/烧录 `/dev/ttyACM0`，协议 `/dev/ttyACM2`，控制/boot `/dev/ttyACM4`，声卡 key `VID_8765&PID_5678:USB_0_4_3_1_0`。

### CSK3022 好太太晾衣机

- 输入目录：`项目需求/好太太晾衣机/`
- 输出目录：`deliverables/csk3022_htt_clothes_airer/`
- 主要脚本：
  - `tools/debug/run_htt_handshake_formal_suite.py`
  - `tools/debug/run_htt_numeric_probe.py`
  - `tools/debug/run_htt_active_passive_playid_sweep.py`
  - `tools/debug/run_htt_followup_checks.py`
  - `tools/debug/run_htt_voice_restricted_probe.py`
  - `tools/debug/run_htt_active_only_remaining.py`
  - `tools/debug/run_htt_active_only_phrase_probe.py`
  - `tools/debug/run_htt_pyaudio_route_probe.py`
  - `tools/debug/run_listenai_endpoint_meter_probe.py`
  - `tools/serial/fan_proto_handshake_probe.py`
- 功能判断前必须闭合 MCU ready：品牌查询、心跳、ready 响应都要处理；持续出现 `MCU is not ready!` 时不得下正式功能结论。
- 当前好太太需求里的“注册声纹”已按需求删除/无效范围处理，不作为正向语音注册功能验证项。

## 硬件与烧录规则

- 默认 Windows 映射：协议 `COM36 @ 9600`，日志/烧录 `COM38 @ 115200`，控制/boot `COM39 @ 115200`。
- Linux 映射必须来自用户或本地探测；如果用户已明确 `/dev/ttyACM*`，不得自行猜测顺序。
- 烧录只使用仓库封装入口：Windows 用 `tools/burn_bundle/run_fan_burn.ps1`，Linux 用 `tools/burn_bundle/run_fan_burn.sh`。
- 所有项目在继电器夹具上的统一烧录时序：断电 -> 进 BOOT -> 上电 -> 保持 BOOT `PreBurnWaitMs`，默认 `6000ms` -> 下 BOOT -> 启动 `Uart_Burn_Tool`。
- `6000ms` 等待必须发生在 `uut-switch1.on` 之后、`uut-switch2.off` 之前。
- 若设备支持 `config.clear` 或等价全配置清除，验证固件默认值前必须执行 `config.clear -> reboot -> burn`。
- 烧录闭环不能只看工具退出码，必须同时确认烧录成功标记和日志口启动版本。

## 验证流程

1. 解析需求文档、协议表、词表、流程图、固件和用户最新澄清，拆成可测试功能点。
2. 为当前项目生成或刷新测试方案和正式用例。
3. 烧录固件，并先完成最小可测性门禁，再进入全量执行。
4. 串行执行验证；同一组协议/日志串口不能被多个采集任务并发占用。
5. 每个执行批次完成后聚合项目用例状态。
6. raw FAIL 若来自断言逻辑、空采集、状态污染、保存闭环缺失、前置条件未闭合、TTS 短语误选或 MCU 回包缺失，必须先修验证路径并重跑。
7. 最终 FAIL 只能保留两类：固件不满足需求，或需求本身错误/矛盾。
8. 最终结果同步到项目用例资产和 `plan.md`。

## 证据规则

- 协议结论以协议 UART 原始帧为准；日志里的 `send msg::` 只作辅助。
- 识别、播报、保存、启动配置、超时、play id 以日志 UART 为主。
- 播报结论看 play id、`play start`、`play stop`，不得用人耳判断。
- 持久化结论必须先看到保存完成，再断电或重启。
- 负向用例必须证明采集有效；不能因为空采集直接判 PASS。
- 人工项或当前环境不可自动化的内容保留为 `TODO` / manual / BLOCKED，不能伪造成 PASS 或固件 FAIL。

## 固定断言规则

- 唤醒超时：从响应播报结束或 `0x0001/Wakeup` 到 `TIME_OUT/MODE=0` 测真实时间，再比对需求；纯唤醒和唤醒后命令两条路径都要一致。
- 音量档位：先锚定最小/最大边界，再做 min->max、max->min 双向探测，用运行时 `mini player set vol` 阶梯判断档位对称性。
- 默认音量：`config.clear -> reboot -> burn` 后抓首启 `Running Config`，从默认位单边探到边界，再双边探总档位，用边界步数反推默认档位。
- 音量持久化：等待 `refresh config volume=` 或保存闭环后再重启；重启后和当前需求比对，不和写死默认值比对。
- HTT 主动命令若只是上报 MCU，本地副作用必须等 MCU 被动确认后再断言；例如主动音量 `0x0041/0x0042` 需要回同码被动协议，主动关闭语音 `0x0016` 需要回被动 `0x0012`。
- HTT 全链路命令覆盖中，单个 TTS 短语若稳定误打到同表邻近意图，先使用同一需求行的官方别名做探测收敛；别名通过时不得把 TTS 选择问题留成最终 FAIL。
- 语音注册命令词共存：必须有保存闭环、重启、学习别名复测、原默认命令复测；若目标控制帧在已激活会话中出现，即使未重复唤醒帧也可作为有效控制证据。
- 模板满检查：必须在用例内主动填满模板、观察保存、重启、再进入学习流程；不得只用启动 `regCmdCount` 推断模板已满。
- 冲突词检查：必须使用词表中的真实 spoken phrase；默认唤醒词冲突这类随机性场景，要从干净基线重复确认后才能保留固件 FAIL。

## 报告与发布

- Markdown 报告使用中文标题和正文，尽量保持 Windows 友好的 UTF-8。
- 报告必须区分 PASS、FAIL、BLOCKED、TODO/manual。
- 最终 FAIL 清单不得包含验证方案、用例设计或断言问题。
- 发布前运行相关 `py_compile` 或 skill 校验，检查 `git status --short`。
- 不提交运行证据、音频缓存、烧录临时文件、日志、`__pycache__`。
- 合并或发布时不得删除其他项目资产；多项目内容要按目录融合。
