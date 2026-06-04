# Orion Synapse SkillTest Profile 资料框架

## 目标

Skill 不应该只暴露一段 `SKILL.md` 说明。为了让 Augur 页面能直接展示“可测模块 -> 测试方案 -> 自然语言测试用例 -> 执行/证据”的完整链路，每个支持平台化测试的 skill 都应在 skill 根目录提供一份结构化资料文件。

推荐文件名：

- `orion.skilltest.json`（首选）
- `skilltest.json`
- `skill-test.json`
- `.orion/skilltest.json`
- `.orion/skill-test.json`
- `docs/orion.skilltest.json`

平台扫描 SkillHub 时会优先读取这些文件；如果不存在，则只展示 `SKILL.md` 摘要，不展示可执行模块。

## 顶层结构

```json
{
  "schema": "orion.skilltest.v1",
  "skill_id": "polaris-device-validation",
  "name": "Polaris Device Validation",
  "summary": "用于 WS63/离线语音设备的功能验证、方案生成、用例执行和证据归档。",
  "version": "1.0.0",
  "flow": ["选择 Agent", "选择设备配置", "选择待测模块", "生成方案", "生成自然语言用例", "确认后执行", "收集证据"],
  "call_method": "python .../run_task.py --task <task.json> --mode <mode> --env-file <env>",
  "required_config": ["目标 Agent 在线", "设备串口配置", "声卡/音频播放设备", "测试素材或 task.json"],
  "generation": {},
  "capabilities": []
}
```

### 顶层字段

- `schema`：固定为 `orion.skilltest.v1`。
- `skill_id`：平台内唯一标识，建议和仓库名或 skill 名一致。
- `name` / `summary`：Augur skill 选择器和说明区展示。
- `version`：资料文件版本，便于后续兼容。
- `flow`：测试人员看到的流程，不写内部实现细节。
- `call_method`：简要说明如何调用，不要堆完整长命令。
- `required_config`：测试人员必须准备/确认的配置。
- `generation`：方案/用例生成方式，支持服务端大模型生成。
- `capabilities`：模块化功能测试项列表。

## generation：方案与用例生成方式

多模块组合测试通常不能靠固定模板拼接，需要大模型结合模块关系、用户自定义需求、设备配置和历史经验生成方案。因此平台支持“服务端生成、Agent 执行”的分层模式：

- 方案/自然语言用例生成在服务器侧完成，可以调用服务端本地 skill、Codex/Claude CLI 或后续统一的 LLM API。
- 真机串口、声卡、设备动作仍在选中的 Agent 节点执行。
- 生成结果必须保存为结构化 JSON + Markdown，和任务 ID/方案 ID 关联，便于追溯。

推荐字段：

```json
{
  "generation": {
    "mode": "server-llm",
    "planner": "codex|claude|openai|template",
    "prompt": "根据选中模块、设备配置和用户补充需求生成测试方案与自然语言测试用例。",
    "output_schema": "orion.skilltest.plan.v1",
    "artifacts": ["plan.json", "cases.md", "cases.json"]
  }
}
```

## capabilities：模块化功能测试项

每个 capability 是测试人员在页面上点击选择的卡片。

```json
{
  "id": "wake_latency",
  "module": "timing",
  "name": "唤醒耗时",
  "summary": "验证音频注入到串口唤醒事件之间的耗时。",
  "requirement": "验证唤醒耗时是否满足项目阈值。",
  "logic": "播放唤醒音频，采集串口 marker，计算 audio_start 到 wake_event 的耗时。",
  "modes": ["plan-only", "dry-run", "execute"],
  "recommended_mode": "dry-run",
  "runner": "agent_shell",
  "task": "tasks/wake_latency.example.json",
  "requires": ["播放声卡", "AP 串口", "upper/asr 串口", "耗时阈值"],
  "side_effects": ["播放唤醒音频", "读取串口日志"],
  "risk_level": "low|medium|high",
  "test_cases": []
}
```

### capability 字段

- `id`：模块 ID，必须在当前 skill 内唯一。
- `module`：模块分类，例如 `wake`、`command`、`network`、`stress`。
- `name` / `summary`：卡片标题和摘要。
- `requirement`：默认测试目标，用户未输入自定义需求时使用。
- `logic`：鼠标悬停卡片时展示，说明“这个模块到底测什么”。
- `modes`：支持的执行模式。
- `recommended_mode`：默认推荐模式。
- `runner`：执行器类型，例如 `agent_shell`、`codex`、`manual`。
- `task`：默认任务文件或入口脚本相对路径。
- `requires`：依赖资源。
- `side_effects`：真实执行可能产生的动作或风险。
- `risk_level`：用于 execute 二次确认。
- `test_cases`：自然语言测试用例模板。

## test_cases：自然语言用例

这是最关键的展示内容。测试人员选择模块并生成方案后，页面必须清楚展示“将执行哪些测试”。不要只展示命令行参数。

```json
{
  "id": "wake_latency_basic",
  "title": "基础唤醒耗时验证",
  "objective": "确认设备能被指定唤醒词唤醒，且唤醒耗时低于项目阈值。",
  "preconditions": ["设备已烧录目标固件", "AP/upper 串口可读", "播放声卡可用"],
  "steps": [
    "清理上一轮串口日志并确认设备处于待唤醒状态。",
    "通过指定声卡播放标准唤醒音频。",
    "采集串口中的 audio_start、wake_event、ASR ready 等 marker。",
    "计算唤醒耗时并和阈值比较。"
  ],
  "expected_results": [
    "串口能观察到一次有效 wake_event。",
    "唤醒耗时低于配置阈值。",
    "没有异常重启、卡死或误触发。"
  ],
  "evidence": ["串口日志", "耗时统计 JSON", "最终 Markdown 报告"],
  "pass_criteria": "所有样本满足阈值且没有阻塞异常。",
  "fail_criteria": "出现超阈值、无唤醒事件或异常重启。",
  "blocked_conditions": ["声卡不可用", "串口被占用", "缺少测试音频"],
  "estimated_minutes": 3
}
```

### 用例展示规则

- 方案生成后，Augur 应先展示模块组合方案，再展示自然语言测试用例。
- 用例应按模块分组；多模块组合时还需要展示“组合覆盖关系”和“执行顺序”。
- 用例里必须有：测试目标、前置条件、步骤、预期结果、证据、PASS/FAIL/BLOCKED 口径。
- 如果用户在页面上输入自定义需求，大模型生成时应把自定义需求合并到用例中，而不是只使用默认模板。
- execute 前必须让测试人员确认用例和 side effects。

## 服务器调用 skill 的推荐架构

1. Augur 选择 Agent、设备配置、待测 capability。
2. 用户点击 `Generate Plan`。
3. 服务器读取 skill 目录下的 `orion.skilltest.json`、`SKILL.md` 和必要的参考文件。
4. 服务器在隔离目录生成方案任务，例如 `var/skill-test/plans/<plan_id>/`。
5. 如果 `generation.mode=server-llm`，服务器调用指定 planner（Codex/Claude/OpenAI API）生成：
   - `plan.json`
   - `cases.json`
   - `cases.md`
6. Augur 展示方案和自然语言用例，测试人员确认后再下发执行任务到选定 Agent。
7. Agent 只负责真机执行，日志进入 `D:\zhsh\logs\tasks\<task_id>`，结果回传 Cortex/Augur。

这样可以避免把大模型、仓库资料读取和真机执行混在一个环节里，也能保证服务重启后仍能恢复生成结果和执行结果。
