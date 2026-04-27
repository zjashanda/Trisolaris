# 好太太晾衣机主动命令-被动响应-play id sweep 用例

| 用例ID | 分组 | 标题 | 语音输入 | 期望主动协议 | 期望被动接收日志 |
| --- | --- | --- | --- | --- | --- |
| `FULL-LIGHT-ON-001` | `fixed-passive` | 打开照明全链路 | 小好小好 / 打开照明 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 09 27 FB | receive msg:: A5 FA 81 00 09 29 FB |
| `FULL-LIGHT-OFF-001` | `fixed-passive` | 关闭照明全链路 | 小好小好 / 关闭照明 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 0A 28 FB | receive msg:: A5 FA 81 00 0A 2A FB |
| `FULL-POWER-OFF-001` | `fixed-passive` | 关机全链路 | 小好小好 / 关机 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 05 23 FB | receive msg:: A5 FA 81 00 05 25 FB |
| `FULL-UP-001` | `fixed-passive` | 上升全链路 | 小好小好 / 晾杆上升 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 06 24 FB | receive msg:: A5 FA 81 00 06 26 FB |
| `FULL-DOWN-001` | `fixed-passive` | 下降全链路 | 小好小好 / 晾杆下降 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 07 25 FB | receive msg:: A5 FA 81 00 07 27 FB |
| `FULL-STOP-001` | `fixed-passive` | 停止全链路 | 小好小好 / 停止升降 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 08 26 FB | receive msg:: A5 FA 81 00 08 28 FB |
| `FULL-STERILIZE-ON-001` | `fixed-passive` | 打开消毒全链路 | 小好小好 / 打开消毒 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 0B 29 FB | receive msg:: A5 FA 81 00 0B 2B FB |
| `FULL-STERILIZE-OFF-001` | `fixed-passive` | 关闭消毒全链路 | 小好小好 / 关闭消毒 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 0D 2B FB | receive msg:: A5 FA 81 00 0D 2D FB |
| `FULL-VOL-UP-001` | `fixed-passive` | 调大音量全链路 | 小好小好 / 调大音量 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 41 5F FB | receive msg:: A5 FA 81 00 41 61 FB |
| `FULL-VOL-DOWN-001` | `fixed-passive` | 调小音量全链路 | 小好小好 / 调小音量 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 42 60 FB | receive msg:: A5 FA 81 00 42 62 FB |
| `FULL-VOL-MAX-001` | `fixed-passive` | 最大音量全链路 | 小好小好 / 最大音量 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 43 61 FB | receive msg:: A5 FA 81 00 43 63 FB |
| `FULL-VOL-MIN-001` | `fixed-passive` | 最小音量全链路 | 小好小好 / 最小音量 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 44 62 FB | receive msg:: A5 FA 81 00 44 64 FB |
| `FULL-BRIGHT-UP-001` | `fixed-passive` | 调亮全链路 | 小好小好 / 亮度调高一点 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 5B 79 FB | receive msg:: A5 FA 81 00 46 66 FB |
| `FULL-BRIGHT-DOWN-001` | `fixed-passive` | 调暗全链路 | 小好小好 / 调暗一点 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 5C 7A FB | receive msg:: A5 FA 81 00 47 67 FB |
| `FULL-BRIGHT-MAX-001` | `fixed-passive` | 最亮全链路 | 小好小好 / 调到最亮 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 57 75 FB | receive msg:: A5 FA 81 00 48 68 FB |
| `FULL-BRIGHT-MIN-001` | `fixed-passive` | 最暗全链路 | 小好小好 / 调到最暗 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 58 76 FB | receive msg:: A5 FA 81 00 49 69 FB |
| `FULL-COLD-UP-001` | `fixed-passive` | 调冷全链路 | 小好小好 / 增加冷光 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 5D 7B FB | receive msg:: A5 FA 81 00 4A 6A FB |
| `FULL-WARM-UP-001` | `fixed-passive` | 调暖全链路 | 小好小好 / 增加暖光 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 5E 7C FB | receive msg:: A5 FA 81 00 4B 6B FB |
| `FULL-COLD-MAX-001` | `fixed-passive` | 最冷全链路 | 小好小好 / 打开冷光模式 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 59 77 FB | receive msg:: A5 FA 81 00 4C 6C FB |
| `FULL-WARM-MAX-001` | `fixed-passive` | 最暖全链路 | 小好小好 / 打开暖光模式 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 5A 78 FB | receive msg:: A5 FA 81 00 4D 6D FB |
| `FULL-NIGHT-ON-001` | `fixed-passive` | 打开夜灯全链路 | 小好小好 / 打开夜灯 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 61 7F FB | receive msg:: A5 FA 81 00 4E 6E FB |
| `FULL-NIGHT-OFF-001` | `fixed-passive` | 关闭夜灯全链路 | 小好小好 / 关闭夜灯 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 62 80 FB | receive msg:: A5 FA 81 00 4F 6F FB |
| `FULL-SCENE-CLOTHES-001` | `fixed-passive` | 打开晾衣模式全链路 | 小好小好 / 打开晾衣模式 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 63 81 FB | receive msg:: A5 FA 81 00 50 70 FB |
| `FULL-SCENE-LEISURE-001` | `fixed-passive` | 打开休闲模式全链路 | 小好小好 / 打开休闲模式 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 64 82 FB | receive msg:: A5 FA 81 00 51 71 FB |
| `FULL-SCENE-READ-001` | `fixed-passive` | 打开阅读模式全链路 | 小好小好 / 打开阅读模式 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 65 83 FB | receive msg:: A5 FA 81 00 52 72 FB |
| `FULL-SCENE-GARDEN-001` | `fixed-passive` | 打开园艺模式全链路 | 小好小好 / 打开园艺模式 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 66 84 FB | receive msg:: A5 FA 81 00 53 73 FB |
| `FULL-ROD1-UP-001` | `fixed-passive` | 杆一上升全链路 | 小好小好 / 杆一上升 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 51 6F FB | receive msg:: A5 FA 81 00 63 83 FB |
| `FULL-ROD2-UP-001` | `fixed-passive` | 杆二上升全链路 | 小好小好 / 杆二上升 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 52 70 FB | receive msg:: A5 FA 81 00 63 83 FB |
| `FULL-ROD1-DOWN-001` | `fixed-passive` | 杆一下降全链路 | 小好小好 / 降低杆一 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 53 71 FB | receive msg:: A5 FA 81 00 64 84 FB |
| `FULL-ROD2-DOWN-001` | `fixed-passive` | 杆二下降全链路 | 小好小好 / 杆二下降 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 54 72 FB | receive msg:: A5 FA 81 00 64 84 FB |
| `FULL-ROD1-STOP-001` | `fixed-passive` | 杆一停止全链路 | 小好小好 / 第一根杆停止 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 55 73 FB | receive msg:: A5 FA 81 00 65 85 FB |
| `FULL-ROD2-STOP-001` | `fixed-passive` | 杆二停止全链路 | 小好小好 / 杆二停止 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 56 74 FB | receive msg:: A5 FA 81 00 65 85 FB |
| `FULL-COLLECT-SET-OK-001` | `fixed-passive` | 设为收衣位成功 | 小好小好 / 设为收衣位 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 77 95 FB | receive msg:: A5 FA 81 00 73 93 FB |
| `FULL-COLLECT-SET-FAIL-001` | `fixed-passive` | 设为收衣位失败 | 小好小好 / 设为收衣位 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 77 95 FB | receive msg:: A5 FA 81 00 74 94 FB |
| `FULL-COLLECT-CANCEL-001` | `fixed-passive` | 取消收衣位 | 小好小好 / 取消收衣位 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 78 96 FB | receive msg:: A5 FA 81 00 7B 9B FB |
| `FULL-DRY-SET-OK-001` | `fixed-passive` | 设为晒衣位成功 | 小好小好 / 设为晒衣位 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 79 97 FB | receive msg:: A5 FA 81 00 75 95 FB |
| `FULL-DRY-SET-FAIL-001` | `fixed-passive` | 设为晒衣位失败 | 小好小好 / 设为晒衣位 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 79 97 FB | receive msg:: A5 FA 81 00 76 96 FB |
| `FULL-DRY-CANCEL-001` | `fixed-passive` | 取消晒衣位 | 小好小好 / 取消晒衣位 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 7A 98 FB | receive msg:: A5 FA 81 00 7C 9C FB |
| `FULL-PAIR-SUCCESS-001` | `fixed-passive` | 开始配网成功链路 | 小好小好 / 开始配网 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 20 3E FB | receive msg:: A5 FA 81 00 04 24 FB / receive msg:: A5 FA 81 00 1C 3C FB |
| `FULL-PAIR-FAIL-001` | `fixed-passive` | 开始配网失败链路 | 小好小好 / 开始配网 | A5 FA 7F 00 01 1F FB / A5 FA 7F 00 20 3E FB | receive msg:: A5 FA 81 00 04 24 FB / receive msg:: A5 FA 81 00 1D 3D FB |
