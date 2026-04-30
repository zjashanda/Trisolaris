# 项目执行 Profile

通用正式全集执行器使用这里的 profile 做项目识别和调度，不允许把某个项目的用例/断言写死成全局规则。

## Profile 职责

- `project_id`：项目唯一标识，对应 `deliverables/<project_id>/` 与 `result/<project_id>/`。
- `detect`：根据需求目录名、固件名、关键文件名识别项目。
- `adapter`：执行适配器名称。通用入口只负责编排，具体项目执行细节在 adapter 内部处理。
- `firmware_globs`：默认固件匹配规则；用户显式指定固件时优先用户输入。
- `stages`：脚本管线型项目的内部执行阶段。阶段可以是项目专用脚本，但最终必须输出统一 summary。

## 新项目接入

1. 新增一个 profile JSON。
2. 若可由通用脚本管线覆盖，使用 `script-pipeline` adapter 并列出阶段。
3. 若存在复杂状态机或聚合规则，新增项目 adapter，但 adapter 只处理项目差异，不污染通用入口。
4. 新项目验证稳定后，把通用模块回灌 `references/validation-pool/`，项目码值留在 profile 或项目 runner。
