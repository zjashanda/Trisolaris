# Trisolaris

Trisolaris 是离线语音项目的本地验证仓库。当前主线服务于 `CSK3022 好太太晾衣机` 项目，保留可复用的烧录、串口、音频播放、需求验证和报告沉淀能力。

## 当前范围

- 需求输入：`项目需求/好太太晾衣机/`
- 稳定交付：`deliverables/csk3022_htt_clothes_airer/plan/`、`deliverables/csk3022_htt_clothes_airer/cases/`
- 执行脚本：`tools/debug/run_htt_*.py`
- 协议/串口工具：`tools/serial/`
- 音频与播放工具：`tools/audio/`
- 烧录工具：`tools/burn_bundle/`

历史运行目录、报告日志、音频缓存和临时固件不进入 Git；本地运行时按需重新生成。

## 固定端口

- `COM36 @ 9600`：协议串口，作为主动/被动协议结论的正式证据口。
- `COM38 @ 115200`：日志/烧录串口，采集识别、播报、play id、`TIME_OUT`、`MODE=0`、启动配置等证据。
- `COM39 @ 115200`：上下电和 boot 控制口。

## 常用入口

- 最小握手与正式主链：`tools/debug/run_htt_handshake_formal_suite.py`
- 数值验证：`tools/debug/run_htt_numeric_probe.py`
- 主动/被动协议与播报 ID：`tools/debug/run_htt_active_passive_playid_sweep.py`
- 语音关闭受限态：`tools/debug/run_htt_voice_restricted_probe.py`
- 后续缺陷复测：`tools/debug/run_htt_followup_checks.py`
- active-only 命令复测：`tools/debug/run_htt_active_only_remaining.py`
- 协议握手仿真：`tools/serial/fan_proto_handshake_probe.py`

## 验证口径

- 先跑最小闭环：协议握手 ready -> 唤醒 -> 识别 -> 主动协议 -> 响应播报。
- 数值项必须先实测再比对需求，不能用需求值反推结论。
- 唤醒超时以响应结束到 `TIME_OUT` + `MODE=0` 的真实时长为准，并覆盖纯唤醒和唤醒后命令两条路径。
- 音量默认值、档位数、边界通过逐步增大/减小探测，结合上下边界计算。
- 被动播报由 `COM36` 注入 MCU -> CSK 的 `0x81` 帧，同时断言播报 ID。
- 主动控制由 `COM36` 捕获 CSK -> MCU 的 `0x7F` 帧，不用 `COM38 send msg` 替代正式协议证据。

## 保留文档

当前保留的好太太最终文档集中在：

- `deliverables/csk3022_htt_clothes_airer/plan/20260424_需求_验证方案_用例_执行详表_v1.md`
- `deliverables/csk3022_htt_clothes_airer/plan/20260424_FAIL用例详细输出_v1.md`
- `deliverables/csk3022_htt_clothes_airer/plan/20260424_FAIL归因分类_v1.md`
- `deliverables/csk3022_htt_clothes_airer/plan/20260424_稳定FAIL缺陷清单_v2.md`
- `deliverables/csk3022_htt_clothes_airer/plan/20260424_按修复建议复测结论_v2.md`

## 工作规则

1. 每轮先读取并更新 `plan.md`。
2. 需求、方案、用例、执行结果必须一一对应。
3. PASS/FAIL/BLOCKED 不伪造；环境问题归 BLOCKED，固件行为不符合需求归 FAIL。
4. 日志、报告 bundle、音频缓存、烧录 staging 文件都视为运行产物，不提交到 Git。
