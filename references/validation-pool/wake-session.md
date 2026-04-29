---
module_id: wake-session
title: 唤醒、会话和超时
tags: [唤醒, 唤醒词, 会话, 超时, TIME_OUT, MODE=0, 未唤醒, 重唤醒]
source_projects: [mars-moon, mars-belt, csk3022-htt, csk5062-xiaodu]
---

# 唤醒、会话和超时

## 适用需求特征

- 有默认唤醒词、会话窗口、超时时间、未唤醒阻断或超时后重唤醒要求。

## 变体维度

- 唤醒后是否必须有主动协议。
- 超时起点：唤醒标志 / 播报结束 / 业务响应结束。
- 超时后命令：必须重唤醒 / 当前窗口可连续对话 / 设置窗口特殊处理。
- 模式差异：语音模式、嘀嗒模式、受限语音模式可能有不同提示。

## 需求解析字段

- 默认唤醒词、候选唤醒词、会话时长、提示音/play id、日志超时标记。
- 未唤醒命令是否应阻断。
- 超时后是否允许不重唤醒继续控制。

## 验证方案模板

1. 默认唤醒 smoke。
2. 唤醒后基础命令控制。
3. 未唤醒直接命令反例。
4. 会话超时值测量。
5. 超时后未重唤醒阻断。
6. 超时后重唤醒恢复。

## 用例模板

- `WAKE-DEFAULT-001`
- `SESSION-CMD-001`
- `SESSION-BLOCK-NO-WAKE-001`
- `SESSION-TIMEOUT-VALUE-001`
- `SESSION-TIMEOUT-BLOCK-001`
- `SESSION-REWAKE-RECOVER-001`

## 断言与证据

- 唤醒以日志 ASR/wakeup 和协议帧互证。
- 超时值优先用同一日志口时间差，跨串口只作旁证。
- 负例必须证明采集有效，不能用空采集假 PASS。
- 连续唤醒失败需止损并归为执行/环境问题先处理。

## 执行器映射

- 好太太：`run_htt_handshake_formal_suite.py`、`run_htt_numeric_probe.py`。
- mars-moon：`dooya_voice_runner.py`。
- mars-belt：`listenai_profile_suite.py` / weekly runner。

## 回灌规则

- 新项目如果有不同会话窗口或特殊设置态超时，新增变体和起点规则。
