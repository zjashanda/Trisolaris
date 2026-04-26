# Trisolaris

Trisolaris 是离线语音项目的多项目本地验证 skill 仓库。当前同时保留并融合：

- `CSK5062 小度风扇`：烧录、需求解析、方案/用例生成、全链路执行、断言收敛。
- `CSK3022 好太太晾衣机`：协议握手仿真、主动/被动协议、数值探测、缺陷复测。

仓库目标不是固定到单一项目，而是新项目进来后能按对应需求目录生成测试方案、正式用例、执行链路和最终归因。

## 项目目录

- 小度风扇输入：`CSK5062小度风扇需求/`
- 小度风扇交付：`deliverables/csk5062_xiaodu_fan/plan/`、`deliverables/csk5062_xiaodu_fan/cases/`、`deliverables/csk5062_xiaodu_fan/archive/`
- 好太太输入：`项目需求/好太太晾衣机/`
- 好太太交付：`deliverables/csk3022_htt_clothes_airer/plan/`、`deliverables/csk3022_htt_clothes_airer/cases/`
- 通用工具：`tools/audio/`、`tools/serial/`、`tools/burn_bundle/`

运行报告、原始日志、音频缓存、烧录 staging 都是本地运行产物，默认不进入 Git。

## 常用入口

### CSK5062 小度风扇

- 静态资产生成：`tools/cases/generate_formal_assets.py`
- 主全链路：`tools/debug/run_post_restructure_fullflow.py`
- 缺失非注册补充：`tools/debug/run_missing_nonreg_cases.py`
- 语音注册补充：`tools/debug/run_remaining_voice_reg_batch.py`
- 全量聚合：`tools/debug/generate_full_formal_aggregate.py`
- 最终收敛：`tools/debug/apply_fresh_full_suite_convergence.py`
- 超时/音量探针：`tools/debug/run_timeout_volume_probe.py`
- targeted closure：`tools/debug/run_fresh_closure_targets.py`

### CSK3022 好太太晾衣机

- 握手仿真正式套件：`tools/debug/run_htt_handshake_formal_suite.py`
- 数值验证：`tools/debug/run_htt_numeric_probe.py`
- 主动/被动协议与播报 ID：`tools/debug/run_htt_active_passive_playid_sweep.py`
- 语音关闭受限态：`tools/debug/run_htt_voice_restricted_probe.py`
- 后续缺陷复测：`tools/debug/run_htt_followup_checks.py`
- 协议握手仿真：`tools/serial/fan_proto_handshake_probe.py`

## 验证口径

- 每轮先读写 `plan.md`，保持 done / doing / todo 同步。
- 需求、方案、用例、执行结果必须一一对应；数值项必须先实测再比对需求。
- 串口证据优先级：协议 UART 原始帧用于协议结论，日志 UART 用于识别、播报、保存、启动配置、超时等结论。
- 如果 raw FAIL 来自断言、采集、状态污染、保存闭环缺失或前置条件未闭合，先修验证逻辑并重跑；最终 FAIL 只允许是固件问题或需求错误。
- 有 `config.clear` 等全配置清除指令时，验证固件默认值前必须执行 `config.clear -> reboot -> burn`，确保默认值来自固件本身。
- 默认音量按单边探测 + 双边边界探测计算真实默认档位，不能直接用启动 raw 值或需求值反推。
- 报告正文使用中文，区分 PASS / FAIL / BLOCKED / TODO；不把环境问题或人工项伪造成固件 FAIL。

## 当前小度风扇 Linux 设备映射

- 日志/烧录：`/dev/ttyACM0`
- 协议：`/dev/ttyACM2`
- 控制/boot：`/dev/ttyACM4`
- 声卡 key：`VID_8765&PID_5678:USB_0_4_3_1_0`

## 清理与提交

提交前应清理或保持忽略：

- `result/`
- `audio_cache/`
- `deliverables/*/reports/`
- `tools/burn_bundle/*/app.bin`
- `tools/burn_bundle/*/burn.log`
- `tools/burn_bundle/*/burn_tool.log`
- `__pycache__/`、`.venv/`、临时固件压缩包和解压目录
