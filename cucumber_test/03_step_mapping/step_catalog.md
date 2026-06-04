# Step 映射目录

本文定义 Cucumber step 与 Trisolaris 能力的映射。当前已落地小度 native step 子集，位于 `cucumber_test/runtime/features/steps/xiaodu_native_steps.py`；未迁移模块继续按本目录口径补 step/adapter。


## 已落地 Native 通用 DSL

`xiaodu_native_steps.py` 已提供两类通用表驱动 step，后续新增同类功能用例优先只改 `.feature`：

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

当前支持动作：`开始采集/start_capture`、`播放/play`、`等待/wait`、`协议发送/proto_send`、`日志命令/log_shell`。
当前支持断言：`协议包含/proto_contains`、`协议不包含/proto_not_contains`、`无控制帧/proto_no_control`、`日志包含/log_contains`、`日志不包含/log_not_contains`。

## Given 类

| Gherkin Step | 调用能力 | 输出上下文 |
| --- | --- | --- |
| `Given 当前项目 profile 已加载` | `references/project-profiles/*.json` | `project_id`、adapter、目录、固件匹配规则 |
| `Given 已清除配置并烧录当前项目固件` | `config.clear` 能力 + `tools/burn_bundle/run_fan_burn.sh` | 烧录日志、启动版本、默认配置证据 |
| `Given 设备通过最小可测性门禁` | `tools/suite/run_formal_suite.py` gate stage | gate status、日志/协议/声卡证据 |
| `Given 设备已唤醒并处于普通会话` | 音频播放 + 日志/协议采集 | `Wakeup`、`0x0001`、会话时间窗 |
| `Given MCU 握手仿真已常驻` | `tools/serial/fan_proto_handshake_probe.py` 或项目 adapter | ready 状态、心跳闭环 |
| `Given 已进入语音学习模式` | 项目 voice-register runner | 学习模式入口日志/play id |
| `Given 已恢复干净基线` | `config.clear` / reboot / 项目 reset adapter | 无残留学习/会话/配置污染 |

## When 类

| Gherkin Step | 调用能力 | 注意点 |
| --- | --- | --- |
| `When 播放唤醒词 "<phrase>"` | `tools/audio/listenai_play_repo.py` | 必须确认声卡 key 存在，否则 BLOCKED |
| `When 播放语音命令 "<phrase>"` | 音频播放 + 采集窗口 | 不能与上一条音频重叠 |
| `When 向协议口注入被动协议 "<frame>"` | serial writer/helper | 需要设备 ready 后注入，避免粘连心跳 |
| `When 等待会话超时` | log capture + timeout probe | 用日志同源时间戳，不用跨串口推断 |
| `When 执行断电重启` | 控制串口 power cycle | 保存类用例必须先看到保存完成 |
| `When 使用音量边界探测法推断当前默认档位` | volume probe | 先单边到边界，再双边确认总档位 |
| `When 填满命令词模板后再次进入学习` | voice-register batch | 用例内主动填满，不用启动计数直接推断 |

## Then 类

| Gherkin Step | 调用能力 | 最终判断口径 |
| --- | --- | --- |
| `Then 协议口应捕获主动协议 "<frame>"` | 协议 UART 原始帧解析 | 协议口原始帧为主，日志 send msg 为辅 |
| `Then 日志应出现 play id "<id>"` | 日志解析 | play id/play start/play stop 为主，不靠人耳 |
| `Then 默认音量档位应等于需求值` | volume probe 结构化结果 | 不用 raw volume 直接等价档位 |
| `Then 会话超时时长应等于需求值允许误差 "<tolerance>"` | timeout probe | 从响应结束或 Wakeup 到 TIME_OUT/MODE=0 |
| `Then 不应产生控制协议` | 负向采集窗口 | 必须证明采集有效，不允许空采集直接 PASS |
| `Then 配置应在重启后保持` | 保存日志 + 重启后行为 | 先保存完成，再断电/重启 |
| `Then 用例失败应进入收敛分析` | `fault-convergence.md` | raw FAIL 不能直接作为最终固件 FAIL |

## Step 实现边界

Step 不做以下事情：

- 不把 `cucumber-formal` 包装旧 runner 说成 native。
- 不为每一条新增功能用例增加一个专用 runner；优先复用动作表/断言表或扩展通用 DSL。
- 不自行决定最终 FAIL 归因。
- 不跨项目读取旧 deliverables 作为默认断言。

Step 只负责把自然语言步骤映射到项目 adapter 或 native 硬件原语；adapter/native step 输出结构化证据，最终归因仍由 Trisolaris 收敛规则处理。
