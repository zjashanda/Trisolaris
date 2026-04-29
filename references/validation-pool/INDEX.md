# 模块化验证池索引

## 使用顺序

1. 读取 `schema.md`，确认模块和变体规则。
2. 读取输入需求，拆成功能点和约束项。
3. 用本索引匹配候选模块。
4. 对每个命中模块读取对应文件，只加载需要的模块。
5. 生成项目级方案和用例，禁止直接复制旧项目 deliverables 的断言。
6. 执行后把新发现的通用逻辑回灌对应模块。

## 模块列表

| 模块 | 适用场景 | 来源项目 |
| --- | --- | --- |
| `requirement-ingestion.md` | 多文件需求、词表、协议、tone、流程图、固件输入解析 | mars-moon、小度、好太太 |
| `burn-and-gates.md` | 烧录、健康检查、最小可测性门禁、预处理 | mars-moon、mars-belt、好太太 |
| `wake-session.md` | 唤醒、会话、超时、未唤醒反例、重唤醒恢复 | mars-moon、mars-belt、小度、好太太 |
| `active-protocol.md` | 语音触发主动协议输出 | 小度、好太太、mars-moon |
| `passive-protocol.md` | MCU/外部协议注入、被动播报和状态改变 | 好太太、mars-moon |
| `active-passive-closed-loop.md` | 主动上报后必须等 MCU 回包才断言本地状态 | 好太太 |
| `broadcast-play-id.md` | 播报、tone、play id、提示音、设置失败提示 | 好太太、小度、mars-moon |
| `volume-level.md` | 音量档位、默认音量、边界、上下溢播报 | mars-belt、好太太、小度 |
| `persistence-config.md` | 掉电保存、config.clear、恢复出厂、重启后配置 | mars-belt、mars-moon、好太太、小度 |
| `state-machine-settings.md` | 设置窗口、工作模式、窗帘模式、普通词干扰 | mars-moon |
| `voice-switch-state-machine.md` | 语音开关、受限态、恢复语音、会话窗口 | 好太太 |
| `voice-register.md` | 命令词/唤醒词学习、删除、冲突、模板满 | mars-belt、小度 |
| `multi-wake.md` | 多唤醒、切换、查询、恢复默认、掉电保持 | mars-belt、mars-moon、小度 |
| `negative-abnormal.md` | 负例、删除词条、不应响应、异常协议、重启异常 | mars-moon、mars-belt、好太太 |
| `packaging-config-matrix.md` | 平台打包、支持矩阵、边界/中值包、控制变量复测 | mars-belt |
| `fault-convergence.md` | raw FAIL 收敛、控制变量、最终归因 | mars-belt、好太太、小度 |

## 变体优先级

1. 当前需求明确写出的逻辑优先。
2. 用户在当前轮明确澄清的逻辑优先。
3. 运行探测得到的固件状态刷新和协议证据优先。
4. 验证池通用模板只提供候选，不得覆盖 1~3。
5. 旧项目 deliverables 只能作案例，不得直接成为新项目断言。
