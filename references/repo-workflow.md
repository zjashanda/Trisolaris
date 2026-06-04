# Repo Workflow

## 当前范围

本仓库是 Trisolaris 多项目离线语音验证 skill，当前同时保留：

- `CSK5062 小度风扇`：当前 Linux 设备全链路验证主线。
- `CSK3022 好太太晾衣机`：云端合入项目，保留握手仿真、需求矩阵、方案、用例和复测逻辑。

后续新项目进入时，必须新增独立 input / deliverables / report namespace，不能覆盖既有项目资产。

## 启动流程

每轮在仓库根目录执行：

1. 读取 `plan.md`；没有则创建。
2. 明确本轮目标、当前执行项、待执行项。
3. 每个关键动作后把 done / doing / todo 同步到 `plan.md`。
4. 新需求、需求变更、全链路执行或发布前读取 `references/fullflow-validation-method.md`。
5. 判断证据前读取 `references/evidence-rules.md`。

## 输入目录

- 小度风扇：`项目需求/CSK5062小度风扇需求/`
- 好太太晾衣机：`项目需求/好太太晾衣机/`

输入目录保留需求文档、词表、固件和必要资源；压缩包解压副本、临时日志和运行 staging 不放入输入目录。

## 输出目录

- `deliverables/csk5062_xiaodu_fan/plan/`：小度方案。
- `deliverables/csk5062_xiaodu_fan/cases/`：小度正式用例。
- `deliverables/csk5062_xiaodu_fan/archive/`：小度用例归档。
- `deliverables/csk3022_htt_clothes_airer/plan/`：好太太方案、矩阵、缺陷、复测结论。
- `deliverables/csk3022_htt_clothes_airer/cases/`：好太太稳定用例定义。
- `result/`：本地原始执行证据，忽略 Git。
- `deliverables/*/reports/`：本地报告 bundle，忽略 Git。
- `audio_cache/`：本地 TTS 缓存，忽略 Git。

## 工具入口

### 小度风扇

- `tools/cases/generate_formal_assets.py`
- `tools/debug/run_post_restructure_fullflow.py`
- `tools/debug/run_missing_nonreg_cases.py`
- `tools/debug/run_remaining_voice_reg_batch.py`
- `tools/debug/generate_full_formal_aggregate.py`
- `tools/debug/apply_fresh_full_suite_convergence.py`
- `tools/debug/run_timeout_volume_probe.py`
- `tools/debug/run_fresh_closure_targets.py`

### 好太太晾衣机

- `tools/debug/run_htt_handshake_formal_suite.py`
- `tools/debug/run_htt_numeric_probe.py`
- `tools/debug/run_htt_active_passive_playid_sweep.py`
- `tools/debug/run_htt_followup_checks.py`
- `tools/debug/run_htt_voice_restricted_probe.py`
- `tools/debug/run_htt_active_only_remaining.py`
- `tools/debug/run_htt_active_only_phrase_probe.py`
- `tools/debug/run_htt_pyaudio_route_probe.py`
- `tools/debug/run_listenai_endpoint_meter_probe.py`
- `tools/serial/fan_proto_handshake_probe.py`

## 执行原则

1. 先确认烧录和可测性门禁，再进入正式用例。
2. 数值项先测固件真实值，再与需求比对。
3. 默认值验证前执行 `config.clear -> reboot -> burn`，避免历史配置污染。
4. 协议结论使用协议口原始帧；日志 `send msg::` 只能作为辅助。
5. 保存/掉电保持结论必须看到保存闭环后再重启或断电。
6. raw FAIL 如果是断言、窗口、状态污染或前置条件问题，必须修验证逻辑并重跑，不能留到最终 FAIL。
7. 最终 FAIL 只允许是固件问题或需求错误；环境问题归 BLOCKED，人工项归 TODO。

## 清理规则

提交前删除或保持忽略：

- `result/`
- `audio_cache/`
- `deliverables/*/reports/`
- `tools/burn_bundle/windows/app.bin`
- `tools/burn_bundle/windows/burn.log`
- `tools/burn_bundle/windows/burn_tool.log`
- `tools/burn_bundle/linux/app.bin`
- `tools/burn_bundle/linux/burn.log`
- `tools/burn_bundle/linux/burn_tool.log`
- `__pycache__/`、`.venv/`、临时固件压缩包和解压副本

## Git 同步颗粒度

同步到远端时必须保证另一台 PC 拉取仓库后具备完整 skill 能力：

- 必须提交核心入口和规则：`SKILL.md`、`README.md`、`plan.md`、`orion.skilltest.json`、`references/docs/`、`references/fullflow-validation-method.md`、`references/modular-validation-workflow.md`、`references/evidence-rules.md`、`references/repo-workflow.md`。
- 必须提交可复用能力池和适配资料：`references/validation-pool/`、`references/project-profiles/`、稳定的 `deliverables/<project_key>/plan/`、`deliverables/<project_key>/cases/`、`deliverables/<project_key>/archive/`。
- 必须提交可执行资产：`tools/`、`cucumber_test/README.md`、`cucumber_test/runtime/`、`cucumber_test/tools/`、`cucumber_test/00_assessment/` 到 `06_migration/` 的设计说明。
- 新增或修改功能模块、执行入口、项目 profile、Cucumber/native step、烧录/gate 逻辑或断言规则时，必须同步更新对应文档、Feature/用例、profile 和 `orion.skilltest.json`。
- 不提交本地运行证据：`result/`、`audio_cache/`、`deliverables/*/reports/`、`deliverables/formal_suite_runs/`、Cucumber debug reports、日志、烧录 staging、临时固件包和 Python 缓存。
- 发布前至少运行 `python3 -m json.tool orion.skilltest.json >/tmp/orion.skilltest.validated.json`，并对改动的 Python 文件运行 `python3 -m py_compile ...`；最后用 `git status --short` 和 `git diff --cached --name-only` 核对没有遗漏必需文件。
