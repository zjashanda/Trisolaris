# Gherkin 用例建模规则

## Feature 粒度

Feature 应按验证池模块或需求功能域拆分，不按脚本文件拆分。

推荐 Feature：

- `burn_and_gate.feature`
- `wake_session.feature`
- `active_protocol.feature`
- `passive_protocol.feature`
- `active_passive_closed_loop.feature`
- `broadcast_play_id.feature`
- `volume_level.feature`
- `persistence_config.feature`
- `voice_switch_state_machine.feature`
- `voice_register.feature`
- `negative_abnormal.feature`

## Scenario 粒度

一个 Scenario 对应一个正式用例 ID。用例 ID 放在 tag 或标题中，便于聚合到 `case_results.json`。

示例：

```gherkin
@case_id:CFG-VOL-001 @module:volume-level @formal
Scenario: CFG-VOL-001 默认音量应符合需求
  Given 已清除配置并烧录当前项目固件
  When 设备首次启动完成
  And 使用音量边界探测法推断当前默认档位
  Then 默认音量档位应等于需求值
```

## Tag 规则

| Tag | 含义 |
| --- | --- |
| `@formal` | 正式全集用例 |
| `@smoke` | 最小可测性门禁 |
| `@negative` | 反例/不应响应 |
| `@numeric` | 数值探测 |
| `@persistence` | 掉电/重启保存 |
| `@voice_register` | 语音注册专项 |
| `@active_protocol` | 主动协议输出 |
| `@passive_protocol` | 被动协议注入 |
| `@closed_loop` | 主动后必须等 MCU 回包闭环 |
| `@manual` | 人工听测或当前环境不可完全自动化 |
| `@project:csk5062_xiaodu_fan` | 项目限定 |
| `@project:csk3022_htt_clothes_airer` | 项目限定 |
| `@variant:<name>` | 同功能不同实现变体 |

## Background 使用规则

Background 只写稳定的项目上下文，不写会污染状态的操作。

适合写入：

```gherkin
Background:
  Given 当前项目 profile 已加载
  And 日志口、协议口、控制口和声卡已按 profile 准备
```

不适合写入：

- 烧录固件；烧录耗时且会改变设备状态，应由 suite stage 或显式 Scenario 处理。
- 恢复出厂；会影响其他用例，应由具体 Scenario 前置写清。
- 进入学习模式；会造成状态污染，应在用例内闭环退出或隔离重启。

## Examples 使用规则

同一逻辑、多组命令/协议/play id 可以用 Scenario Outline。

```gherkin
Scenario Outline: 主动语音命令应发送对应协议
  Given 设备已唤醒并处于普通会话
  When 播放语音命令 "<phrase>"
  Then 协议口应捕获主动协议 "<active_frame>"

  Examples:
    | phrase       | active_frame |
    | 打开电风扇   | A5 FA 04 BB  |
    | 关闭电风扇   | A5 FA 05 BB  |
```

项目码值不应长期写死在通用 feature 中。正式落地时，Examples 应由当前项目需求/词表/profile 生成。

## Native 动作表/断言表规则

当新增用例属于已支持动作集合时，优先使用表驱动 DSL，避免新增 runner：

```gherkin
When Native 执行动作表
  | 动作 | 值 | 等待秒 |
  | 开始采集 | | |
  | 播放 | 小度小度 | 1.6 |
  | 播放 | 打开电风扇 | 3 |
Then Native 断言表应满足
  | 断言 | 值 |
  | 协议包含 | A5 FA 01 BB |
  | 协议包含 | A5 FA 04 BB |
```

只有当现有动作或断言无法表达需求时，才扩展通用 DSL；不要为单条用例新增专用 step 或 runner。

