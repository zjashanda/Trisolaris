---
module_id: multi-wake
title: 多唤醒、切换和掉电保持
tags: [多唤醒, 唤醒词切换, 查询唤醒词, 恢复默认唤醒词, wakeWordSave, 当前唤醒词]
source_projects: [mars-belt, mars-moon, csk5062-xiaodu]
---

# 多唤醒、切换和掉电保持

## 适用需求特征

- 需求包含多个唤醒词、切换当前词、查询当前词、恢复默认词或唤醒词掉电保存。

## 变体维度

- 默认词是否始终保留可用。
- 非当前词是否必须失效。
- 切换模式：指定模式、循环模式、协议模式。
- `wakeWordSave=true/false` 后重启保持/恢复默认。

## 需求解析字段

- 默认唤醒词、额外唤醒词、切换命令、查询命令、恢复默认命令、保存开关。

## 验证方案模板

1. 新增或确认至少 2 个额外唤醒词。
2. 默认词可唤醒。
3. 切换到目标词。
4. 当前词可唤醒。
5. 非当前词反例。
6. 查询当前词。
7. 恢复默认词。
8. 掉电保持/恢复默认验证。

## 用例模板

- `MWK-DEFAULT-001`
- `MWK-SWITCH-001`
- `MWK-CURRENT-WAKE-001`
- `MWK-NONCURRENT-BLOCK-001`
- `MWK-QUERY-001`
- `MWK-RESTORE-DEFAULT-001`
- `MWK-SAVE-001`

## 断言与证据

- 切换成功播报不等于当前词隔离正确。
- 非当前词反例必须证明播放和采集有效。
- `wakeWordSave` 问题要区分“保存开关有效”与“运行态隔离失效”。

## 执行器映射

- mars-belt：multi-wke 包和 weekly runner。
- mars-moon：WAKEWORD/SELECTOR 模块。
- 小度：语音注册/唤醒词学习专项。

## 回灌规则

- 新模式必须单独得出结论，不能把 specified/loop/protocol 混成一条。
