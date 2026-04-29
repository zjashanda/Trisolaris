---
module_id: volume-level
title: 音量档位、默认值和边界验证
tags: [音量, 默认音量, 档位, 最大音量, 最小音量, 边界, volLevel, defaultVol]
source_projects: [mars-belt, csk3022-htt, csk5062-xiaodu]
---

# 音量档位、默认值和边界验证

## 适用需求特征

- 需求包含默认音量、音量档位数、最大/最小音量、音量掉电保存或上下溢播报。

## 变体维度

- 默认值来自固件配置 / 平台打包参数 / 运行时配置。
- 音量改变是否需要 MCU 回包。
- 档位编码是否等于用户可见档位。
- 是否支持保存当前音量。

## 需求解析字段

- `volLevel`、`defaultVol`、音量命令、边界播报、保存开关、配置刷新日志。

## 验证方案模板

1. 清配置或恢复出厂建立默认态。
2. 从默认位单边探测到上/下边界。
3. 双边探测得到总档位数。
4. 用边界步数反推默认档位。
5. 边界后再次操作验证上溢/下溢播报。
6. 如验证保存，设置非默认音量后等待保存再重启。

## 用例模板

- `VOLUME-DEFAULT-001`
- `VOLUME-TOTAL-STEPS-001`
- `VOLUME-UP-001`
- `VOLUME-DOWN-001`
- `VOLUME-MAX-BOUNDARY-001`
- `VOLUME-MIN-BOUNDARY-001`
- `VOLUME-PERSIST-001`

## 断言与证据

- 不能直接用启动 raw 编码等同用户档位。
- 默认音量必须在前序音量操作污染前测。
- 需要回包的项目必须先闭环回包再读本地音量。
- `config.clear -> reboot -> burn` 可用时优先使用固件默认值。

## 执行器映射

- 好太太：`run_htt_numeric_probe.py`、`run_htt_followup_checks.py`。
- mars-belt：`probe_volume_levels.py`、profile suite。
- 小度：`run_timeout_volume_probe.py`。

## 回灌规则

- 新项目发现档位编码和用户档位映射不同，新增映射策略，不替换边界探测原则。
