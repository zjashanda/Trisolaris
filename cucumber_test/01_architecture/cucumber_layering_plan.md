# Cucumber 接入分层方案

## 目标

在不破坏当前 Trisolaris 硬件验证能力的前提下，引入 Cucumber/Gherkin 作为统一的用例表达层，使新项目和老项目变更都能用同一套结构描述需求、步骤和断言。

## 推荐分层

```text
L0 输入层
- 项目需求目录
- 固件 bin
- 协议表/词表/tone 表/流程图
- 用户最新澄清

L1 需求建模层
- references/validation-pool/
- references/project-profiles/
- 当前有效需求清单

L2 Gherkin 用例层
- cucumber_test/04_examples/features/*.feature
- 后续可生成 deliverables/<project>/features/*.feature

L3 Step 桥接层
- Python step definitions
- wrapper step：调用现有工具或 adapter
- native step：直接驱动声卡播放、串口采集、协议注入、日志/协议断言
- 每个 step 不跨项目套用旧 deliverables 断言

L4 执行层
- tools/suite/run_formal_suite.py
- cucumber_test/tools/run_*_cucumber_native_*.py
- tools/debug/run_<project>_*.py
- tools/audio/
- tools/serial/
- tools/burn_bundle/

L5 结果层
- Cucumber JSON/JUnit
- case_results.json
- suite_report.md
- FAIL 收敛结论
```

## 接入原则

1. Gherkin 只描述行为，不直接写串口实现细节。
2. Step definitions 只做编排和调用；native step 可以操作底层硬件原语，但必须保持动作/断言 DSL 通用。
3. 项目码值、固件、端口、声卡、握手规则仍来自 profile、Feature Examples 或项目 adapter，不从旧项目结论继承。
4. `cucumber-formal` 是 wrapper；只有 Scenario step 直接执行硬件动作时才叫 `cucumber-native`。
5. Cucumber 失败只是 raw FAIL，不能直接作为最终固件 FAIL。
6. 所有 Cucumber 试验产物先放 `cucumber_test/`，方案稳定后再决定是否进入正式 `deliverables/<project>/`。

## 与现有模块关系

| 现有文件/目录 | Cucumber 后的位置 |
| --- | --- |
| `references/validation-pool/*.md` | 继续作为方案池；未来可生成 Scenario 模板 |
| `references/project-profiles/*.json` | 给 Cucumber runner 提供项目参数和 adapter |
| `tools/suite/run_formal_suite.py` | 增加可选 stage：`cucumber-smoke` / `cucumber-formal` / `cucumber-native` |
| `cucumber_test/runtime/features/steps/xiaodu_native_steps.py` | native step 直接执行声卡、串口、协议、断言原语 |
| `tools/debug/run_post_restructure_fullflow.py` | 被 wrapper step/adapter 调用，保留尚未 native 化的复杂执行逻辑 |
| `tools/debug/run_htt_*.py` | 被 step/adapter 调用，保留项目差异逻辑 |
| `deliverables/<project>/cases/` | 可保留表格用例，也可生成对应 `.feature` |

## 推荐工具选择

当前仓库以 Python 为主，后续优先考虑 Python 生态的 Gherkin 执行器：

- `behave`：最贴近 Cucumber 的 Python BDD 框架，适合 `features/steps/*.py`。
- `pytest-bdd`：适合已有 pytest 体系，但当前项目未形成 pytest 主链路。
- `cucumber-js/java`：标准 Cucumber 生态更完整，但会引入 Node/Java 栈，不适合作为第一阶段。

建议第一阶段不引入依赖，只沉淀 `.feature` 和 step 目录设计；第二阶段再选择 `behave` 做最小可运行闭环。
