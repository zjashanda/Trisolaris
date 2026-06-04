# Cucumber 调试区

所有 Cucumber 相关调试材料都放在本目录下，避免污染正式 `result/`、`deliverables/` 和根目录。

| 子目录 | 用途 |
| --- | --- |
| `logs/` | behave/cucumber 执行日志、临时 stdout |
| `reports/` | cucumber.json、junit.xml、临时 html/md 报告 |
| `evidence/` | 与 Cucumber 场景关联的串口/音频/协议证据副本或索引 |
| `sandbox/` | 临时 feature、step、转换脚本试验 |

规则：

- 本目录内容默认不作为正式验证结论。
- 只有经过 Trisolaris 收敛并同步到正式报告后，才可作为最终证据引用。
- 后续若提交 Git，只提交 README、方案和稳定样例；大体积日志和运行报告不提交。
