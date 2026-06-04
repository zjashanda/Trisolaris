# Cucumber 适配方案归档

本目录存放 Trisolaris 引入 Cucumber / Gherkin 的方案、样例、可执行试验文件、调试材料和后续试验产物。当前已完成小度 5062 的 smoke、formal wrapper 和 native 三种可执行闭环，并以可选模式接入 `tools/suite/run_formal_suite.py`；默认正式全集链路不受影响。

## 当前结论

Cucumber 适合作为 Trisolaris 的“用例表达层”和“需求验收契约层”，不适合直接替代现有烧录、串口、声卡、协议仿真、日志解析和 FAIL 收敛执行器。

推荐架构：

```text
需求文档/词表/协议/固件
  -> validation-pool 模块匹配
  -> 生成项目方案
  -> 生成 Gherkin Feature/Scenario
  -> Cucumber/Behave step 调用项目 adapter 或 native 硬件步骤
  -> 统一 case_results.json
  -> Trisolaris 最终报告和固件/需求归因
```

## 目录说明

| 目录 | 用途 |
| --- | --- |
| `00_assessment/` | 当前 skill 哪些部分适合/不适合 Cucumber 的评估 |
| `01_architecture/` | Cucumber 接入分层方案和边界 |
| `02_gherkin_model/` | Feature、Scenario、Tag、Examples 的建模规则 |
| `03_step_mapping/` | Given/When/Then 与现有脚本能力的映射 |
| `04_examples/features/` | 小度、好太太和通用门禁的样例 `.feature` 文件 |
| `05_runner_integration/` | 与 `tools/suite/run_formal_suite.py` 的集成方案 |
| `06_migration/` | 分阶段落地路线 |
| `runtime/` | 已进入可执行验证的 Feature、behave hooks 和 step definitions |
| `tools/` | Cucumber 执行器和结果转换器 |
| `debug/` | 后续 Cucumber 相关调试日志、报告、临时证据和沙箱；不得散落到根目录 |

## 当前已实现

- 已用 Python `behave` 跑通小度 5062 最小 Cucumber smoke。
- 已生成 `cucumber.json`，并转换为 Trisolaris 统一 `case_results.json`。
- 已接入 `tools/suite/run_formal_suite.py --execution-mode cucumber-smoke`。
- 已接入 `tools/suite/run_formal_suite.py --execution-mode cucumber-formal`：这是 Cucumber 顶层包装旧 formal runner，用于 72 条正式用例状态断言，不属于 native 执行。
- 已接入 `tools/suite/run_formal_suite.py --execution-mode cucumber-native`：Scenario step 直接驱动声卡播放、串口采集、协议注入、日志/协议断言。
- 已接入 `tools/suite/run_formal_suite.py --execution-mode cucumber-all`：同一 suite 内先跑 native 场景，再跑 72 条正式 Cucumber Feature，输出一个全链路报告。
- 当前 smoke 覆盖：声卡/串口 gate、默认唤醒协议 `A5 FA 01 BB`、打开风扇协议 `A5 FA 04 BB`。
- 当前 native 覆盖：小度 gate、清配置重启、9 条主动协议、未唤醒负例、被动播报协议、语音关闭后协议开语音恢复，以及 `CFG-VOL-001` 默认音量数值探测；最新实测 `14 PASS / 1 FAIL / 0 BLOCKED`，唯一 native FAIL 为默认音量探测值 `2` 与需求 `3` 不一致。
- 当前 cucumber-all 最新实测：正式 72 条 `70 PASS / 1 FAIL / 1 TODO / 0 BLOCKED`，native `14 PASS / 1 FAIL`，两侧唯一 FAIL 均为 `CFG-VOL-001` 默认音量需求不符。
- 当前 formal wrapper 覆盖：小度 72 条正式用例状态断言；新增/删除用例优先修改 Feature Examples 或重新生成 Feature。

## 当前不做的事

- 不把 `cucumber-formal` 包装旧 runner 说成 native。
- 不把历史项目的码值硬编码进通用 step。
- 不把 raw FAIL 直接交给 Cucumber 判断最终归因；最终归因仍由 Trisolaris 收敛规则处理。
- 未迁移到 native 的复杂专项（如语音注册全量、持久化）仍由项目 adapter 执行；默认音量已迁入 native，后续迁移时要先补 native DSL/step，再补 Feature。
