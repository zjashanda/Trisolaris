# Trisolaris 正式全集执行报告

- 项目：`csk5062_xiaodu_fan`
- Adapter：`xiaodu-5062`
- 需求目录：`项目需求/CSK5062小度风扇需求`
- 固件：`项目需求/CSK5062小度风扇需求/fw-csk5062_xiaodu_fan-v1.0.0.bin`
- 结果目录：`deliverables/formal_suite_runs/20260429_221703_xiaodu5062_unified_full_suite_r1`
- 统计：`PASS=70 / FAIL=1 / TODO=1 / BLOCKED=0 / TOTAL=72`
- 收敛说明：REG-CFG-005 初次 targeted closure 因注册提示时序过快 BLOCKED；已修正为单句固定等待后复测 PASS，并重新聚合 72 条正式用例。

## 关键产物

- `main_case_results`：`deliverables/csk5062_xiaodu_fan/reports/20260429_221705_xiaodu5062_unified_full_suite_r1_main_fullflow/03_execution/case_results.json`
- `supplement_case_results`：`deliverables/csk5062_xiaodu_fan/reports/20260429_224030_xiaodu5062_unified_full_suite_r1_missing_nonreg/03_execution/case_results.json`
- `voice_summary`：`result/csk5062_xiaodu_fan/0429231028_73_remaining_voice_reg_batch_summary/summary.json`
- `closure_case_results`：`deliverables/csk5062_xiaodu_fan/reports/20260429_231733_xiaodu5062_unified_full_suite_r1_regcfg005_closure_r3/03_execution/case_results.json`
- `aggregate_case_results`：`deliverables/csk5062_xiaodu_fan/reports/20260429_232027_xiaodu5062_unified_full_suite_r1_formal_aggregate_converged/aggregate_case_results.json`
- `aggregate_report`：`deliverables/csk5062_xiaodu_fan/reports/20260429_232027_xiaodu5062_unified_full_suite_r1_formal_aggregate_converged/aggregate_report.md`
- `classification`：`deliverables/csk5062_xiaodu_fan/plan/20260429_221703_formal_suite_模块化验证池匹配结果.md`

## 非 PASS 项

| 用例ID | 状态 | 结论 |
| --- | --- | --- |
| `SESS-001` | `TODO` | 本轮保留为人工验证；已补充启动连续日志作为辅助证据 |
| `CFG-VOL-001` | `FAIL` | 烧录后探测默认音量档位=2，需求=3；启动配置 raw volume=1，期望 raw≈2 |

## 阶段日志

- `xiaodu_main_fullflow` rc=0 log=`deliverables/formal_suite_runs/20260429_221703_xiaodu5062_unified_full_suite_r1/logs/02_xiaodu_main_fullflow.log`
- `xiaodu_missing_nonreg` rc=0 log=`deliverables/formal_suite_runs/20260429_221703_xiaodu5062_unified_full_suite_r1/logs/03_xiaodu_missing_nonreg.log`
- `xiaodu_remaining_voice_reg` rc=0 log=`deliverables/formal_suite_runs/20260429_221703_xiaodu5062_unified_full_suite_r1/logs/04_xiaodu_remaining_voice_reg.log`
- `xiaodu_regcfg005_closure` rc=0 log=`deliverables/formal_suite_runs/20260429_221703_xiaodu5062_unified_full_suite_r1/logs/05_xiaodu_regcfg005_closure.log`
- `xiaodu_generate_72_aggregate` rc=0 log=`deliverables/formal_suite_runs/20260429_221703_xiaodu5062_unified_full_suite_r1/logs/06_xiaodu_generate_72_aggregate.log`
- `xiaodu_regcfg005_closure_r3_fixed_timing` rc=0 log=`result/csk5062_xiaodu_fan/20260429_unified_regcfg005_closure_r3.log`
- `xiaodu_generate_72_aggregate_converged` rc=0 log=`deliverables/csk5062_xiaodu_fan/reports/20260429_232027_xiaodu5062_unified_full_suite_r1_formal_aggregate_converged/aggregate_report.md`
