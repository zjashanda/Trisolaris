# Cucumber 可执行试验区

本目录存放已经进入可执行验证的 Cucumber/behave 文件。当前包含小度 5062 的 smoke、formal wrapper 和 native 场景；native 场景会清配置重启、执行协议/音频链路和默认音量数值探测，不再调用旧 formal runner。

## 当前文件

| 文件 | 作用 |
| --- | --- |
| `features/xiaodu_minimal.feature` | 小度 5062 最小 Gherkin 用例，覆盖声卡/串口 gate、默认唤醒协议、打开风扇协议 |
| `features/xiaodu_formal_fullflow.feature` | 小度 5062 正式 72 条 Cucumber 用例表，Examples 驱动逐条状态断言；执行仍包装 formal runner |
| `features/xiaodu_native_core.feature` | 小度 5062 native 核心场景，Scenario 直接驱动硬件动作与断言 |
| `features/environment.py` | behave hooks，负责运行目录、证据目录、串口采集生命周期和同句柄写入 |
| `features/steps/xiaodu_steps.py` | 中文 Given/When/Then step definitions，调用现有声卡播放和串口采集能力 |
| `features/steps/xiaodu_formal_steps.py` | 正式全链路 wrapper step definitions，负责调用 formal suite 并按用例表断言状态 |
| `features/steps/xiaodu_native_steps.py` | native step definitions，直接执行播放、采集、协议注入、日志命令和断言表 |
| `../tools/run_xiaodu_cucumber_minimal.py` | 一键执行 smoke，生成 cucumber JSON、case_results 和中文报告 |
| `../tools/run_xiaodu_cucumber_fullflow.py` | 小度 Cucumber formal wrapper 入口 |
| `../tools/run_xiaodu_cucumber_native_core.py` | 小度 Cucumber native 入口 |
| `../tools/generate_xiaodu_formal_feature.py` | 从正式用例 markdown 生成 Cucumber Feature/Examples |
| `../tools/convert_behave_json.py` | 将 behave JSON 转换为 Trisolaris `case_results.json` |

## 执行命令

直接执行 Cucumber smoke：

```bash
python3 cucumber_test/tools/run_xiaodu_cucumber_minimal.py \
  --log-port /dev/ttyACM0 \
  --proto-port /dev/ttyACM2 \
  --ctrl-port /dev/ttyACM4 \
  --device-key 'VID_8765&PID_5678:USB_0_4_3_1_0'
```

通过通用 suite 入口执行：

```bash
python3 tools/suite/run_formal_suite.py \
  --req-dir 项目需求/CSK5062小度风扇需求 \
  --project csk5062_xiaodu_fan \
  --execution-mode cucumber-smoke \
  --log-port /dev/ttyACM0 \
  --proto-port /dev/ttyACM2 \
  --ctrl-port /dev/ttyACM4 \
  --device-key 'VID_8765&PID_5678:USB_0_4_3_1_0'
```

通过通用 suite 入口执行 Cucumber 正式全链路：

```bash
python3 tools/suite/run_formal_suite.py \
  --req-dir 项目需求/CSK5062小度风扇需求 \
  --project csk5062_xiaodu_fan \
  --execution-mode cucumber-formal \
  --log-port /dev/ttyACM0 \
  --proto-port /dev/ttyACM2 \
  --ctrl-port /dev/ttyACM4 \
  --device-key 'VID_8765&PID_5678:USB_0_4_3_1_0'
```


通过通用 suite 入口执行 Cucumber all 全链路：

```bash
python3 tools/suite/run_formal_suite.py \
  --req-dir 项目需求/CSK5062小度风扇需求 \
  --project csk5062_xiaodu_fan \
  --execution-mode cucumber-all \
  --log-port /dev/ttyACM0 \
  --proto-port /dev/ttyACM2 \
  --ctrl-port /dev/ttyACM4 \
  --burn-port /dev/ttyACM0 \
  --device-key 'VID_8765&PID_5678:USB_0_4_3_1_0' \
  --pre-burn-wait-ms 6000
```

通过通用 suite 入口执行 Cucumber native：

```bash
python3 tools/suite/run_formal_suite.py \
  --req-dir 项目需求/CSK5062小度风扇需求 \
  --project csk5062_xiaodu_fan \
  --execution-mode cucumber-native \
  --log-port /dev/ttyACM0 \
  --proto-port /dev/ttyACM2 \
  --ctrl-port /dev/ttyACM4 \
  --device-key 'VID_8765&PID_5678:USB_0_4_3_1_0'
```

## 当前边界

- 当前使用 Python `behave` 作为 Cucumber-compatible Gherkin 执行器。
- smoke 模式只验证小度 5062 最小链路是否可通过 Cucumber 执行。
- formal 模式是 Cucumber wrapper：Feature/Examples 驱动正式用例状态断言，但功能动作仍复用已收敛的项目 runner/adapter。
- native 模式是 Cucumber 直接执行：Scenario step 直接驱动硬件原语；当前 native 覆盖 15 条，实测 `14 PASS / 1 FAIL / 0 BLOCKED`，唯一 FAIL 为 `CFG-VOL-001` 默认音量探测值 `2` 与需求 `3` 不一致。
- all 模式是当前全链路交付入口：先跑 native 场景，再跑 72 条 formal Feature，最终报告同时给出正式用例统计和 native 覆盖统计。
- 新增或删除 formal 状态断言用例时，优先修改 `features/xiaodu_formal_fullflow.feature` 的 Examples 或重新生成该文件。
- 新增或删除 native 功能执行用例时，优先修改 native `.feature` 的 Scenario/Examples/动作表/断言表；只有通用 DSL 不足时才扩展 step。
