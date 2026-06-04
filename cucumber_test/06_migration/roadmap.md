# Cucumber 分阶段落地路线

## P0：方案归档

状态：已完成。

交付物：

- Cucumber 适配评估；
- 分层方案；
- Gherkin 建模规则；
- Step 映射目录；
- 小度、好太太、通用门禁样例 Feature；
- 与正式全集执行器的集成方案。

已在后续阶段执行硬件 smoke，并引入 Python `behave`。

## P1：只生成 Feature，不执行

目标：从已有正式用例/validation-pool 生成 `.feature`，让人先审可读性。

建议动作：

1. 为 `tools/cases/generate_formal_assets.py` 增加可选输出 `.feature`。
2. 将小度 72 条和好太太 96 条中稳定用例映射为 Feature。
3. 每个 Scenario 必须带 `@case_id:<id>`。
4. 与现有 markdown/xlsx 用例做数量一致性校验。

验收：

- 小度 Feature 数量覆盖 72 条正式用例；
- 好太太 Feature 数量覆盖 96 条正式用例；
- 不改变现有执行结果。

## P2：最小 step 闭环

目标：只挑 3 类低风险用例跑通：

- 烧录/gate smoke；
- 主动协议命令；
- 被动播报/play id。

建议动作：

1. 选择 `behave` 作为 Python Cucumber 执行器。
2. 新增 `cucumber_test/runtime/features/` 和 `cucumber_test/runtime/steps/`。
3. Step 调用现有 Python adapter，不重新写串口底层。
4. 输出 Cucumber JSON，再转换 `case_results.json`。

验收：

- 至少 3 条 Scenario 能稳定执行；当前小度 `XIAODU-CUKE-GATE-001` / `XIAODU-CUKE-WAKE-001` / `XIAODU-CUKE-OPEN-001` 已通过。
- 结果能进入 `run_formal_suite.py` 聚合；当前已通过 `--execution-mode cucumber-smoke` 接入。
- raw FAIL 仍进入现有收敛流程。

## P3：接入通用全集执行器

目标：`tools/suite/run_formal_suite.py` 支持 `--case-format cucumber` 或 profile 配置。

状态：已完成 opt-in 接入，包含 `--execution-mode cucumber-smoke`、`--execution-mode cucumber-formal`、`--execution-mode cucumber-native` 和 `--execution-mode cucumber-all`。其中 `cucumber-formal` 是 wrapper，`cucumber-native` 才是 Scenario 直接驱动硬件，`cucumber-all` 是当前全链路交付入口。

建议动作：

1. profile 声明 Cucumber feature 路径和 tag。
2. runner 在烧录/gate 后运行 Cucumber stage。
3. Cucumber result 转换成统一 `case_results.json`。
4. final report 同时链接 `.feature` 和结构化证据。

验收：

- 好太太或小度任一项目可用 Cucumber 方式执行一个稳定子集；
- 非 Cucumber 项目不受影响；
- 全量 runner 对外仍只输出一次全集结果。

## P3.5：Native 执行器迁移

目标：把高价值正式用例从 wrapper 逐步迁移到 Scenario 直接驱动硬件。

当前状态：

- 小度 native 已完成默认音量数值用例迁移：当前真实设备执行 `14 PASS / 1 FAIL / 0 BLOCKED`，唯一 FAIL 为 `CFG-VOL-001` 默认音量探测值 `2` 与需求 `3` 不一致，归因不再是执行器/断言问题。
- 已接入 suite：`--execution-mode cucumber-native`。
- 已提供动作表/断言表 DSL，新增同类场景优先只改 `.feature`。

后续迁移顺序：

1. 主动协议与被动协议全量 Examples。
2. 会话超时、退出识别、负向阻断。
3. 播报开关、语音开关、持久化。
4. 音量边界/默认值探测。
5. 语音注册专项。

验收：

- 每迁移一组，raw FAIL 必须先收敛验证逻辑，最终 FAIL 仍只能是固件或需求问题。
- 未迁移组继续由 formal adapter 执行，不能冒充 native。

## P4：模块化验证池反向生成 Feature 模板

目标：新项目需求进入后，validation-pool 不只生成测试方案，还能生成 Gherkin 骨架。

建议动作：

1. 给每个 `references/validation-pool/*.md` 增加 Gherkin 模板片段。
2. 模板只写行为，不写项目码值。
3. 当前项目需求解析后填充 Examples。
4. 新变体收敛后回灌模板。

验收：

- 新项目可以先得到可审阅 `.feature` 方案；
- 需求变更可以 diff Feature 变更点；
- 同功能不同项目变体通过 tag/Examples 区分。

## P5：正式替换部分表格式用例

目标：当 Cucumber 链路稳定后，正式用例主表达从 markdown/xlsx 逐步切到 `.feature`。

保留项：

- xlsx 可继续作为对外交付格式；
- markdown 报告继续作为最终报告；
- Python runner 继续承载硬件细节和收敛逻辑。

不建议完全替换 Trisolaris 当前 runner，因为硬件验证的关键复杂度不在用例语法，而在执行稳定性和证据归因。
