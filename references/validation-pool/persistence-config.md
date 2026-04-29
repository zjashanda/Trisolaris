---
module_id: persistence-config
title: 配置默认值、掉电保存和恢复出厂
tags: [掉电保存, 持久化, config.clear, 恢复出厂, 默认值, 保存, reboot, 断电]
source_projects: [mars-moon, mars-belt, csk3022-htt, csk5062-xiaodu]
---

# 配置默认值、掉电保存和恢复出厂

## 适用需求特征

- 需求涉及默认值、保存开关、断电后保持/恢复、恢复出厂、配置清除。

## 变体维度

- 掉电保存 true/false。
- 恢复出厂恢复全部/部分配置。
- 设置后立即保存 / 延迟保存 / 需等待日志标记。
- 固件默认值依赖清配置后首次启动。

## 需求解析字段

- 配置项名、默认值、保存标志、保存完成日志、恢复动作、重启方式。

## 验证方案模板

1. 先确认当前默认态。
2. 设置成非默认值。
3. 等待保存闭环或超时策略。
4. 主动断电/重启。
5. 观察启动配置和后续行为。
6. 恢复出厂后重测默认态。

## 用例模板

- `CONFIG-DEFAULT-001`
- `CONFIG-PERSIST-ON-001`
- `CONFIG-PERSIST-OFF-001`
- `CONFIG-FACTORY-RESET-001`
- `CONFIG-CLEAR-BURN-001`

## 断言与证据

- 持久化必须先看到保存完成或按需求给足保存时间。
- 主动断电重启是测试动作，不算异常重启。
- 无法自动判断的配置保留人工项，不伪造 PASS。

## 执行器映射

- 好太太：`run_htt_followup_checks.py`。
- mars-moon：POWER / FACTORY 模块。
- mars-belt：wakeWordSave、volSave、defaultVol 包矩阵。

## 回灌规则

- 每个新保存项补充保存触发条件、保存证据和重启观察字段。
