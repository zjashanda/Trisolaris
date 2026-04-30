# Trisolaris

Trisolaris 是离线语音项目的多项目本地验证 skill 仓库。当前同时保留并融合：

- `CSK5062 小度风扇`：烧录、需求解析、方案/用例生成、全链路执行、断言收敛。
- `CSK3022 好太太晾衣机`：协议握手仿真、主动/被动协议、数值探测、缺陷复测。

仓库目标不是固定到单一项目，而是新项目进来后能按对应需求目录生成测试方案、正式用例、执行链路和最终归因。

## 复用入口

- 新项目或需求变更的完整方法：`references/fullflow-validation-method.md`
- 模块化需求解析和验证池工作流：`references/modular-validation-workflow.md`
- 功能拆解、方案、用例和断言池：`references/validation-pool/INDEX.md`
- 项目识别与执行适配：`references/project-profiles/`
- 证据与归因规则：`references/evidence-rules.md`
- 仓库和运行产物规则：`references/repo-workflow.md`

## 项目目录

- 小度风扇输入：`项目需求/CSK5062小度风扇需求/`
- 小度风扇交付：`deliverables/csk5062_xiaodu_fan/plan/`、`deliverables/csk5062_xiaodu_fan/cases/`、`deliverables/csk5062_xiaodu_fan/archive/`
- 好太太输入：`项目需求/好太太晾衣机/`
- 好太太交付：`deliverables/csk3022_htt_clothes_airer/plan/`、`deliverables/csk3022_htt_clothes_airer/cases/`
- 好太太当前最新收敛口径：`deliverables/csk3022_htt_clothes_airer/plan/20260428_好太太最终收敛方案与结果_v1.md`
- 通用工具：`tools/audio/`、`tools/serial/`、`tools/burn_bundle/`
- 模块化验证池辅助工具：`tools/pool/validation_pool.py`
- 通用正式全集入口：`tools/suite/run_formal_suite.py`

运行报告、原始日志、音频缓存、烧录 staging 都是本地运行产物，默认不进入 Git。

## 常用入口

### 通用正式全集

- 首选入口：`tools/suite/run_formal_suite.py`
- profile 目录：`references/project-profiles/`
- 入口职责：项目识别、验证池匹配、烧录/gate、分组执行、targeted overlay、全集聚合和统一报告。
- 项目差异必须写在 profile/adapter 或项目 runner 里，不能写死到通用入口。

示例：

```bash
python3 tools/suite/run_formal_suite.py \
  --req-dir 项目需求/CSK5062小度风扇需求 \
  --project csk5062_xiaodu_fan \
  --log-port /dev/ttyACM0 \
  --proto-port /dev/ttyACM2 \
  --ctrl-port /dev/ttyACM4 \
  --device-key 'VID_8765&PID_5678:USB_0_4_3_1_0'
```

### CSK5062 小度风扇

- 当前已接入通用正式全集入口：`tools/suite/run_formal_suite.py`
- 小度 profile：`references/project-profiles/csk5062_xiaodu_fan.json`
- 小度 adapter 内部使用的项目脚本：
  - `tools/cases/generate_formal_assets.py`
  - `tools/debug/run_post_restructure_fullflow.py`
  - `tools/debug/run_missing_nonreg_cases.py`
  - `tools/debug/run_remaining_voice_reg_batch.py`
  - `tools/debug/run_xiaodu_regcfg005_closure.py`
  - `tools/debug/generate_full_formal_aggregate.py`
  - `tools/debug/run_timeout_volume_probe.py`
  - `tools/debug/run_fresh_closure_targets.py`

### CSK3022 好太太晾衣机

- 握手仿真正式套件：`tools/debug/run_htt_handshake_formal_suite.py`
- 数值验证：`tools/debug/run_htt_numeric_probe.py`
- 主动/被动协议与播报 ID：`tools/debug/run_htt_active_passive_playid_sweep.py`
- 语音关闭受限态：`tools/debug/run_htt_voice_restricted_probe.py`
- 语音开关状态机：`tools/debug/run_htt_voice_switch_state_machine_probe.py`
- 后续缺陷复测：`tools/debug/run_htt_followup_checks.py`
- 协议握手仿真：`tools/serial/fan_proto_handshake_probe.py`

## 验证口径

- 每轮先读写 `plan.md`，保持 done / doing / todo 同步。
- 新项目必须先匹配 `references/validation-pool/`，不能直接套旧项目 deliverables 的方案或断言。
- 同一个功能需求点在不同项目中可能有不同实现、方案和断言；必须按当前需求选择模块变体。
- 需求、方案、用例、执行结果必须一一对应；数值项必须先实测再比对需求。
- 串口证据优先级：协议 UART 原始帧用于协议结论，日志 UART 用于识别、播报、保存、启动配置、超时等结论。
- 如果 raw FAIL 来自断言、采集、状态污染、保存闭环缺失或前置条件未闭合，先修验证逻辑并重跑；最终 FAIL 只允许是固件问题或需求错误。
- Linux `/dev/ttyACM*` 端口必须过门禁：控制口要实测能 power-cycle/boot，协议口要实测能收主动帧和发被动帧；端口枚举漂移或注入时机问题只算验证环境问题，不能算最终固件 FAIL。
- 有 `config.clear` 等全配置清除指令时，验证固件默认值前必须执行 `config.clear -> reboot -> burn`，确保默认值来自固件本身。
- 默认音量按单边探测 + 双边边界探测计算真实默认档位，不能直接用启动 raw 值或需求值反推。
- 好太太这类“主动命令上报 MCU、MCU 回包后模块才改变本地状态”的链路，断言本地副作用前必须补齐 MCU 被动回包；例如主动调音量需回同码被动协议。语音开关当前实测口径为主动关闭 `0x0016 -> 0x0036`、主动打开 `0x0017 -> 0x0037`，被动 `0x0012` 是 MCU 直接关闭语音的独立入口。
- 单个 TTS 短语若稳定打到同表邻近意图，应先用同一需求行的官方别名做探测收敛，不能把纯短语/TTS 选择问题留成最终功能 FAIL。
- 报告正文使用中文，区分 PASS / FAIL / BLOCKED / TODO；不把环境问题或人工项伪造成固件 FAIL。
- 新需求执行收敛后，通用逻辑回灌 `references/validation-pool/`，项目特定码值和结论留在 `deliverables/<project_key>/`。

## 当前 Linux 设备映射参考

- 日志/烧录：`/dev/ttyACM0`
- 协议：`/dev/ttyACM2`
- 控制/boot：以用户口径和本地门禁为准；最近用户口径为 `/dev/ttyACM4`，若 power-cycle/boot 不生效需重新探测当前枚举。
- 声卡 key：`VID_8765&PID_5678:USB_0_4_3_1_0`

## 统一烧录时序

- Linux 统一入口：`tools/burn_bundle/run_fan_burn.sh`
- Windows 统一入口：`tools/burn_bundle/run_fan_burn.ps1`
- 所有项目统一进入烧录时序：断电 -> 进 boot -> 上电 -> 上电后保持 boot 6s -> 下 boot -> 启动 `Uart_Burn_Tool`
- 脚本默认 `-PreBurnWaitMs 6000`，且等待位置必须在 `uut-switch1.on` 之后、`uut-switch2.off` 之前。
- 烧录成功不能只看工具 exit code；必须同时看到 `SEND END COMMAND SUCCESS`、`SEND MD5 COMMAND WITH RAM SUCCESS`、`CONNECT ROM AND DOWNLOAD RAM LOADER SUCCESS`。

## 清理与提交

提交前应清理或保持忽略：

- `result/`
- `audio_cache/`
- `deliverables/*/reports/`
- `tools/burn_bundle/*/app.bin`
- `tools/burn_bundle/*/burn.log`
- `tools/burn_bundle/*/burn_tool.log`
- `__pycache__/`、`.venv/`、临时固件压缩包和解压目录
