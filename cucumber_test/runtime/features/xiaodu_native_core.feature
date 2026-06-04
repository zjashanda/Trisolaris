# language: zh-CN
@native @project:csk5062_xiaodu_fan
功能: 小度 5062 Cucumber Native 核心链路
  为了让功能用例可以直接由 Cucumber Scenario 驱动硬件执行
  作为 Trisolaris 验证执行器
  我需要用通用 step 完成播放、采集、协议注入和断言，而不是调用旧 fullflow runner

  背景:
    假如 当前小度 Native 执行环境已准备

  @case_id:NATIVE-GATE-001 @smoke
  场景: NATIVE-GATE-001 Native 声卡和串口门禁
    那么 日志口 "/dev/ttyACM0" 应存在
    并且 协议口 "/dev/ttyACM2" 应存在
    并且 控制口 "/dev/ttyACM4" 应存在
    并且 声卡 "VID_8765&PID_5678:USB_0_4_3_1_0" 应可探测

  @case_id:NATIVE-BASELINE-001 @state
  场景: NATIVE-BASELINE-001 Native 清配置并重启到干净基线
    当 开始 Native 采集
    并且 Native 执行日志口命令 "config.clear" 并等待 1 秒
    并且 Native 执行日志口命令 "reboot" 并等待 8 秒
    那么 Native 日志口应出现 "Running Config"

  @active_protocol
  场景大纲: <case_id> Native 唤醒后语音命令应产生主动协议
    当 开始 Native 采集
    并且 Native 播放语音 "小度小度"
    并且 Native 等待 1.6 秒
    并且 Native 播放语音 "<phrase>"
    并且 Native 等待 3 秒
    那么 Native 协议口应捕获 "A5 FA 01 BB"
    并且 Native 协议口应捕获 "<expected_frame>"

    例子:
      | case_id | phrase | expected_frame |
      | NATIVE-ACTIVE-OPEN-001 | 打开电风扇 | A5 FA 04 BB |
      | NATIVE-ACTIVE-CLOSE-001 | 关闭电风扇 | A5 FA 05 BB |
      | NATIVE-ACTIVE-POWER-ON-001 | 开机 | A5 FA 06 BB |
      | NATIVE-ACTIVE-POWER-OFF-001 | 关机 | A5 FA 07 BB |
      | NATIVE-ACTIVE-VOL-UP-001 | 大声点 | A5 FA 13 BB |
      | NATIVE-ACTIVE-VOL-DOWN-001 | 小声点 | A5 FA 15 BB |
      | NATIVE-ACTIVE-VOL-MAX-001 | 最大音量 | A5 FA 14 BB |
      | NATIVE-ACTIVE-VOL-MIN-001 | 最小音量 | A5 FA 16 BB |
      | NATIVE-ACTIVE-EXIT-001 | 退出识别 | A5 FA 17 BB |

  @case_id:NATIVE-NEG-NOWAKE-001 @negative
  场景: NATIVE-NEG-NOWAKE-001 Native 未唤醒直接说控制词不应产生控制协议
    当 Native 等待 17 秒
    并且 开始 Native 采集
    并且 Native 播放语音 "打开电风扇"
    并且 Native 等待 3 秒
    那么 Native 协议口不应捕获任何控制帧

  @case_id:NATIVE-PASSIVE-REPORT-001 @passive_protocol
  场景: NATIVE-PASSIVE-REPORT-001 Native 被动播报协议应被日志口接收
    当 Native 执行动作表
      | 动作 | 值 | 等待秒 |
      | 开始采集 | | |
      | 协议发送 | A5 FB 12 CC | 4 |
    那么 Native 断言表应满足
      | 断言 | 值 |
      | 日志包含 | receive msg:: A5 FB 12 CC |
      | 日志包含 | play id |

  @case_id:NATIVE-VOICE-SWITCH-001 @state
  场景: NATIVE-VOICE-SWITCH-001 Native 关闭语音后协议开语音可恢复基础控制
    当 开始 Native 采集
    并且 Native 播放语音 "小度小度"
    并且 Native 等待 1.6 秒
    并且 Native 播放语音 "关闭语音"
    并且 Native 等待 3 秒
    那么 Native 协议口应捕获 "A5 FA 11 BB"
    当 Native 向协议口发送十六进制 "A5 FB 0A CC"
    并且 Native 等待 3 秒
    并且 Native 播放语音 "小度小度"
    并且 Native 等待 1.6 秒
    并且 Native 播放语音 "打开电风扇"
    并且 Native 等待 3 秒
    那么 Native 协议口应捕获 "A5 FA 04 BB"

  @case_id:CFG-VOL-001 @numeric @module:volume-level
  场景: CFG-VOL-001 Native 默认音量应符合需求值
    假如 Native 已清除配置并烧录当前项目固件
    当 开始 Native 采集
    并且 Native 等待 3 秒
    并且 Native 使用音量边界探测法推断默认档位
    那么 Native 默认音量档位应等于需求值
