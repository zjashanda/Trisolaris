---
module_id: broadcast-play-id
title: 播报、tone 和 play id 验证
tags: [播报, play id, tone, 提示音, 设置成功, 设置失败, 咚]
source_projects: [csk3022-htt, csk5062-xiaodu, mars-moon, mars-belt]
---

# 播报、tone 和 play id 验证

## 适用需求特征

- 需求定义播报文案、tone id、play id、提示音或成功/失败提示。

## 变体维度

- 语音播报 / 提示音 / 静默不播报。
- 模式差异播报：语音模式、滴答模式、静音/播报关闭。
- 字符串 TTS 参数：可能只能配置断言，不能自动判听感。

## 需求解析字段

- 触发动作、期望 play id/tone、是否允许额外播报、播报开关状态、模式状态。

## 验证方案模板

1. 建立正确前置状态。
2. 触发动作。
3. 采集日志中的 play id、play start、play stop。
4. 过滤前置/恢复动作产生的播报。
5. 与需求的播报/不播报/提示音规则比对。

## 用例模板

- `BROADCAST-PLAYID-001`
- `BROADCAST-NO-EXTRA-001`
- `BROADCAST-SETTING-FAIL-001`
- `BROADCAST-MODE-001`

## 断言与证据

- 不使用人耳作为自动化结论。
- 断言必须限定目标动作之后的播报窗口，避免恢复默认或启动播报污染。
- 设置类不能只看“设置成功”播报，还要验证状态生效。

## 执行器映射

- 好太太：`run_htt_active_passive_playid_sweep.py`、`run_htt_followup_checks.py`。
- mars-moon：tone map + runner。
- mars-belt：欢迎语/上下溢播报以配置断言 + 稳定性为主。

## 回灌规则

- 新 play id 只写入项目矩阵；通用池只记录“如何断言和隔离播报”。
