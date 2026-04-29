---
module_id: active-protocol
title: 主动协议输出验证
tags: [主动协议, send msg, 发送协议, 命令词, 控制命令, UART]
source_projects: [csk3022-htt, csk5062-xiaodu, mars-moon]
---

# 主动协议输出验证

## 适用需求特征

- 语音识别后设备应主动向 MCU/外部控制器发送协议。
- 需求表包含命令词和发送协议。

## 变体维度

- 只验证主动协议；或必须同时验证播报；或必须等被动回包后验证状态。
- 协议字段方向：CSK -> MCU 与 MCU -> CSK 同码时必须区分方向。
- 无固定回包时，只收敛到主动侧，不强行断言本地副作用。

## 需求解析字段

- 唤醒词、命令词、主动协议值、协议口、波特率、是否有被动回包列。

## 验证方案模板

1. 前置 ready。
2. 唤醒。
3. 播放目标命令词。
4. 协议口捕获主动帧。
5. 若需求有播报要求，补播报断言。
6. 若需求有本地状态变化，转入 `active-passive-closed-loop`。

## 用例模板

- `ACTIVE-CMD-<feature>-001`
- `ACTIVE-ONLY-<feature>-001`
- `ACTIVE-ALIAS-<feature>-001`

## 断言与证据

- 主断言使用协议 UART 原始帧。
- 日志 `send msg` 只作辅助。
- TTS 短语稳定误打到同表邻近意图时，先按同需求行官方别名收敛。

## 执行器映射

- 好太太：`run_htt_active_only_remaining.py`、`run_htt_active_passive_playid_sweep.py`。
- 小度：正式用例 runner。
- mars-moon：`dooya_voice_runner.py`。

## 回灌规则

- 新项目主动协议格式或校验方式不同，新增协议解析变体，不替换已有协议解析。
