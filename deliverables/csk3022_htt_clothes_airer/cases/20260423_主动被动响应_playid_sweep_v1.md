# 好太太晾衣机主动命令-被动响应-play id sweep 用例

| 用例ID | 分组 | 标题 | 语音输入 | 期望主动协议 | 期望被动接收日志 |
| --- | --- | --- | --- | --- | --- |
| `FULL-BRIGHT-DOWN-001` | `fixed-passive` | 调暗全链路 | 小好小好 / 太亮了 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 5C 7A FB | receive msg:: A5 FA 81 00 47 67 FB |
