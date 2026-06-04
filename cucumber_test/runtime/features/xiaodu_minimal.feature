# language: zh-CN
@formal @smoke @project:csk5062_xiaodu_fan @cucumber_p2
功能: 小度 5062 Cucumber 最小验证闭环
  为了验证 Cucumber 能接入 Trisolaris 的真实硬件链路
  作为验证执行器
  我需要用 Gherkin 场景驱动小度设备完成声卡、日志口、协议口和基础语音命令检查

  背景:
    假如 当前小度项目验证环境已准备

  @case_id:XIAODU-CUKE-GATE-001
  场景: XIAODU-CUKE-GATE-001 声卡和串口应可用于验证
    那么 日志口 "/dev/ttyACM0" 应存在
    并且 协议口 "/dev/ttyACM2" 应存在
    并且 控制口 "/dev/ttyACM4" 应存在
    并且 声卡 "VID_8765&PID_5678:USB_0_4_3_1_0" 应可探测

  @case_id:XIAODU-CUKE-WAKE-001
  场景: XIAODU-CUKE-WAKE-001 默认唤醒词应产生唤醒日志和协议帧
    当 开始采集日志口和协议口
    并且 播放语音 "小度小度"
    并且 等待 4 秒
    那么 日志口应出现 "Wakeup"
    并且 日志口应出现 "keyword:xiao du xiao du"
    并且 协议口应捕获十六进制帧 "A5 FA 01 BB"

  @case_id:XIAODU-CUKE-OPEN-001
  场景: XIAODU-CUKE-OPEN-001 唤醒后打开电风扇应产生主动控制协议
    当 开始采集日志口和协议口
    并且 播放语音 "小度小度"
    并且 等待 1.6 秒
    并且 播放语音 "打开电风扇"
    并且 等待 5 秒
    那么 日志口应出现 "keyword:da kai dian feng shan"
    并且 协议口应捕获十六进制帧 "A5 FA 01 BB"
    并且 协议口应捕获十六进制帧 "A5 FA 04 BB"
