# 当前 Skill 的 Cucumber 适配评估

## 适合 Cucumber 的部分

| 当前能力 | 适配方式 | 价值 |
| --- | --- | --- |
| 需求功能点拆解 | 转成 `Feature` 和 `Scenario` | 产品、测试、固件开发都能读懂验收条件 |
| 正式用例表达 | 用 `Given / When / Then` 表达前置、动作、断言 | 替代纯表格里的长步骤，减少歧义 |
| 反例/异常用例 | 用 `Scenario` + `@negative` / `@abnormal` 标记 | 明确“不应发生什么”，避免空采集误判 PASS |
| 项目差异 | 用 `@project_xxx`、`@variant_xxx`、`Examples` | 同一功能不同项目逻辑可以并存，不互相污染 |
| 用户澄清逻辑 | 固化成独立 Scenario 或 Rule | 例如好太太 G-07 语音开关状态机可明确写成多分支 |
| 回归全集 | 按 tag 选择 `@formal`、`@smoke`、`@voice_register` | 支持全量/专项/冒烟不同执行粒度 |
| 报告可读性 | Cucumber 原始结果再转换为 Trisolaris 报告 | 保留人可读用例，同时输出现有统计格式 |

## 部分适合，需要桥接的部分

| 当前能力 | Cucumber 角色 | 仍由 Trisolaris 负责 |
| --- | --- | --- |
| validation-pool 模块匹配 | 生成候选 Feature 模板 | 模块选择、变体判断、需求冲突识别 |
| project profile | 提供 Background / tag 参数 | 项目识别、端口、固件、执行 adapter |
| 通用全集执行器 | 调用 Cucumber 阶段或消费 Cucumber JSON | 烧录/gate/分组隔离/聚合 |
| 用例聚合 | Scenario status 可作为输入 | TODO/BLOCKED/FAIL 最终口径收敛 |
| FAIL 归因 | Scenario 失败提供现场 | 判断是否为断言/环境/状态污染，修复后复跑 |

## 不适合直接交给 Cucumber 的部分

| 部分 | 原因 | 保留方式 |
| --- | --- | --- |
| 烧录工具时序 | 依赖控制串口、电源、boot、重试和成功标记 | 继续放在 `tools/burn_bundle/` 和 Python runner |
| 串口采集循环 | 需要非阻塞读、时间窗、粘包/半包处理 | 继续由现有 serial helper 处理 |
| 声卡路由和播放 | 依赖设备 key、ALSA/PyAudio、播放完成检测 | 继续由 `tools/audio/` 处理 |
| 协议仿真/MCU 握手 | 需要持续心跳、主动/被动帧闭环 | 继续由项目 adapter 和 `tools/serial/` 处理 |
| 日志解析和数值探测 | 需要边界探测、时间戳、play id、保存闭环 | 继续由 Python probe 输出结构化结果 |
| raw FAIL 收敛 | 需要动态修断言、隔离重跑、人工判断 | 保持 Trisolaris 规则：最终 FAIL 只能是固件或需求 |

## 结论

Cucumber 不应成为底层执行引擎，而应成为正式用例的可读 DSL。最稳妥的方式是：

1. `validation-pool` 继续负责“如何设计验证”。
2. Gherkin 负责“把验证表达成人可读、可执行的场景”。
3. Python step definitions 负责“把场景调用到现有硬件执行能力”。
4. `run_formal_suite.py` 继续负责“项目识别、烧录、门禁、阶段调度、聚合和最终归因”。
