# 与正式全集执行器的集成方案

## 当前入口

当前正式全集入口是：

```bash
python3 tools/suite/run_formal_suite.py \
  --req-dir <项目需求目录> \
  --log-port /dev/ttyACM0 \
  --proto-port /dev/ttyACM2 \
  --ctrl-port /dev/ttyACM4 \
  --device-key 'VID_8765&PID_5678:USB_0_4_3_1_0'
```

该入口已经负责：

- 项目识别；
- validation-pool 匹配；
- 固件选择；
- 烧录/gate；
- 项目 adapter 阶段调度；
- 结果聚合；
- 输出 suite summary/report。

## Cucumber 接入点

推荐增加一个可选阶段，而不是替换当前入口：

```text
run_formal_suite.py
  -> detect profile
  -> classify validation pool
  -> burn/gate
  -> if profile supports cucumber:
       run cucumber/behave features by tag
       convert cucumber json -> case_results.json
     else:
       run existing project stages
  -> aggregate final report
```

当前已落地三个可选模式：

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

模式边界：

- `cucumber-smoke`：只接小度 5062 最小 smoke feature，验证 Gherkin/step/硬件桥接。
- `cucumber-formal`：Cucumber 包装旧 formal runner，覆盖 72 条正式用例状态断言，但不是 native。
- `cucumber-native`：Scenario step 直接执行硬件动作，目前小度 native core 已接入 suite，覆盖 14 条核心链路。
- `cucumber-all`：当前全链路交付入口，先跑 native core，再跑 72 条正式 Cucumber Feature，最终汇总到一个 suite report。

示例：

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

默认 `formal` 模式不变，仍负责正式 72 条全集；native 迁移完成前不能把 `cucumber-formal` 当作 native 结果。

## 标准输出转换

Cucumber 原始结果需要转换成现有格式：

```json
{
  "case_results": [
    {
      "case_id": "CFG-VOL-001",
      "module": "volume-level",
      "status": "PASS|FAIL|TODO|BLOCKED",
      "evidence": "...",
      "raw_status": "cucumber passed/failed/skipped",
      "attribution": "pending|firmware|requirement|test_logic|environment"
    }
  ]
}
```

转换规则：

1. `passed` -> `PASS`。
2. `skipped` 且 tag 为 `@manual` -> `TODO`。
3. 环境或前置失败 -> `BLOCKED`，不能算固件 FAIL。
4. `failed` -> raw FAIL，必须进入 Trisolaris 收敛。
5. 收敛后最终 `FAIL` 只能保留固件问题或需求问题。

## Profile 扩展建议

后续可在 `references/project-profiles/*.json` 增加字段：

```json
{
  "cucumber": {
    "enabled": true,
    "feature_globs": ["deliverables/<project>/features/*.feature"],
    "tags": ["@formal", "not @manual"],
    "step_adapter": "python-behave",
    "result_json": "cucumber_test/debug/reports/<run_id>/cucumber.json"
  }
}
```

## 不建议的做法

- 不建议每个 Scenario 自己烧录一次，成本太高且引入状态漂移。
- 不建议在 `.feature` 里写死 `/dev/ttyACM*`，端口应来自 profile 或命令参数。
- 不建议在通用 `.feature` 里写死所有协议帧；项目 feature 的 Examples 可以由当前需求/词表生成。
- 不建议让 Cucumber 直接决定最终缺陷归因。
- 不允许用调用旧 runner 的 step 冒充 native；native 必须能在证据中看到 Scenario 级声卡/串口/协议动作。
