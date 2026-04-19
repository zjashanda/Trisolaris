# Trisolaris

Trisolaris 是一个面向离线语音项目验证的本地工作仓库，当前主要承载 `CSK5062小度风扇` 项目的全链路测试能力。

仓库当前已经落地的能力包括：

- 根据需求文档动态生成测试方案
- 根据需求文档动态生成正式测试用例 Excel
- 使用本地烧录工具完成固件烧录
- 基于 `COM36` / `COM38` / `COM39` 执行串口与功能验证
- 使用指定声卡进行语料播报
- 汇总测试结果、失败分析与统一证据目录

## 当前项目范围

当前仓库重点服务于：

- `CSK5062小度风扇需求/`
- `deliverables/csk5062_xiaodu_fan/`
- `tools/`

同时仓库中保留了 `mars-moon/` 目录，作为历史参考与方法借鉴目录。

## 目录说明

- `CSK5062小度风扇需求/`: 输入侧需求资料，保持干净，不放执行产物
- `deliverables/`: 方案、用例、报告等稳定产物
- `tools/`: 烧录、串口、音频、用例生成、调试脚本
- `audio_cache/`: 本地合成语料缓存
- `references/`: 方法说明、验证规则、专项记录
- `mars-moon/`: 参考项目目录

## 当前全链路入口

正式全链路执行脚本：

- `tools/debug/run_post_restructure_fullflow.py`

执行前会先动态刷新：

- `deliverables/csk5062_xiaodu_fan/plan/测试方案.md`
- `deliverables/csk5062_xiaodu_fan/archive/测试用例-正式版.md`
- `deliverables/csk5062_xiaodu_fan/cases/测试用例-正式版.xlsx`

动态生成脚本：

- `tools/cases/generate_formal_assets.py`

## 烧录规则

当前仓库统一使用本地烧录入口：

- `tools/burn_bundle/run_fan_burn.ps1`
- `tools/burn_bundle/run_fan_burn.sh`

固定规则：

1. 先删除本地烧录目录中的旧 `app.bin`
2. 将待烧录固件复制到本地烧录目录并重命名为 `app.bin`
3. 使用本地 burn bundle 执行烧录
4. 通过烧录日志和启动版本日志双重确认烧录成功

## 串口与设备约束

- 协议串口：`COM36 @ 9600`
- 日志串口：`COM38 @ 115200`
- 控制口：`COM39`
- 播报声卡：`VID_8765&PID_5678:8_804B35B_1_0000`

## 当前正式报告

本轮保留的正式报告目录：

- `deliverables/csk5062_xiaodu_fan/reports/20260419_162517_post_restructure_fullflow/`

该目录下统一包含：

- `测试方案.md`
- `测试用例-正式版.xlsx`
- `case_results.json`
- `failure_analysis.md`
- `execution_summary.md`
- `burn.log`
- `burn_tool.log`
- `com36.log`
- `com38.log`

## 工作原则

- 每次启动先读取并同步 `plan.md`
- 先读需求，再动态生成方案和用例，再执行验证
- 功能验证、参数一致性、异常稳定性三层并行收敛
- 协议结论以 `COM36` 为准
- 保存类结论必须先看到保存完成日志
- 需求目录保持输入态，执行产物统一写到 `deliverables/`
