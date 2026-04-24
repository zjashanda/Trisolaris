# Repo Workflow

## 当前范围

本仓库当前主线是 `CSK3022 好太太晾衣机` 离线语音验证。历史 CSK5062 风扇运行产物、报告日志、临时固件和旧专用脚本已清理，不再作为当前工作流输入。

## 启动流程

每轮在 `D:\revolution4s\Trisolaris` 内执行：

1. 读取 `plan.md`。
2. 明确本轮目标和待执行步骤。
3. 将执行中、已完成、待执行同步到 `plan.md`。
4. 需要判断证据时读取 `references/evidence-rules.md`。

## 输入目录

`项目需求/好太太晾衣机/` 只保留当前项目输入：

- `好太太晾衣机需求迭代.md`
- `电控词表协议--小好晾衣机语音词条协议-20260309.xlsx`
- `语音关闭逻辑.png`
- `当前有效需求清单_20260422.md`
- `fw-csk3022-htt-clothes-airer-v1.0.9.bin`

压缩包、解压副本、运行日志不放入需求目录。

## 输出目录

- `deliverables/csk3022_htt_clothes_airer/plan/`：最终方案、矩阵、缺陷、复测结论。
- `deliverables/csk3022_htt_clothes_airer/cases/`：保留的稳定用例定义。
- `result/`：本地原始执行证据，忽略 Git。
- `deliverables/*/reports/`：本地报告 bundle，忽略 Git。
- `audio_cache/`：本地 TTS 缓存，忽略 Git。

## 当前工具

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
- `tools/serial/fan_serial_maintenance.py`
- `tools/audio/fan_validation_helper.py`
- `tools/audio/listenai-play/scripts/listenai_play.py`
- `tools/burn_bundle/run_fan_burn.ps1`

## 固定端口

- `COM36 @ 9600`：协议证据口。
- `COM38 @ 115200`：日志/烧录证据口。
- `COM39 @ 115200`：上下电/boot 控制口。

## 执行节奏

1. 先确认协议握手 ready。
2. 再跑最小闭环：唤醒 -> 识别 -> 主动协议 -> 响应播报。
3. 数值项用实测值比对需求。
4. 主动协议看 `0x7F` 方向，被动播报看 `0x81` 注入方向。
5. 被动播报必须同时验证 play id。
6. 配置类功能要验证状态变化和后续恢复路径。
7. 每批执行后同步最终文档，不把原始日志 bundle 提交 Git。

## 清理规则

提交前应删除或忽略：

- `result/`
- `audio_cache/`
- `deliverables/*/reports/`
- `tools/burn_bundle/windows/app.bin`
- `tools/burn_bundle/windows/burn.log`
- `tools/burn_bundle/windows/burn_tool.log`
- 历史项目输入、重复方案版本、临时脚本、临时固件压缩包和解压副本。
