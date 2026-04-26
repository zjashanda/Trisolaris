# Plan

## 2026-04-19 Current Round
- [completed] Read `plan.md` and reload the current repo / requirement / fullflow state.
- [completed] Preserve every evidence path referenced by the latest formal deliverables inside `deliverables/csk5062_xiaodu_fan/reports/20260419_162517_post_restructure_fullflow/04_preserved_result_refs/`.
- [completed] Delete earlier test data: remove old report bundles and clear the old `result/` raw-history directory while keeping the latest bundle intact.
- [completed] Verify only the latest report bundle remains and that the current formal outputs no longer depend on deleted external `result/` paths.
- [completed] Check Git preconditions for publishing the current directory and push the root repo to `zjashanda/Trisolaris`.
- [completed] Add a root `README.md` for the published repository and switch it to public.
- [completed] Confirm `mars-moon/` is included as a subdirectory inside `Trisolaris`.
- [completed] Export `tools/burn_bundle` as an independent repository named `burn_bundle`, keeping only `linux/`, `windows/`, plus a dedicated `README.md` and `.gitignore`.
- [completed] Exclude the root-level wrapper scripts from the exported `burn_bundle` repo, and also exclude runtime artifacts such as `windows/app.bin`, `windows/burn.log`, and `windows/burn_tool.log`.
- [completed] Create and push the standalone public GitHub repository `zjashanda/burn_bundle`.
- [completed] Verify the `burn_bundle` remote state: `main` branch exists, repo is public, and the published contents match the intended export set.
- [completed] Add firmware override support to `tools/debug/run_post_restructure_fullflow.py` so one requirement set can validate multiple target `.bin` files under `固件/`.
- [completed] Re-align the generated plan / cases / runner with the current requirement document before validating `xieyierror.bin` and `yichang.bin`.
- [completed] Fix the fullflow runner so it no longer depends on deleted historical `result/` directories for late voice-registration checks.
- [completed] Re-run fullflow for `固件/xieyierror.bin` and collect a complete bundle plus failure analysis.
- [completed] Run fullflow for `固件/yichang.bin` and collect a complete bundle plus failure analysis.
- [completed] Compare both bundles against the current requirement and summarize each firmware's concrete defects.

## Current Focus
- Current requirement has already changed to `唤醒时长=15s`、`音量档位=5`、`默认音量=3`、`唤醒词掉电保存=是`、`音量掉电保存=是`; the generated plan / cases / runner must match these values first.
- The previous `xieyierror.bin` round stopped near the end because `tools/debug/run_post_restructure_fullflow.py` still referenced deleted legacy `result/` evidence for `REG-CFG-003/004` and `REG-CONFLICT-001`.
- The requirement / generator / runner mismatch has been repaired, including dynamic handling for `音量掉电保存=是` and live execution of the late voice-registration retry / conflict checks.
- Both target firmwares have finished a complete fullflow run; next is side-by-side defect comparison and归因输出.

## Live Progress
- [done] Read `plan.md` and reload the repo state for this firmware-comparison round.
- [done] Reconfirm the current requirement baseline from `需求文档.md`: `15s / 5 档 / 默认音量 3 / 唤醒词保存 是 / 音量保存 是`.
- [done] Repair the generated assets / runner so the current requirement and the executable fullflow are consistent.
- [done] `xieyierror.bin` clean rerun finished; latest bundle: `deliverables/csk5062_xiaodu_fan/reports/20260419_215522_xieyierror_fullflow_r2`.
- [done] `yichang.bin` clean rerun finished; latest bundle: `deliverables/csk5062_xiaodu_fan/reports/20260419_223031_yichang_fullflow`.
- [done] Deliver the final per-firmware defect analysis.

## Execution Rules Still In Force
- Fixed ports: `COM36 @ 9600`, `COM38 @ 115200`, `COM39`.
- Burn entry inside Trisolaris remains `tools/burn_bundle/run_fan_burn.ps1`.
- Protocol conclusions must come from `COM36`; `COM38` is only auxiliary evidence.
- Save-related conclusions require the save-finished log first.
- Wait until the previous playback ends before the next audio; default cadence is `4.5s`, but playback completion allows earlier continuation.
- Requirement validation must cover: function enablement, parameter consistency, and abnormal behavior.
- For save / non-save behavior, verify both the functional effect before power loss and the post-reboot persistence expectation.

## 2026-04-20 Current Round
- [completed] Read `plan.md` and reload the latest firmware-validation bundles.
- [completed] Generate one standalone detailed markdown test report inside each target bundle directory for `xieyierror.bin` and `yichang.bin`.
- [completed] Ensure each report explicitly records requirement baseline, test method, pass/fail/manual results, detailed fail analysis, and manual/blocked explanations.

## 2026-04-20 Rework Round
- [completed] Rework the validation flow to add a burn-after testability gate, capture the initial default volume immediately after burn, and replace wake-timeout `None` with a measured concrete upper-limit result.
- [completed] Re-run `xieyierror.bin` with the updated flow, then regenerate its detailed markdown report. Latest bundle: `deliverables/csk5062_xiaodu_fan/reports/20260420_121440_xieyierror_fullflow_gate_r3`.
- [completed] Re-run `yichang.bin` with the updated flow; gate failed and the flow stopped immediately with an explicit untestable-firmware report. Latest bundle: `deliverables/csk5062_xiaodu_fan/reports/20260420_121250_yichang_fullflow_gate_r2`.
- [doing] Return the new report paths and the key corrections made versus the previous reports.

## 2026-04-20 Rework Progress
- [done] Read the user's correction: gain verification should be manual, wake timeout must be measured concretely, default volume must be confirmed on the first boot after burn, and each burn must start with a testability gate.
- [done] Patch the runner/report flow to enforce the new rules before starting the rerun.
- [done] Make the testability gate a mandatory pre-check before every firmware run and land it in the runner flow.
- [done] Execute the two firmware reruns and regenerate the reports.

## 2026-04-20 Live Progress
- [done] Confirm the two target bundle directories still exist and are the latest single-firmware result directories.
- [done] Build the per-bundle detailed report generator and write the two markdown reports into the corresponding bundle roots.
- [done] Return the generated report paths to the user for review.

## 2026-04-20 Boot Config Evidence
- [completed] Read `plan.md` and extract the post-burn first-boot `Running Config` fields from the three latest formal fullflow bundles.
- [completed] Return the exact startup config values for the user to inspect, including the repeated-boot symptom on `yichang.bin`.

## 2026-04-20 Failure Fixback Analysis
- [completed] Read `plan.md` and collect the three formal fullflow bundles as the current analysis baseline.
- [completed] Inspect the current FAIL items one by one, separate real firmware defects from remaining assertion/report issues, and derive concrete firmware-side repair suggestions.
- [completed] Return a per-failure fixback list with evidence paths, expected behavior, actual behavior, and suggested repair direction.

## 2026-04-20 Formal Validation Next Step
- [completed] Re-confirm with the user that the revised timeout/volume assertion design is accepted.
- [completed] Run the formal fullflow with the corrected wake-timeout and volume-step logic for all three firmwares under `固件/`.
- [completed] Collect the three result bundles: `20260420_153111_base_formal_fullflow_r1`, `20260420_160258_xieyierror_formal_fullflow_r1`, `20260420_163604_yichang_formal_fullflow_r1`.

## 2026-04-20 Markdown Encoding Fix
- [completed] Read `plan.md`, locate the garbled markdown issue in `deliverables/csk5062_xiaodu_fan/plan/test_methods_20260420.md`, and confirm the old file content was already written as question marks.
- [completed] Rewrite `deliverables/csk5062_xiaodu_fan/plan/test_methods_20260420.md` with full Chinese content and save it as UTF-8 with BOM for better Windows compatibility.
- [completed] Record the follow-up rule: future markdown outputs must use Chinese text and avoid writing through a path that can down-convert Chinese into question marks.

## 2026-04-20 Timeout/Volume Revalidation
- [completed] Read `plan.md`, reload the current runner/probe scripts, and restate the user's corrected timeout/volume assertions.
- [completed] Repair the serial-log capture chain after reboot/powercycle, extend the timeout probe wait windows, and rerun the dedicated timeout/volume probe.
- [completed] Write the current requirement-point test/assertion methods into `deliverables/csk5062_xiaodu_fan/plan/test_methods_20260420.md`.
- [completed] Clean the intermediate timeout/volume probe bundles and keep only the final validated bundle `20260420_145358_timeout_volume_probe_r3`.

## 2026-04-20 Validation Bugfix Follow-up
- [done] Analyze why `CFG-WAKE-001` and `CFG-VOL-002` produced wrong conclusions against the user's manual evidence.
- [done] Replace the current wake-timeout behavioral probe with explicit wake-response-end / `TIME_OUT` / `MODE=0` marker timing.
- [done] Replace the current volume-step inference with a step-by-step level verification based on `mini player set vol` runtime levels.
- [done] Re-run the affected firmware in the main fullflow chain and confirm the corrected assertions now land as PASS on the formal runs.

## 2026-04-20 Skill Publish Round
- [done] Read `plan.md`, reload the current repo dirty state, and confirm the publish target is the current `trisolaris` skill logic only.
- [done] Inspect the skill-facing diffs for the updated wake-timeout / volume-step validation flow and decide the minimum file set that should be committed.
- [done] Update repository metadata so reports, logs, burn runtime artifacts, audio cache, and local firmware payloads stay out of the publish set.
- [done] Stage only the relevant skill files, commit them, and push to `origin` with commit `46a5f5c`.
- [done] Sync the final publish result back into `plan.md` and return the pushed file list to the user.

## 2026-04-20 Fullflow Asset Publish Round
- [done] Read `plan.md` and re-check which generated fullflow assets were still only local.
- [done] Add the current requirement baseline plus the generated plan / methods / formal cases into the publish set so the repo contains the complete static fullflow assets.
- [done] Commit and push the added fullflow assets without bringing runtime logs, burn artifacts, or report bundles into Git. Commit `42b27b2`.
- [done] Sync the final uploaded file list back into `plan.md` and return it to the user.

## 2026-04-20 报告中文化 Round
- [done] Read `plan.md` and confirm the current issue: the detailed report generator still uses English template text and only drills down on FAIL / MANUAL items.
- [done] Update the detailed report generator so the report body, headings, labels, and default output filename are all Chinese, and add PASS detail sections instead of only listing FAIL details.
- [done] Regenerate the local detailed reports from the updated generator and verify the markdown is readable in Windows with Chinese content.
- [done] Commit and push the report-generator update to `origin`. Commit `e4d9900`.

## 2026-04-20 Skill Rule Sync Round
- [done] Update `SKILL.md` so the skill body explicitly includes the static asset generation chain, the Chinese-report requirement, and the rule that detailed reports must contain PASS / FAIL / 待人工 / 阻塞的完整结构 instead of only failure details.
- [done] Commit and push the `SKILL.md` update to `origin`. Commit `3bcad21`.
- [done] Return the updated rule summary to the user and reserve task 2 for re-organizing today's latest three firmware result bundles.


## 2026-04-22 好太太晾衣机需求梳理 Round
- [done] 读取 `plan.md` 并检查 `项目需求/好太太晾衣机` 目录下的现有文件。
- [done] 阅读需求材料（`好太太晾衣机需求迭代.md`、词表协议 Excel、`语音关闭逻辑.png`，并确认压缩包仅包含固件镜像），提炼项目需求逻辑。
- [done] 向用户输出项目的功能结构、命令逻辑、状态约束和当前可见的疑点。

## 2026-04-22 好太太晾衣机有效需求整理 Round
- [done] 再次读取 `plan.md`，确认本轮任务为先整理“当前有效需求”再等待用户确认是否继续拆测试点。
- [done] 合并 `电控词表协议--小好晾衣机语音词条协议-20260309.xlsx`、`好太太晾衣机需求迭代.md` 与 `语音关闭逻辑.png`，整理当前有效需求清单。
- [done] 输出一份干净的最终版需求清单到 `项目需求/好太太晾衣机/当前有效需求清单_20260422.md`，并向用户说明合并口径与待确认项。

## 2026-04-22 好太太晾衣机烧录验活与测试执行 Round
- [done] 读取 `plan.md`，确认本轮顺序必须是“先烧录 + 最小验活，确认可用后再写测试方案/用例并执行”。
- [done] 定位 `fw-csk3022-htt-clothes-airer-v1.0.9.bin`、烧录入口、串口约定和现有测试链路，准备烧录与最小验证。
- [done] 落实目录隔离：好太太的方案、用例、报告、原始结果必须与 `csk5062_xiaodu_fan` 完全分开，且不能改动小度项目既有内容；已建立 `deliverables/csk3022_htt_clothes_airer/` 与 `result/csk3022_htt_clothes_airer/`。
- [done] 根据用户最终确认，当前好太太项目固定串口为：控制 `COM39`、日志烧录 `COM38`、协议 `COM36`；后续判断不再引用 `COM14/COM15` 作为好太太结论依据。
- [done] 按 `tools/burn_bundle/run_fan_burn.ps1` / Windows burn bundle 尝试烧录 `项目需求/好太太晾衣机/fw-csk3022-htt-clothes-airer-v1.0.9.bin` 并收集日志；本次烧录 3 次均失败，日志位于 `result/csk3022_htt_clothes_airer/20260422_113156_v1.0.9_burn_gate/02_burn/`。
- [done] 做最小可用性验证；`COM39/COM38` 启动观察显示当前运行版本为 `1.0.9`，但存在 `MCU is not ready!`，且 `小好小好 -> 打开照明` 门禁未形成业务闭环，当前判定不可继续正式测试。
- [done] 进一步用 `COM36 -> COM38` 做协议注入验证：发送好太太品牌帧 `A5 FA 81 00 20 40 FB` 与播报开启帧 `A5 FA 81 00 69 89 FB` 后，模组均有明确日志响应，说明协议口与模组接收链路可用，当前更像是真实 MCU/整机闭环未 ready，而不是串口映射错误。
- [done] 追加抓取正常上电时的 `COM36 + COM38` 同步日志，确认模组启动后会先在 `COM36` 连续发送品牌查询帧 `A5 FA 7F 01 02 21 FB`，之后再发送心跳帧 `A5 FA 7F 5A 5A D2 FB`；说明协议口侧确实需要 MCU 先返回品牌应答，证据位于 `result/csk3022_htt_clothes_airer/20260422_113156_v1.0.9_burn_gate/03_gate/startup_proto_watch/`。
- [done] 在好太太独立目录下输出当前 gate 结论报告：`deliverables/csk3022_htt_clothes_airer/reports/20260422_113156_v1.0.9_burn_gate_gate_summary/gate_summary.md`。
- [done] 按用户要求单独执行进入烧录模式控制序列：`COM39` 上已发送 `进boot -> 上电 -> 下boot`，记录位于 `result/csk3022_htt_clothes_airer/20260422_113156_v1.0.9_burn_gate/03_gate/20260422_123203_manual_enter_burn_mode/`，该动作仅代表控制序列完成，不直接判定烧录成功。
- [todo] 待用户确认硬件链路/端口映射后，再重新执行烧录闭环与最小验活；在此之前不进入正式测试方案、正式用例和正式执行。

## 2026-04-22 好太太协议握手排查 Round
- [done] 再次读取 `plan.md`，确认当前先暂停烧录，优先分析 `MCU is not ready!` 与协议口握手关系。
- [done] 复核好太太现有证据：启动阶段 `COM36` 连续发出品牌查询 `A5 FA 7F 01 02 21 FB`，日志阶段存在 `MCU is not ready!`，且手工注入好太太品牌应答 `A5 FA 81 00 20 40 FB` 后模组可立即识别处理。
- [done] 形成当前判断：协议口大概率确实需要 MCU 侧在启动窗口内返回品牌应答，单次人工补发可证明链路有效，但还不足以证明整机 MCU ready 闭环已经完整。
- [todo] 下一步若继续联调，优先在上电初期按时序模拟 MCU：先应答品牌查询，再观察是否还持续报 `MCU is not ready!`，必要时再补抓后续心跳/状态握手。
- [doing] 继续按需求文档反推协议握手细节：已从词表协议 Excel 进一步确认，除上电品牌查询 `0x0102 -> 0x0020/0x0021/0x0022` 外，还存在 `0x7F/0x83` 双向心跳机制：语音模组可发 `0x7F 0x5A5A` 让 MCU 回 `0x83 0x5A5A`，MCU 也会周期发 `0x83 0xA5A5` 让模组回 `0x7F 0xA5A5`；当前准备做自动应答联调验证。
- [done] 为当前联调补充了独立串口探针 `tools/serial/fan_proto_handshake_probe.py`：可在 `COM39` 上电控制下同步抓取 `COM36/COM38`，并按规则自动应答指定协议帧，方便验证品牌握手和心跳握手是否是 `MCU is not ready!` 的根因。
- [doing] 使用新探针执行“品牌应答 + 心跳应答”最小联调实验，观察 `MCU is not ready!`、启动协议序列和后续业务可用性是否变化。
- [done] 已完成启动握手对比实验 1（仅自动回品牌应答）：目录 `result/csk3022_htt_clothes_airer/20260422_113156_v1.0.9_burn_gate/04_debug/20260422_124818_auto_brand_only_boot/`；虽然在启动窗口自动回了 `A5 FA 81 00 20 40 FB`，但随后日志仍出现 `MCU is not ready!`，说明仅品牌应答不足以让 MCU ready。
- [done] 已完成启动握手对比实验 2（品牌应答 + 心跳应答）：目录 `result/csk3022_htt_clothes_airer/20260422_113156_v1.0.9_burn_gate/04_debug/20260422_124905_auto_brand_and_heartbeat_reply/`；当模组发送 `A5 FA 7F 5A 5A D2 FB` 时自动回 `A5 FA 83 5A 5A D6 FB` 后，日志中不再出现 `MCU is not ready!`，并可持续看到模组正常接收该心跳应答。
- [done] 已完成启动握手对比实验 3（补充 MCU 主动查询验证）：目录 `result/csk3022_htt_clothes_airer/20260422_113156_v1.0.9_burn_gate/04_debug/20260422_125013_auto_brand_heartbeat_and_mcu_query/`；周期发送 `A5 FA 83 A5 A5 6C FB` 后，模组会回 `A5 FA 7F A5 A5 68 FB`，与词表里“MCU 主动查询 / 模组回复 MCU 查询”的双向心跳定义一致。
- [done] 当前阶段性结论：真实 MCU 至少需要在协议口完成两类握手——启动品牌应答 `0x0102 -> 0x0020`，以及对模组心跳 `0x7F 5A5A` 返回 `0x83 5A5A`；此外 MCU 侧还应按文档周期发送 `0x83 0xA5A5` 做通讯探测，模组会回复 `0x7F 0xA5A5`。
- [todo] 基于上述握手闭环，下一步可继续做“维持握手常驻 + 最小语音/业务闭环”验证，再判断是否已经具备正式测试条件。
- [done] 已在握手常驻仿真下完成最小语音闭环验证：目录 `result/csk3022_htt_clothes_airer/20260422_113156_v1.0.9_burn_gate/04_debug/20260422_125459_voice_gate_with_handshake_emulator/`；当常驻维持 `0x0102 -> 0x0020`、`0x7F 5A5A -> 0x83 5A5A`、并周期发送 `0x83 0xA5A5` 时，`COM38` 成功识别 `小好小好` / `打开照明`，`COM36` 分别出现 `A5 FA 7F 00 01 1F FB` 与 `A5 FA 7F 00 09 27 FB`，说明固件本体在握手补齐后可进入正常语音业务闭环。
- [done] 当前根因进一步收敛：此前 gate 失败不是固件命令链路本身失效，而是实机 MCU 协议握手未补齐，导致模组一直处在 `MCU not ready` 态；一旦按需求文档补齐品牌与心跳链路，语音业务即可跑通。
- [todo] 后续需要决定正式测试口径：是推动真实 MCU/整机修正协议握手，还是在测试夹具侧维持协议仿真后继续跑正式方案与用例；在口径确认前，仍不直接进入“整机正式通过”结论。
## 2026-04-22 好太太握手仿真正式执行 Round
- [done] 读取 `plan.md`，确认用户已选择按“握手仿真常驻”口径继续推进好太太方案、用例与执行。
- [doing] 梳理握手仿真口径下的正式测试范围，并准备在好太太独立目录中落方案、用例和首轮执行链路。
- [todo] 复用现有握手仿真 + 音频播放工具，跑首轮正式执行并输出独立报告；报告必须明确“仿真 MCU 握手口径”与“非真实整机 MCU 已修复”的边界。
- [done] 已在好太太隔离目录下生成握手仿真正式方案：`deliverables/csk3022_htt_clothes_airer/plan/20260422_握手仿真正式测试方案_v1.md`。
- [done] 已生成握手仿真正式用例：`deliverables/csk3022_htt_clothes_airer/cases/20260422_握手仿真正式测试用例_v1.md`。
- [done] 已执行首轮握手仿真正式套件：`result/csk3022_htt_clothes_airer/20260422_133901_htt_handshake_formal_suite/`；本轮共 8 条，PASS 8、FAIL 0、BLOCKED 0。
- [done] 已输出独立执行报告：`deliverables/csk3022_htt_clothes_airer/reports/20260422_133901_htt_handshake_formal_suite/summary.md`。
- [todo] 若后续要把当前结果外推为“整机正式通过”，仍需真实 MCU 按同一握手时序修正协议；当前报告只代表“握手仿真夹具口径下，固件业务链路可用”。
- [done] 再次读取 `plan.md`，确认用户选择继续扩覆盖面，且当前仍保持“握手仿真夹具口径、好太太目录隔离、不影响小度”的执行边界。
- [doing] 准备第二批扩展用例：优先补音量控制、播报开关、语音开关/受限状态、会话超时阻断等当前夹具口径可稳定执行的链路；被动协议注入类验证视执行稳定性再追加。
- [done] 已完成第二批扩展套件执行：`result/csk3022_htt_clothes_airer/20260422_135332_htt_handshake_formal_suite/`；本轮共 17 条，PASS 12、FAIL 5、BLOCKED 0；对应报告为 `deliverables/csk3022_htt_clothes_airer/reports/20260422_135332_htt_handshake_formal_suite/summary.md`。
- [done] 已归因首批失败点：`VOL-UP-001` / `VOL-DOWN-001` / `REPORT-OFF-001` 在日志中只有唤醒没有后续命令，下轮优先改用词表主命令短语；`VOICE-OFF-BLOCK-001` / `VOICE-ON-RECOVER-001` 暴露出“关闭语音”前置唤醒缺失、以及受限态判定需要按状态机重写的问题。
- [doing] 正在修正第二轮复测脚本：补充按 `case_id` 定向复跑能力，改用更稳的主命令短语（`调大音量` / `调小音量` / `关闭播报功能`），并按有效需求重写“语音关闭/恢复”会话顺序与断言。
- [done] 已完成脚本修正：`tools/debug/run_htt_handshake_formal_suite.py` 现支持 `--case-id` 定向复跑与 `--suite-tag` 标记结果目录；静态资产升级为 `deliverables/csk3022_htt_clothes_airer/plan/20260422_握手仿真正式测试方案_v3.md` 与 `deliverables/csk3022_htt_clothes_airer/cases/20260422_握手仿真正式测试用例_v3.md`。
- [done] 已完成失败项定向复测闭环：五条原 FAIL 项复测目录为 `result/csk3022_htt_clothes_airer/20260422_142715_htt_handshake_formal_suite_failed_rerun_r2_final/`，结果 PASS 5、FAIL 0、BLOCKED 0；报告位于 `deliverables/csk3022_htt_clothes_airer/reports/20260422_142715_htt_handshake_formal_suite_failed_rerun_r2_final/summary.md`。
- [done] 已执行全量 17 条正式套件复跑确认：`result/csk3022_htt_clothes_airer/20260422_143048_htt_handshake_formal_suite_full_r3/`；结果 PASS 17、FAIL 0、BLOCKED 0；最终汇总报告位于 `deliverables/csk3022_htt_clothes_airer/reports/20260422_143048_htt_handshake_formal_suite_full_r3/summary.md`。
- [done] 当前结论维持不变：以上结果仅代表“握手仿真夹具口径”下该固件业务链路可用；若要外推为真实整机通过，仍需真实 MCU 按同样时序补齐品牌/心跳/通讯探测握手。


## 2026-04-22 好太太握手仿真续跑修正 Round
- [done] 再次读取 `plan.md`，复核好太太最新方案/用例 v4 与 `deliverables/csk3022_htt_clothes_airer/reports/20260422_151223_htt_handshake_formal_suite_full_v4_r1/summary.md` 的失败分布。
- [done] 对比 `20260422_143048_htt_handshake_formal_suite_full_r3` 与 v4 失败日志，确认 v4 大面积 FAIL 主要来自跨用例状态污染：新增被动协议后，后续主动语音用例在 `voice=0` 等脏基线上启动。
- [done] 已修正 `tools/debug/run_htt_handshake_formal_suite.py`：除纯启动观察与自带恢复出厂注入的被动用例外，其余用例执行前自动注入 `0x006C` 恢复出厂，并等待统一基线 ready 后再播音，避免套件内状态串扰。
- [done] 继续补修脚本时序：把恢复出厂后的 `25s hold` 计入统一等待窗口，并为含语音交互的用例追加尾部观测时长，避免命令已下发但被过早截断。
- [done] 已完成修正后冒烟验证：`result/csk3022_htt_clothes_airer/20260422_161031_htt_handshake_formal_suite_baseline_smoke_r2/` 中 `CTRL-LIGHT-001`、`VOL-UP-001` 已恢复 PASS；`VOICE-ON-RECOVER-001` 也在 `deliverables/csk3022_htt_clothes_airer/reports/20260422_161757_htt_handshake_formal_suite_voice_followup_r3/summary.md` 中恢复 PASS。
- [done] 已重跑 v4 全量正式套件：`result/csk3022_htt_clothes_airer/20260422_162226_htt_handshake_formal_suite_full_v4_r2/`；结果 `PASS 20 / FAIL 2 / BLOCKED 0`，对应报告为 `deliverables/csk3022_htt_clothes_airer/reports/20260422_162226_htt_handshake_formal_suite_full_v4_r2/summary.md`。
- [done] 已对剩余 2 条 FAIL 做定向复测确认：`result/csk3022_htt_clothes_airer/20260422_164545_htt_handshake_formal_suite_final_fail_rerun_r1/`；两条用例均稳定复现，说明不再是套件串扰或截断问题。
- [done] 当前已将剩余问题收敛为握手仿真口径下的真实固件缺陷：`VOICE-OFF-BLOCK-001` 中主动“关闭语音”后再次唤醒并说“打开照明”仍下发 `0x0009`；`PASSIVE-VOICE-ON-001` 中被动 `0x0012` 关语音后即使已下发 `0x0017`，后续“打开照明”仍被日志判定 `voice is closed!`、未恢复业务协议。
- [todo] 如用户需要，可基于以上两条剩余 FAIL 继续输出专项缺陷报告 / 固件修复建议，或把当前 `20 PASS + 2 真实 FAIL` 结果整理成最终对外交付口径。

## 2026-04-22 好太太需求-方案-验证追踪 Round
- [done] 再次读取 `plan.md`，确认本轮任务是把“需求功能点 -> 需求解析依据 -> 测试方案 -> 用例 -> 验证方法 -> 最新结果”完整串起来，并与当前正式执行结果一一对应。
- [done] 已复核需求源、有效需求清单、v4 方案、v4 用例、最新全量报告与最终 FAIL 复测报告，统一当前追踪口径为“握手仿真夹具口径”。
- [done] 已输出独立追踪矩阵：`deliverables/csk3022_htt_clothes_airer/plan/20260422_req_traceability_v1.md`，内容包含需求解析方法、全量功能点总表、功能/数值验证方法、22 条正式用例与需求的一一对应关系、以及当前 2 条真实缺陷结论。
- [done] 已准备向用户回传简版总览：说明哪些功能点已覆盖、哪些仍未覆盖、功能怎么验、数值怎么验、当前 PASS/FAIL 分布与证据路径。

## 2026-04-22 好太太数值验证口径修正 Round
- [done] 再次读取 `plan.md`，接收用户新增要求：数值项必须先测固件真实值，再与需求值比对，不能拿需求值反推等待窗口。
- [done] 对照 `deliverables/csk5062_xiaodu_fan/plan/test_methods_20260420.md` 与 `tools/debug/run_post_restructure_fullflow.py`，抽取“小度方案”的数值验证方法模板。
- [done] 修订好太太需求追踪/测试方案文档：把“功能验证”和“数值验证”彻底拆开，逐条写清楚需求解析、方案设计、验证步骤、当前结论与未闭环项。
- [done] 已生成修正版追踪矩阵：`deliverables/csk3022_htt_clothes_airer/plan/20260422_req_traceability_v2.md`。
- [done] 已同步修正静态方案/用例与 runner 口径：
  - `deliverables/csk3022_htt_clothes_airer/plan/20260422_握手仿真正式测试方案_v4.md`
  - `deliverables/csk3022_htt_clothes_airer/cases/20260422_握手仿真正式测试用例_v4.md`
  - `tools/debug/run_htt_handshake_formal_suite.py`
- [done] 明确修正以下口径：
  - 会话超时：改为测量真实超时点（响应结束 -> `TIME_OUT` / 会话回收），再比对 `25s`
  - 音量档位：改为测出真实可达档位序列与边界，再比对 `1~5 档`
  - 默认音量：改为测首次上电/恢复出厂后的真实运行音量，再比对“默认 3 档”
  - 播报次数：改为记录真实播放次数，再比对需求“0x0082=1 次、0x0069=2 次”
  - 语音关闭受限窗口：改为测真实受限持续时长，再比对 `10s`
- [done] 已把“需求功能点 -> 解析依据 -> 测试方案 -> 功能验证 -> 数值验证 -> 当前状态”的一一对应说明沉淀到 `deliverables/csk3022_htt_clothes_airer/plan/20260422_req_traceability_v2.md`，并准备结合本轮数值阻塞结论一并向用户回传。

## 2026-04-22 好太太数值专项实测 Round
- [done] 再次读取 `plan.md`，确认用户本轮已把数值专项目标收敛为 3 项：`唤醒超时`、`恢复出厂默认音量档位`、`音量总档位数`。
- [done] 复核上一轮数值探针首跑失败证据：`result/csk3022_htt_clothes_airer/20260422_194759_htt_numeric_probe_r1/` 中 `timeout_probe` 未抓到唤醒标记，`volume_*` 分支也未形成有效调音闭环，因此当前 `FAIL` 不能直接当成固件最终结论。
- [done] 已完成 `tools/debug/run_htt_numeric_probe.py` 重构：
  - 超时项改为复用已验证稳定的握手仿真/播音时序，直接抓 `Wakeup / 0x0001 -> TIME_OUT / MODE=0` 的实测时间差；
  - 默认音量与档位数改为按用户要求走“恢复出厂 -> 从默认位逐步调大到上边界 / 逐步调小到下边界 -> 统计真实边界步数 -> 反推默认档位与总档位数”，不再拿需求值反推等待窗口或直接用需求档位做结论。
- [done] 已完成脚本重构并重跑数值探针：`result/csk3022_htt_clothes_airer/20260422_200618_htt_numeric_probe_r2/`；原始报告位于 `deliverables/csk3022_htt_clothes_airer/reports/20260422_200618_htt_numeric_probe_r2/summary.md`。
- [done] 已追加环境复核：
  - 基础控制用例 `SESS-WAKE-001` 单独复跑目录：`result/csk3022_htt_clothes_airer/20260422_201458_htt_handshake_formal_suite_numeric_debug_now/`，结果同样未出现 `0x0001`；
  - 3 个可见 ListenAI 渲染设备逐个试播目录：`result/csk3022_htt_clothes_airer/device_key_probe/`，都未抓到唤醒；
  - 端点扫描与音量快照：`result/csk3022_htt_clothes_airer/20260422_200618_htt_numeric_probe_r2/diagnostics/`。
- [done] 已把当前结论修正为“环境阻塞，不直接外推为固件数值 FAIL”，并输出阻塞说明：`deliverables/csk3022_htt_clothes_airer/reports/20260422_200618_htt_numeric_probe_r2/blocker_note.md`。
- [done] 已把该轮补充结论同步回追踪矩阵：`deliverables/csk3022_htt_clothes_airer/plan/20260422_req_traceability_v2.md`。
- [done] 按用户追加口径，已把数值探针里的“唤醒起点”扩展为多标记兜底：优先 `0x0001`，其次 `Wakeup:` / `keyword:`，再其次唤醒响应播报 `play start` / `play id`；后续 bench 恢复后将沿此口径继续测超时。
- [todo] 待 bench 的基础语音唤醒链路恢复后，优先重通 `SESS-WAKE-001`，再重跑 `python tools/debug/run_htt_numeric_probe.py` 完成三项数值闭环。

## 2026-04-22 ??????? bench ???? Round
- [done] ???? `plan.md`????????????????????????? 3 ?????????
- [done] ??????????? `tools/debug/run_listenai_endpoint_meter_probe.py`???? Windows ??????? ListenAI render ?? `GetPeakValue`????????????????????
- [done] ??????????`result/csk3022_htt_clothes_airer/20260422_211434_listenai_endpoint_meter_probe/`?
- [done] ?????`key_2 = VID_8765&PID_5678:8_804B35B_1_0000` ?? `????` ???? `??? (4- ListenAI Audio)` ???????`max_peaks ~= 0.5937`??`key_1` / `key_3` ????????????? Windows -> ListenAI ???????????????????? render????
- [done] ????????????? `SESS-WAKE-001`?`result/csk3022_htt_clothes_airer/20260422_211517_htt_handshake_formal_suite_endpoint_meter_followup/`?
- [done] ?????? FAIL???????????????????????? `COM38` ?? `Wakeup:` / `keyword:` / `MODE=1`?`COM36` ?? `0x0001`?????????? DUT/?????????? PC ??????
- [doing] ??????????/????????? DUT ???????USB ?????/???????????? bench ????? 16:22 ???????????????
- [done] ??? `??? (4- ListenAI Audio)` capture ???`result/csk3022_htt_clothes_airer/20260422_211932_restore_prompt_capture_probe/` ?????? `0x006C` ?????? `restore factory response` + `play start/play id`?????? `capture.wav` ??? `peak=10 / rms?1.70`?????????????? DUT ????????????????????????????? capture ?????? DUT ???
- [todo] ?????????????????????????????????????????? `python tools/debug/run_htt_numeric_probe.py`?

## 2026-04-22 ?????????? Round
- [done] ?? `plan.md`?????????? bench ???????
- [done] ????????????? `????` ??????????`audio_cache/tts/dual_1_3fcec41788.wav`?
- [done] ???????????? `SESS-WAKE-001` ???????????????? `ensure_cached_tts(text="????")` ??/???????????????????????????????
- [todo] ??????????? wav ???????????????????????????

## 2026-04-22 ????? v1.0.9 ?? Round
- [done] ?? `plan.md`???????????????? `????/??????/fw-csk3022-htt-clothes-airer-v1.0.9.bin`?????????????????????
- [doing] ?????? `tools/burn_bundle/run_fan_burn.ps1`??????????????????? `COM39/COM38/COM36`????????????
- [todo] ???? v1.0.9 ???????? burn stdout/stderr?`burn.log`?`burn_tool.log` ?????
- [todo] ???????????????????????? `????` ??????????????????
- [todo] ??????????????? `plan.md`?????????????????

- [done] ??????????????`result/csk3022_htt_clothes_airer/20260422_213411_reburn_v1_0_9/02_burn/`?3 ???????? `CONNECT ROM AND DOWNLOAD RAM LOADER SUCCESS`??????? `END COMMAND FORMAT ERROR` / `RECEIVE OVERTIME`?
- [done] ??????????`result/csk3022_htt_clothes_airer/20260422_213411_reburn_v1_0_9/02_burn_retry_low_baud/`??? `BurnBaud=115200` + `PreBurnWaitMs=3000` ?????????????????????????????
- [done] ???????????`result/csk3022_htt_clothes_airer/20260422_213411_reburn_v1_0_9/03_verify/`?????????? `version 1.0.9`????????? `MCU is not ready!`?
- [done] ?????????????????`result/csk3022_htt_clothes_airer/20260422_213411_reburn_v1_0_9/04_normal_wake_check/`??? `????` / `????` ???????????? ListenAI render ???? `COM38` ? `Wakeup:` / `keyword:` / `MODE=1`?`COM36` ?? `0x0001` / `0x0009`????????????
- [done] ??????????`deliverables/csk3022_htt_clothes_airer/reports/20260422_213411_reburn_v1_0_9/summary.md`?

## 2026-04-22 ??? ready ???? Round
- [done] ?? `plan.md`????????????????????? `ready`?????? `MCU is not ready!`???????????????
- [done] ????????????????????????????????????????????? ready ?????????/????????????????????????
- [done] ?????????
  - ????????`COM38` ???? `MCU is not ready!`?
  - ?? `COM38` ?? `Wakeup:` / `keyword:` / `MODE=1`?
  - `COM36` ??? `0x0001` / `0x0009` ????????
  - ?????????????????? `???? -> ????` ??????
- [todo] ?????????????????????? MCU ?? ready ???????????????????


## 2026-04-22 ??????? Round
- [done] ?? `plan.md`??????????????????? `1` ? `2`?
- [done] ?? 1 ?????? `COM39` ?????????? / ? boot ???????????????? `boot=on` ????? `Uart_Burn_Tool.exe` ?? `COM38`????? `result/csk3022_htt_clothes_airer/20260422_222500_burn_mode_probe/`?`result/csk3022_htt_clothes_airer/20260422_223300_manual_hold_boot_burn_probe/`?`result/csk3022_htt_clothes_airer/20260422_223950_multport_boot_probe/`???????? boot ? `COM38/COM36` ??????????? `COM38` ?????? `RECEIVE OVERTIME` / `END COMMAND FORMAT ERROR`??????? `COM38` ???????????
- [done] ?? 2 ??????????????? `COM38` ?? `heartbeat.ignore 1`????? shell ????????? `result/csk3022_htt_clothes_airer/20260422_225100_heartbeat_ignore_probe/01_shell_cmd_after_restore/`?
- [done] ?????? -> ?? `heartbeat.ignore 1` -> ?? `????` / `????`???????? `result/csk3022_htt_clothes_airer/20260422_225100_heartbeat_ignore_probe/03_reboot_cmd_and_voice_check/`??????`COM38` ??? `MCU is not ready!`?`COM36` ??? `0x0102` ????? `0x5A5A` ????????? `0x0001` / `0x0009`??? `heartbeat.ignore 1` ????????? MCU ready ??????????
- [todo] ?????????1) ???? burn ?/boot ???????2) ?????????????????????? `0x0102` / `0x5A5A` ???
- [done] ??????????????????? `plan.md`????????


## 2026-04-22 ??? heartbeat.ignore ???? Round
- [done] ?? `plan.md`?????????????`heartbeat.ignore 1` ???????????????????????????????
- [done] ??????? -> `COM38` ?? `heartbeat.ignore 1` -> ???? -> ?? `???? -> ????`??????????????? `result/csk3022_htt_clothes_airer/20260422_230200_heartbeat_ignore_reboot_check/`?
- [done] ?????`heartbeat.ignore 1` ???????? shell ??????????? `COM38` ?? `26.926s` ? `MCU is not ready!`?`COM36` ???? `0x0102` ??????? `0x5A5A`????? `0x0001` / `0x0009`?? `35.927s` ? `44.767s` ?? `????` / `????` ????? `Wakeup:` / `keyword:` / `MODE=1`??????? `heartbeat.ignore 1` ???????????? ready ????????
- [done] ??????????????????????????????/????????????? heartbeat ?????????
- [todo] ??????????????1) ????????/ready ?? ignore ???2) ???? `0x0102 -> 0x0020` ? `0x7F 5A5A -> 0x83 5A5A` ????????
## 2026-04-23 好太太 bench 恢复续调 Round
- [done] 再次读取 `plan.md`，确认当前最终目标仍是：先恢复基础唤醒/识别链路，再完成 3 项数值检验，最后重跑全量正式用例。
- [doing] 先从时间线回溯：重点复核最后一次可正常语音响应（约 `20260422_164545`）到首次稳定无响应（约 `20260422_200618`）之间的执行日志、串口日志和命令动作，定位是哪一段开始失效。
- [todo] 基于时间线差异继续尝试 bench 恢复：优先排查 ListenAI 音频端点/采集链路、算法状态、shell 可见诊断命令以及可能残留的非易失配置。
- [todo] 一旦基础唤醒恢复，立即按“实测真实值 -> 对比需求值”的口径重跑 `python tools/debug/run_htt_numeric_probe.py`，闭环 `唤醒超时` / `默认音量` / `总档位数`。
- [todo] 数值闭环后再重跑 `python tools/debug/run_htt_handshake_formal_suite.py`，更新最终结果与报告。
## 2026-04-23 好太太被动音量数值突破 Round
- [done] 继续按“恢复 bench -> 数值闭环 -> 全量复测”推进，并补查 `16:45` 后到 `20:06` 前的目录时间线；当前没有发现新的正式业务脚本把模组从“可唤醒”主动改坏，更像是 bench 音频输入链路在空档期后失效。
- [done] 追加恢复尝试：`factory.record.play`、目标 DUT 父级 USB Composite Device (`USB\VID_8765&PID_5678\7&1D315920&0&3`) disable/enable 全量重枚举；两条尝试后 `CTRL-LIGHT-001` 仍未恢复，说明单纯算法重启/父级重枚举还不足以把主动唤醒拉回。
- [done] 新发现：被动协议 `0x0041 / 0x0042` 可直接控制音量，且不依赖当前失效的 ASR 路径。
  - `0x006C` 恢复出厂后，日志稳定出现 `refresh config volume=2`、`mini player set vol : 58`，可作为默认位起点。
  - 向上探测证据：`result/csk3022_htt_clothes_airer/20260422_234251_passive_volume_up_boundary_probe_r2/`
    - 连续注入 `0x0041` 后运行音量序列实测为 `58 -> 79 -> 100 -> 100 ...`，出现明显上边界平台；
    - 日志最终刷新到 `refresh config volume=4`。
  - 向下探测证据：`result/csk3022_htt_clothes_airer/20260422_234139_passive_volume_down_boundary_probe/`
    - 连续注入 `0x0042` 后运行音量序列实测为 `58 -> 37 -> 10 -> 10 ...`，出现明显下边界平台；
    - 日志最终刷新到 `refresh config volume=0`。
- [done] 基于真实边界反推数值结论：
  - 下边界码值 `0`，上边界码值 `4`，共有 `5` 个有效档位（`0,1,2,3,4`）；
  - 恢复出厂默认码值为 `2`，位于 5 档中的第 `3` 档；
  - 当前可先把 `总档位数=5`、`默认音量=3档` 记为“已通过真实值比对需求值”的数值项。
- [doing] 继续集中恢复主动唤醒链路，用于补齐仍阻塞的 `唤醒超时` 数值项；现有最强线索仍是“PC->DUT 音频输入链路未真正进入设备识别通路”。
- [todo] 若主动唤醒仍无法恢复，需要把数值报告拆成：`默认音量/总档位数` 已闭环通过，`唤醒超时` 因 bench 输入链路阻塞暂未闭环；待恢复后再重跑完整 numeric probe 和 formal suite。
## 2026-04-23 好太太唤醒超时口径补充 Round
- [doing] 接收并同步用户新增口径：唤醒超时必须从两个维度验证，且两者结果要一致。
  - 维度 1：仅唤醒，不说命令，等待会话超时；
  - 维度 2：唤醒后说命令词，等命令词响应/播报结束，再等待会话超时；
  - 两者都以 `TIME_OUT` 与紧随其后的 `MODE=0` 为终点标记，必要时结合响应结束点计算 `响应结束 -> 超时`。
- [doing] 接收并同步用户新增线索：`heartbeat.ignore 1` 后，可尝试不走播音，直接通过协议串口按 MCU->模组被动协议格式给 CSK 发包，验证被动播报/被动功能链路是否可用。
- [todo] 先在当前 bench 上复现实机 shell `heartbeat.ignore 1`，再分别试：
  - 直接下发已知被动协议（如 `0x006C / 0x0041 / 0x0042 / 0x0069 / 0x0082`）
  - 若需要，再观察一次主动唤醒识别时 `COM36` 的主动协议格式，作为补充参考。
- [todo] 若协议直发可稳定驱动某些交互链路，再判断能否借此绕开当前 ASR 阻塞，先把 `唤醒超时` 里的“命令后等待超时”维度闭环，或至少补强阻塞归因。
## 2026-04-23 好太太串口占用与被动协议续跑 Round
- [done] 再次读取 `plan.md`，并复核当前阻塞主线：`默认音量`、`总档位数` 已经通过被动协议实测闭环，当前只剩 `唤醒超时` 仍因主动唤醒/识别链路异常而阻塞。
- [doing] 先处理上一轮遗留的 `COM38` 占用问题，释放日志串口后再重试 `heartbeat.ignore 1 + 协议直发` 探测。
- [todo] 复跑 `heartbeat.ignore 1` 后的被动协议注入（优先 `0x006C / 0x0041 / 0x0042 / 0x0069 / 0x0082`），补看在无握手仿真条件下是否仍可驱动被动播报/功能链路。
- [todo] 若被动协议链路恢复可用，继续评估是否能为“命令后等待超时”维度补充证据；若仍不能闭环，则保留 `唤醒超时` 为 bench 阻塞项并继续收敛根因。
- [done] 用户已手动释放 `COM38`，当前可恢复日志串口探测；本轮继续直接重试 `heartbeat.ignore 1 + 被动协议` 实验。
- [done] 在用户释放 `COM38` 后，已完成新一轮 `heartbeat.ignore 1 + 被动协议` 续跑：结果目录 `result/csk3022_htt_clothes_airer/20260423_093332_heartbeat_ignore_passive_proto_probe_r2/`。
- [done] 关键结论 1：`heartbeat.ignore 1` 后若不重启，直接注入 `0x006C / 0x0041 / 0x0042 / 0x0069 / 0x0082`，`COM38` 仅见 `MCU is not ready!`，`COM36` 无有效返回，说明命令后立即直发被动协议仍未放开业务链路。
- [done] 关键结论 2：`heartbeat.ignore 1` 后重启再试，`COM36` 仍只见模组持续发 `A5 FA 7F 5A 5A D2 FB` 心跳查询，注入的被动控制帧没有触发 `receive msg` / `play start` / `restore factory response`；随后在重启后再次输入 `heartbeat.ignore 1` 复测，现象不变，说明该命令不能替代启动 `ready` 握手门禁。
- [done] 关键结论 3：补做对照实验后已确认当前串口链路本身没有坏：
  - 仅补 `0x83 A5A5` 周期查询时，`COM36` 能稳定回 `0x7F A5A5`，说明协议口收发仍通；
  - 重新在启动阶段补齐 `0x0102 -> 0x0020` 与 `0x7F 5A5A -> 0x83 5A5A` 后，被动 `0x006C / 0x0041 / 0x0042` 立即恢复，`COM38` 可见 `receive msg`、`restore factory response`、`mini player set vol`。
- [done] 关键结论 4：错过启动窗口后，再晚发品牌应答 `0x0020` 并配合心跳应答/MCU 查询，也未能把本轮 plain boot 从 not ready 态救回，说明品牌应答大概率必须卡在启动窗口，或至少存在更早的 ready 锁存条件。
- [doing] 当前阻塞进一步收敛：不是“没 read 导致逻辑交互不了”，而是设备仍被 `MCU ready` 门禁卡住；`heartbeat.ignore 1` 在当前固件/环境下不足以放开被动业务链路。
- [todo] 若继续推进数值闭环，可复用“启动握手仿真 + 被动协议”完成仍可做的被动项；但 `唤醒超时` 仍需恢复主动唤醒/识别链路，当前 bench 主阻塞仍是主动语音输入链路未恢复。
## 2026-04-23 好太太双维度超时闭环 Round
- [done] 在握手仿真夹具口径下，主动语音链路已恢复：`CTRL-LIGHT-001` 冒烟复跑目录 `result/csk3022_htt_clothes_airer/20260423_094344_htt_handshake_formal_suite_after_heartbeat_debug/`，结果 PASS，可再次抓到 `Wakeup:` / `keyword:` / `0x0001 / 0x0009`。
- [done] 已完成用户要求的双维度唤醒超时实测：`result/csk3022_htt_clothes_airer/20260423_095403_htt_timeout_dual_probe_r2/`，报告 `deliverables/csk3022_htt_clothes_airer/reports/20260423_095403_htt_timeout_dual_probe_r2/summary.md`。
  - 维度 1（仅唤醒后静默）：`0x0001=39.484s` -> `TIME_OUT/MODE=0=64.362s`，实测 `24.878s`；
  - 维度 2（唤醒后说“调小音量”）：`keyword/send msg=49.110s` -> `TIME_OUT/MODE=0=74.109s`，实测 `24.999s`；
  - 两维差值 `0.121s`，满足“两个维度一致”的要求。
- [done] 到当前为止，3 个数值项已全部按“先测真实值，再对比需求值”的口径闭环：
  - `唤醒超时 = 25s` PASS
  - `默认音量 = 3 档` PASS
  - `总档位数 = 5 档` PASS
- [doing] 进入下一步：基于当前已恢复的握手仿真口径，重跑全量正式用例，更新最终 PASS/FAIL/BLOCKED 分布与剩余问题。
## 2026-04-23 合成音频中文命名 Round
- [done] 再次读取 `plan.md`，接收用户建议：合成音频文件名应尽量使用中文可读名，方便直接按文件名找对应调试音频。
- [done] 已修改公共入口 `tools/audio/fan_validation_helper.py`：
  - 新增 `sanitize_filename_fragment()`，允许中文文件名；
  - 新增 `build_tts_filename()`，默认优先用实际播报文本 `text` 生成缓存文件名，而不是只依赖英文 `label`；
  - 新增 `relocate_cached_file()`，命中旧缓存时会优先迁移到新的中文可读文件名并回写 manifest。
- [done] 已做实测验证：
  - `python tools/audio/fan_validation_helper.py tts-cache --text 小好小好 --label timeout_case_1` -> `audio_cache/tts/小好小好_3fcec41788.wav`
  - `python tools/audio/fan_validation_helper.py tts-cache --text 调小音量 --label timeout_case_cmd` -> `audio_cache/tts/调小音量_cab38074b2.wav`
- [doing] 后续继续跑好太太正式/调试链路时，新生成或命中的 TTS 缓存都会优先落成中文可读文件名。
## 2026-04-23 全量正式复跑确认 Round
- [done] 再次读取 `plan.md`，确认用户当前问题是：基于最新恢复后的状态，判断“是否全部功能验证已通”，并明确还有哪些需求功能尚未验证到。
- [doing] 当前最新全量正式套件仍是旧结果，尚不能直接代表“双维度超时闭环 + 中文音频命名修正”后的当前状态；本轮补跑一遍全量正式套件后再回结论。
- [todo] 复核最新全量正式复跑报告与需求追踪矩阵，输出：1) 已通过功能；2) 仍失败功能；3) 需求上未覆盖/未闭环项；4) 当前口径限制（握手仿真 vs 真实 MCU）。
## 2026-04-23 播报ID补充要求 Round
- [done] 再次读取 `plan.md`，接收用户新增要求：所有被动播报协议和主动发送响应，不仅要验证“有没有播报/播报次数”，还要同步验证对应 `play id`。
- [done] 已复核当前口径：
  - `0x0082 / 0x0069 / 0x006C` 在现有好太太 v4 套件里主要验证了接收日志、状态切换和 `play id` 次数；
  - 还没有把“期望 `play id` 值 = ?”写成明确断言；
  - 主动语音命令当前主要验证 `0x0001 -> 业务协议` 是否下发，也还没有建立“命令词 -> 响应播报 `play id`”的一一映射断言。
- [doing] 下一步需补两类资产：
  - 被动播报协议：补齐每个协议的期望 `play id` 断言；
  - 主动语音响应：整理“命令词 -> 期望响应 `play id`”矩阵，再把 `play id` 校验并入正式套件。
- [todo] 在补齐 `play id` 口径前，不能把“所有被动播报协议和主动发送响应都已验证完成”作为最终结论。
## 2026-04-23 播报ID矩阵与断言补齐 Round
- [done] 再次读取 `plan.md`，接着上一轮“播报ID补充要求”继续推进，先补需求矩阵再补 runner 断言。
- [done] 已重新通读 `项目需求/好太太晾衣机/好太太晾衣机需求迭代.md`、`当前有效需求清单_20260422.md`，并重新抽取 Excel `电控协议/协议播报` 结构化内容，形成“主动命令 -> 被动响应 -> play id 覆盖状态”的最新口径。
- [done] 已新增矩阵文档：`deliverables/csk3022_htt_clothes_airer/plan/20260423_功能点_协议_播报ID矩阵_v1.md`。
  - 文档按功能点列出了主动协议、固定/约定的 MCU 被动响应、已知 `play id` 证据以及当前覆盖状态；
  - 当前明确已知的值级证据：`0x006C -> 103`、`0x0082 -> 无新增播报`、`0x0069 -> 100`、`0x0012 -> 65`、受限态唤醒 `77`、语音关闭提示 `123`、超时休眠 `122`。
- [done] 已修改 `tools/debug/run_htt_handshake_formal_suite.py`：
  - 新增 `required_play_ids` / `forbidden_play_ids` 断言能力；
  - 新增 `extra_respond_rules` 预留能力，后续可用于“主动命令 -> MCU 自动回包”的完整闭环；
  - 已把当前已掌握证据的被动协议升级为精确 `play id` 断言：`PASSIVE-RESET-001`、`PASSIVE-REPORT-OFF-001`、`PASSIVE-REPORT-ON-001`、`PASSIVE-VOICE-ON-001`、`PASSIVE-VOICE-OFF-001`。
- [done] 已执行 `python -m py_compile .\tools\debug\run_htt_handshake_formal_suite.py`，脚本语法通过。
- [done] 已对历史良好结果做离线回放校验：`result/csk3022_htt_clothes_airer/20260422_162226_htt_handshake_formal_suite_full_v4_r2/steps/`
  - `passive-reset-001` 命中 `[103]`
  - `passive-report-off-001` 命中 `[103]`
  - `passive-report-on-001` 命中 `[103, 100]`
  - `passive-voice-on-001` 命中 `[103, 65, 77, 123, 123]`，其中被动协议本体链路满足 `[103, 65]`
  - `passive-voice-off-001` 命中 `[103, 65, 77, 123]`，其中被动协议本体链路满足 `[103, 65]`
  说明本次新增的 `play id` 断言逻辑与既有有效证据一致。
- [done] 已尝试在当前 bench 上实机复跑被动协议子集：`result/csk3022_htt_clothes_airer/20260423_104020_htt_handshake_formal_suite_playid_patch_check/`。
- [doing] 当前 bench 在本轮复跑时又掉回 `MCU is not ready!`：
  - 5 条子集全部 FAIL；
  - `COM38` 只出现 `play id : 7` 与 `MCU is not ready!`，没有收到预期 `COM36` 握手/注入回包；
  - 因此这轮 FAIL 不能判成新断言逻辑错误，更像是当前台架/串口握手状态再次异常。
- [todo] 待 bench 再次恢复到握手仿真 ready 口径后，优先重跑本轮被动协议子集，确认新的精确 `play id` 断言能在当前实机环境稳定通过。
- [todo] 基于 `extra_respond_rules`，继续把“主动命令 -> MCU 自动回包 -> 被动播报 `play id`”的完整闭环补进正式套件，覆盖用户要求的 active/passive 双向验证。
- [todo] 在当前矩阵基础上，继续补全剩余固定被动播报协议的 `play id` sweep，直至可以回答“所有被动播报协议和主动发送响应是否全部验证完成”。
## 2026-04-23 协议串口杜邦线恢复与播报ID复测 Round
- [done] 再次读取 `plan.md`，同步用户最新现场信息：协议串口（`COM36`）杜邦线此前松动，现已恢复。
- [done] 已补做启动观察确认 `COM36` 收发恢复：证据目录 `result/csk3022_htt_clothes_airer/20260423_boot_watch_after_dupont_fix/`，其中 `com36_frames.txt` 已重新抓到 `A5 FA 7F 01 02 21 FB` 与 `A5 FA 7F 5A 5A D2 FB`，说明协议口 TX 不再是 0 字节。
- [done] 已在恢复后重跑被动播报 `play id` 子集：`result/csk3022_htt_clothes_airer/20260423_105428_htt_handshake_formal_suite_playid_patch_check_after_dupont_fix/`，报告 `deliverables/csk3022_htt_clothes_airer/reports/20260423_105428_htt_handshake_formal_suite_playid_patch_check_after_dupont_fix/summary.md`。
- [done] 当前复测结果更新为：`PASSIVE-RESET-001`、`PASSIVE-REPORT-OFF-001`、`PASSIVE-REPORT-ON-001` 已 PASS，且精确 `play id` 分别命中 `103`、`103`、`103,100`。
- [done] `PASSIVE-VOICE-ON-001`、`PASSIVE-VOICE-OFF-001` 当前仍 FAIL，但失败点已收敛：被动 `0x0012` 自身及其 `play id=65` 已正确命中，未通过的是后续主动语音恢复/阻断链路，本轮 `COM36` 未再抓到预期 `0x0001 / 0x0017 / 0x0009`。
- [doing] 下一步继续针对 `0x0012` 语音状态机做单用例复现与时序排查，并补齐“主动命令 -> MCU 回包 -> 播报ID”完整闭环。
## 2026-04-23 主动语音链路回归阻塞诊断 Round
- [done] 已在 `result/csk3022_htt_clothes_airer/20260423_110207_htt_handshake_formal_suite_voice0012_debug_after_dupont_restore/` 复跑 `CTRL-LIGHT-001`、`PASSIVE-VOICE-ON-001`、`PASSIVE-VOICE-OFF-001`；结果 3 条全 FAIL，且失败形态一致：`COM36` 只剩握手/心跳帧，不再出现任何 `0x0001 / 0x0017 / 0x0009`。
- [done] 已排除“仅 0x0012 状态机异常”这一条线：连基准主动用例 `CTRL-LIGHT-001` 也在当前环境下失活，说明当前问题已扩大为整条主动唤醒/识别链路阻塞，而不是 `play id` 断言或单条语音状态机逻辑错误。
- [done] 已补做渲染端点排查：`result/csk3022_htt_clothes_airer/20260423_111117_render_key_ctrl_light_probe_r3/summary.json` 显示 3 个可见 ListenAI render key 逐个试播后，均未再触发 `Wakeup:` / `keyword:` / `0x0001 / 0x0009`，说明不是单一 render key 选错。
- [done] 已补做 Windows 端点电平验证：当前目标设备 `扬声器 (4- ListenAI Audio)` 播放时仍有峰值（约 `0.5937`），说明 PC 端播放调用本身仍在向 render endpoint 送数；阻塞点更接近 DUT 内部的主动识别输入链路，而非协议口或播放脚本直接失效。
- [done] 已尝试软恢复：
  - 先做 `PASSIVE-RESET-001 -> CTRL-LIGHT-001` 预置恢复后再跑主动链路，未恢复；
  - 重启目标 `ListenAI Audio` media 设备 `USB\VID_8765&PID_5678&MI_00\8&804B35B&1&0000` 后复跑 `CTRL-LIGHT-001`，仍未恢复。
- [done] 当前最新可用的“主动全量正式闭环”证据仍是 `deliverables/csk3022_htt_clothes_airer/reports/20260423_100209_htt_handshake_formal_suite_full_rerun_after_timeout_close/summary.md`：22 条中 `PASS 21 / FAIL 1`，唯一剩余真实 FAIL 为 `PASSIVE-VOICE-ON-001`（被动 0x0012 关语音后再次打开仍未恢复后续业务命令）。
- [doing] 后续交付口径需拆开：
  - 10:02 前的主动全链路、3 项数值项与大部分功能链路已有正式 PASS 证据；
  - 10:54 后新增的精确 `play id` 子集已补到 3 PASS；
  - 11:02 后主动链路再次 bench 阻塞，导致“继续扩充 active+passive+play id 全覆盖”暂时无法在当前台架上收敛到最终全 PASS。
## 2026-04-23 详细测试方案输出 Round
- [done] 已基于当前有效需求、需求追踪矩阵、功能/协议/play id 矩阵和最新实测结果，输出详细方案文档：`deliverables/csk3022_htt_clothes_airer/plan/20260423_完整需求测试方案与当前覆盖状态_v1.md`。
- [done] 文档已按“需求点 -> 需求解析 -> 方法ID -> 功能断言 -> 数值断言 -> play id 断言 -> 当前状态”的一一对应口径整理，并覆盖：
  - 握手/会话/数值/全局状态
  - 电机/晾杆/升降
  - 灯光/模式/场景
  - 功能控制/配网/位置设置
  - 音量/播报/语音控制
  - 被动固定播报 `play id` 与已删除非范围项
- [doing] 当前待继续推进的只剩：在主动语音链路 bench 恢复后，补齐未完成的 active+passive+play id 全覆盖与掉电保存/异常项执行证据。

## 2026-04-23 主动语音链路音频路径深挖 Round
- [done] 再次读取 `plan.md`，并同步当前事实：`20260423_100209_htt_handshake_formal_suite_full_rerun_after_timeout_close` 仍是最近一次主动全链路可用的正式基线，结论为 `PASS 21 / FAIL 1`，唯一真实 FAIL 仍是 `PASSIVE-VOICE-ON-001`。
- [done] 已继续补做主动链路恢复实验，但到 `11:02` 后整条主动唤醒/识别链路再次回归阻塞；不仅 `PASSIVE-VOICE-ON/OFF-001` 失败，连 `CTRL-LIGHT-001` 也不再出现 `Wakeup:` / `keyword:` / `0x0001 / 0x0009`。
- [done] 已排除“仅 render key 选错”：
  - 证据 `result/csk3022_htt_clothes_airer/20260423_111117_render_key_ctrl_light_probe_r3/summary.json`
  - 3 个可见 ListenAI render key 逐个试播均未恢复主动识别。
- [done] 已确认 Windows 端播放调用本身仍在向目标端点送数：
  - 端点电平探针显示 `扬声器 (4- ListenAI Audio)` 播放时仍有明显峰值；
  - 说明阻塞点更像是 DUT 侧主动识别输入通路/声道映射，而不是 `listenai_play` 命令完全没播放。
- [done] 已补做捕获端声道分布实验：
  - 采集端索引 `27` = `麦克风 (4- ListenAI Audio)`，`8ch @16000`
  - 当前 `listenai_play` 路径下，采集端 `ch8` 信号最强，`ch1~7` 基本接近静音；
  - 改走 PyAudio 直接输出到渲染设备索引 `7` / `22` 时，采集端 `ch1` 明显更强，但 DUT 仍未被唤醒。
- [done] 已尝试的恢复动作仍未把主动链路拉回：
  - `PASSIVE-RESET-001 -> CTRL-LIGHT-001` 预置恢复
  - 重启目标 media device `USB\\VID_8765&PID_5678&MI_00\\8&804B35B&1&0000`
  - 重启父级 composite device `USB\\VID_8765&PID_5678\\7&1D315920&0&3`
  - 长等待 / no-periodic / periodic8 / ASCII 路径 / 被动拉满音量后再播音
  - PyAudio 直推不同 render 设备索引
- [doing] 当前新的最短执行路径：
  1. 先重跑一轮最小主动冒烟（`CTRL-LIGHT-001`）确认此刻 bench 是否仍阻塞；
  2. 若仍阻塞，则继续把“播放后 DUT capture 端实际进到哪个声道”的探针脚本固化，形成可复现诊断资产；
  3. 一旦主动链路恢复，立即复跑 `CTRL-LIGHT-001`、`PASSIVE-VOICE-OFF-001`、`PASSIVE-VOICE-ON-001`，再决定是否继续全量 sweep。
- [todo] 若当前 bench 仍无法恢复主动识别，则最终结论必须拆分为：
  - 数值项 3/3 已按真实值闭环通过；
  - 当前剩余真实功能 FAIL 仍以 `PASSIVE-VOICE-ON-001` 为主；
  - 但 `11:02` 后新增的主动链路 bench 阻塞会暂时影响继续扩展 active+passive+play id 的全覆盖复测。

## 2026-04-23 音频路由探针固化与新证据 Round
- [done] 已先按当前最短路径重跑最小主动冒烟：`deliverables/csk3022_htt_clothes_airer/reports/20260423_130143_htt_handshake_formal_suite_current_smoke_resume/summary.md`，`CTRL-LIGHT-001` 仍 FAIL；现象未变，`COM36` 只有 `0x0102 / 0x5A5A / 0xA5A5` 握手心跳，没有 `0x0001 / 0x0009`。
- [done] 已新增可复现探针脚本 `tools/debug/run_htt_pyaudio_route_probe.py`：
  - 固化了“握手仿真 + 指定 PyAudio 输出设备索引 + 可选 capture 端声道峰值统计”的单次探测流程；
  - 已执行 `python -m py_compile .\\tools\\debug\\run_htt_pyaudio_route_probe.py`，语法通过。
- [done] 已用新脚本复测多条音频路由：
  - `result/csk3022_htt_clothes_airer/20260423_130737_htt_pyaudio_route_probe_wasapi22_ctrl_light/`
  - `result/csk3022_htt_clothes_airer/20260423_130908_htt_pyaudio_route_probe_mme7_ctrl_light/`
  - `result/csk3022_htt_clothes_airer/20260423_131118_htt_pyaudio_route_probe_wasapi25_ctrl_light/`
  - `result/csk3022_htt_clothes_airer/20260423_131632_htt_pyaudio_route_probe_wasapi22_mono_ctrl_light/`
  - `result/csk3022_htt_clothes_airer/20260423_131822_htt_pyaudio_route_probe_mme7_mono_ctrl_light/`
  - `result/csk3022_htt_clothes_airer/20260423_132535_htt_pyaudio_route_probe_wasapi22_mono_repeat3_ctrl_light/`
- [done] 这些新探针的共同结论：
  - 无论 WASAPI `22`、MME `7`，还是改投 `3- ListenAI Audio` 的 WASAPI `25`，都没有重新打通 `Wakeup:` / `keyword:`；
  - `capture 27` 统计里 `ch8` 始终最强（约 `27501`），说明数字回采路径一直存在；
  - 投到 `4- ListenAI Audio` 时，`ch1` 可被拉高，但目前最高也只到约 `9967~10312`（单声道时比双声道更高），仍未触发唤醒；
  - 把唤醒词重复 3 次后，`ch1` 峰值没有继续增长，也仍然没有 `0x0001`。
- [done] 已补测声道/接口边界：
  - `WDM-KS` 输出索引 `47` 在当前 PortAudio/PyAudio 环境下打开失败，目录 `result/csk3022_htt_clothes_airer/20260423_130537_htt_pyaudio_route_probe_wdmks47_ctrl_light/` 与 `..._wdmks47_mono_ctrl_light/` 可作为“接口不可直接用”的证据；
  - 对 `WASAPI 22` 做 `left/right` 声道分离后，确认 `ch1` 主要来自 left path，right-only 时 `ch1` 基本归零，但 `ch8` 仍强且仍无唤醒：
    - `result/csk3022_htt_clothes_airer/20260423_131331_htt_pyaudio_route_probe_wasapi22_left_ctrl_light/`
    - `result/csk3022_htt_clothes_airer/20260423_131459_htt_pyaudio_route_probe_wasapi22_right_ctrl_light/`
- [done] 已排除两项常见外部原因：
  - 当前目标 render endpoint `扬声器 (4- ListenAI Audio)` 的 Windows 端点音量已是 `1.0`、未静音；
  - 仓库内暂未找到除 `audio_cache/tts/` 之外的现成本地“唤醒词/命令词录音资产”，当前继续复现只能依赖 TTS 缓存或后续自制录音。
- [done] 已继续扩展音频样本尝试：
  - 全仓搜索后发现历史增强样本 `result/csk3022_htt_clothes_airer/audio_boost_test_assets/wake_boost6dB.wav` 与 `.../open_light_boost6dB.wav`；
  - 用新脚本支持 `--audio-file` 后，已执行 `result/csk3022_htt_clothes_airer/20260423_133602_htt_pyaudio_route_probe_wasapi22_boost6db_ctrl_light/`，把 `capture 27` 的 `ch1` 峰值抬到约 `12899`，但仍没有 `Wakeup:` / `0x0001`；
  - 另尝试 `slow_huihui_wake` 旧样本配增强命令词，目录 `result/csk3022_htt_clothes_airer/20260423_133759_htt_pyaudio_route_probe_wasapi22_slowwake_boostcmd_ctrl_light/`，仍未恢复主动识别。
- [done] 已尝试在线生成更自然的 Edge TTS 音频，但当前环境访问 `edge-tts` 服务返回 `403/timeout`，未能形成可用替代样本；证据目录 `result/csk3022_htt_clothes_airer/20260423_edge_tts_assets/`。
- [done] 已复核 shell 诊断命令：
  - `help` / `help factory` 已重新抓到，确认可用诊断仍主要是 `factory connect/version/gpio/uart/mic/adc`、`adconf`、`classd` 等；
  - `factory mic` 在 idle 和 `factory connect` 后重试都快速返回 `mic test failed` / `outRet:17`，目前还不能直接拿它证明 ASR 输入是否正常。
- [doing] 当前更收敛的判断：
  - 不像是“完全没音频送到 DUT”，而更像是“送到了错误/非 ASR 主通道，或 ASR 主通道电平仍不够触发”；
  - 下一步优先考虑两条线：1) 继续找可替代 TTS 的真实录音/更贴近历史成功样本的音频；2) 评估是否需要尝试更激进的 bench 恢复动作（如重新烧录/更换音频接口策略）。

## 2026-04-23 音频线恢复复测 Round
- [done] 再次读取 `plan.md`，同步用户最新现场信息：此前不是算法/协议配置问题，而是音频线未插紧；用户已于当前轮明确表示音频线现已恢复。
- [done] 已按最短路径重跑最小主动冒烟 `CTRL-LIGHT-001`：
  - 报告 `deliverables/csk3022_htt_clothes_airer/reports/20260423_134345_htt_handshake_formal_suite_audio_line_restored_smoke/summary.md`
  - 结果 PASS，`COM38` 重新抓到 `Wakeup:` / `keyword:`，`COM36` 重新出现 `0x0001 / 0x0009`；
  - 说明“音频线未插紧”确实就是本轮主动链路阻塞的直接现场根因。
- [done] 已立刻续跑关键阻塞子集：
  - 报告 `deliverables/csk3022_htt_clothes_airer/reports/20260423_134527_htt_handshake_formal_suite_audio_line_restored_voice_recheck/summary.md`
  - 结果 `PASSIVE-VOICE-OFF-001` PASS、`PASSIVE-VOICE-ON-001` FAIL；
  - 当前再次确认：被动 `0x0012` 关语音后，“语音功能打开”能下发 `0x0017`，但之后再次说“打开照明”仍未恢复 `0x0009`，所以真实剩余 FAIL 仍是 `PASSIVE-VOICE-ON-001`。
- [done] 已在主动链路恢复后重跑全量 formal suite：
  - 报告 `deliverables/csk3022_htt_clothes_airer/reports/20260423_134907_htt_handshake_formal_suite_audio_line_restored_full_rerun/summary.md`
  - 当前最新总结果重新回到稳定基线：`22` 条里 `PASS 21 / FAIL 1 / BLOCKED 0`
  - 唯一 FAIL 仍是 `PASSIVE-VOICE-ON-001`，其余 active / passive / 已补精确 `play id` 的当前套件项全部 PASS。
- [doing] 当前已确认台架恢复成功，后续重点不再是 bench 恢复，而是：
  1. 以 `20260423_134907_...full_rerun` 作为当前最新正式基线；
  2. 继续补需求矩阵里仍未执行的掉电保存 / 异常项 / 其余 active+passive+play id 覆盖；
  3. 最终刷新“完整需求测试方案与当前覆盖状态”文档中的最新执行状态。

## 2026-04-23 22条覆盖范围答复 Round
- [done] 再次读取 `plan.md`，并基于最新正式基线 `deliverables/csk3022_htt_clothes_airer/reports/20260423_134907_htt_handshake_formal_suite_audio_line_restored_full_rerun/summary.md` 复核 22 条 case 的实际覆盖范围。
- [done] 当前结论已明确：
  - 这 22 条是“当前握手仿真正式套件”的覆盖范围，不等于需求文档的全部功能点；
  - 22 条主要覆盖：握手 ready、唤醒/未唤醒阻断、会话超时功能、照明/阅读/配网、音量/播报/语音开关，以及被动 `0x006C/0x0082/0x0069/0x0012` 的关键链路；
  - 最新结果仍是 `PASS 21 / FAIL 1 / BLOCKED 0`，唯一 FAIL 仍是 `PASSIVE-VOICE-ON-001`。
- [done] 已同步“是否覆盖全功能点”的当前口径：
  - 还没有覆盖全功能点；
  - 当前未全量覆盖的主要是：电机/升降/杆控制大类、亮度/色温/夜灯/场景模式大类、消毒/感应/位置设置大类、掉电保存类、异常协议 `0x008C` 类，以及剩余 active+passive+play id 的逐条值级 sweep。


## 2026-04-23 ?? skill ???????? v2 Round
- [done] ???? `plan.md`??????????????????????? + ?????????? skill???????????????????????????
- [done] ?????????????????????????/???????????? `mars-moon`?
  - `mars-moon/references/htt_min_validation_and_pitfalls.md`
  - `mars-moon/SKILL.md`
  - `mars-moon/references/workflow.md`
- [done] ?? `references/??????????.md` ?????????????????????`deliverables/csk3022_htt_clothes_airer/plan/20260423_???????????????_v2.md`?
- [doing] ?? v2 ??????????? -> ???? -> play id???? sweep????????????????????
- [todo] ??? sweep ?????????????????play id ????????????


## 2026-04-23 ?????? sweep ?? Round
- [done] ???? `plan.md`????????????????? `deliverables/csk3022_htt_clothes_airer/reports/20260423_134907_htt_handshake_formal_suite_audio_line_restored_full_rerun/summary.md` ????
- [doing] ??? `tools/debug/run_htt_active_passive_playid_sweep.py` ????????/???????????????? smoke ??????????????? `play id` sweep?
- [todo] ? smoke ?????????????????? sweep??? active -> passive -> play id ?????
- [todo] sweep ?????? `deliverables/csk3022_htt_clothes_airer/plan/` ?????????????? `plan.md` ???????????


## 2026-04-23 ?????? sweep ?? Round??????
- [done] ??? `tools/debug/run_htt_active_passive_playid_sweep.py` ??????
  - `?? -> ????`
  - `?? -> ????`
  - `?? -> ????`
  - `?? -> ????`
  - `?? -> ????`
  - `?? -> ??????`
  - `???? -> ??????`
- [done] ??? `tools/serial/fan_proto_handshake_probe.py`?????????????? `0x81` ????? `0x83 5A5A` ???????? `check_sum error`?
- [done] ??????? full sweep ??????
  - `deliverables/csk3022_htt_clothes_airer/reports/20260423_170059_htt_active_passive_playid_sweep_full_r2_final/summary.md`
  - ???`40` ?? `PASS 38 / FAIL 2 / BLOCKED 0`
- [done] ????????? FAIL ? focused ??????
  - `FULL-BRIGHT-UP-001` -> `deliverables/csk3022_htt_clothes_airer/reports/20260423_174403_htt_active_passive_playid_sweep_brightness_focus_r1/summary.md`?`play id=41`
  - `FULL-COLD-UP-001`?`FULL-WARM-UP-001` -> `deliverables/csk3022_htt_clothes_airer/reports/20260423_164551_htt_active_passive_playid_sweep_coldwarm_retry_r2/summary.md`?`play id=45/46`
  - `FULL-COLD-MAX-001` -> `deliverables/csk3022_htt_clothes_airer/reports/20260423_165501_htt_active_passive_playid_sweep_checksumfix_r2/summary.md`?`play id=47`
- [done] ?????? active->passive->play id ?????????
  - ??????????????? `play id` ????
  - `FULL-BRIGHT-DOWN-001` ?? `full_r1` ??? PASS ??? `play id=42`???? bench focused retry ????????????? PASS??????????
  - ????????? FAIL ??? `PASSIVE-VOICE-ON-001`?
- [done] ????????
  - `deliverables/csk3022_htt_clothes_airer/plan/20260423_???_??_??ID??_v2.md`
  - `deliverables/csk3022_htt_clothes_airer/plan/20260423_???????????????_v3.md`
- [todo] ??????
  1. ???? `FULL-BRIGHT-DOWN-001` ??????????
  2. ??????????? / ???? / ??????
  3. ?????? `0x008C`?
  4. ??????? / ??????????????????


## 2026-04-23 ???? 1/2/3/4 Round
- [done] ???? `plan.md`?????????????????? / PASS / FAIL????? 1) `FULL-BRIGHT-DOWN-001` ???2) ???????3) `0x008C`?4) `PASSIVE-VOICE-ON-001`?
- [doing] ?????????? / full sweep / focused ????????? PASS/FAIL ?????????????
- [todo] ?????? `FULL-BRIGHT-DOWN-001` ???????????????? bench ???? PASS ???
- [todo] ??????????? / ???? / ????????????????????????????????????
- [todo] ?????? `0x008C`?????????????
- [todo] ???? `PASSIVE-VOICE-ON-001`????? bench ??????? FAIL ??????



## 2026-04-23 Continue Round
- [doing] Recount executed cases / PASS / FAIL / BLOCKED from the latest HTT formal+sweep evidence and continue steps 1/2/3/4.
- [todo] Re-run `FULL-BRIGHT-DOWN-001` until we know whether the remaining issue is firmware logic or ASR/bench flakiness.
- [todo] Re-read HTT requirement docs and execute persistence checks for volume / report mode / voice switch, using measured post-reboot actual values before comparing with requirements.
- [todo] Verify passive protocol `0x008C` behavior and confirm whether it should produce no play broadcast / no play id.
- [todo] Re-run `PASSIVE-VOICE-ON-001` after the above checks and refresh the requirement coverage summary.


## 2026-04-23 Continue Round Results
- [done] Bright-down phrase probe finished: `result/csk3022_htt_clothes_airer/20260423_185149_htt_brightdown_phrase_probe/`; `????` got `1/3 PASS`, `???` got `0/2 PASS`, so `FULL-BRIGHT-DOWN-001` remains flaky and the sweep phrase was patched back to `????`.
- [done] Follow-up checks finished: `result/csk3022_htt_clothes_airer/20260423_192040_htt_followup_checks_r1/` and `deliverables/csk3022_htt_clothes_airer/reports/20260423_192040_htt_followup_checks_r1/summary.md`.
- [done] New measured persistence results:
  - volume persist PASS: passive `0x0043` changed actual config `volume 2 -> 4`, reboot kept `4`
  - report-mode persist PASS: active report-off changed `play_mode 0 -> 1`, reboot kept `1`
  - voice persist PASS: passive `0x0012` changed `voice 1 -> 0`, reboot kept `0`, and post-boot voice-off functional block also PASS
- [done] New failure results:
  - passive `0x008C` FAIL: after receive `A5 FA 81 00 8C AC FB`, DUT still played extra `play id 127` instead of no-broadcast
  - `PASSIVE-VOICE-ON-001` recheck FAIL 2/2: still reaches `0x0017` and wake, but does not recover final `0x0009`
- [done] Added reusable helper script `tools/debug/run_htt_followup_checks.py` for persistence / `0x008C` / passive-voice-on follow-up reruns.
- [todo] Refresh the requirement coverage/report docs with the new persistence and `0x008C` conclusions, then continue the remaining uncovered full-function matrix.


## 2026-04-23 Final Converge Round
- [doing] Enumerate current effective but still-unproven functions after formal + full sweep + persistence/0x008C follow-up.
- [todo] Run an active-only suite for the remaining current-effective commands that have no fixed passive reply definition, so every valid command at least closes to wakeup -> recognition -> active protocol.
- [todo] Refresh the requirement coverage markdown with the new active-only results plus the latest persistence / 0x008C / passive-voice conclusions.


## 2026-04-23 Active-only???? Round
- [done] ?? `plan.md`???????????follow-up ???active-only ???????/?????
- [done] ?????????
  - formal ?? `22` ?? `PASS 21 / FAIL 1 / BLOCKED 0`
  - full sweep `40` ?? `PASS 38 / FAIL 2 / BLOCKED 0`
  - persistence follow-up ??????/??/?????? PASS?`0x008C` FAIL?`PASSIVE-VOICE-ON-001` FAIL
  - active-only ?? `21` ???????????????????
- [doing] ???? Excel ? active-only ?????????? 21 ??????????????????????????????
- [todo] ???????????????????/???/????/??/????/?????
- [todo] ??????????? active-only ????????????????????????????????????????/??????????
- [todo] ???????PASS / FAIL / flaky / ????????? `deliverables/csk3022_htt_clothes_airer/plan/` ?????????????


## 2026-04-23 Active-only???? Round Results
- [done] ?? `tools/debug/run_htt_active_only_remaining.py` ?????
  - ?? case ?? baseline reset??????? `voice=0`
  - ??? UTF-8 ??????????? TTS ??? FAIL
- [done] ?? 6 ? representative probe?`result/csk3022_htt_clothes_airer/20260423_203000_htt_active_only_remaining_r1_probe6/`?6/6 ? FAIL??????? runner ?????
- [done] ????????? `tools/debug/run_htt_active_only_phrase_probe.py`?????? alias probe?
  - `deliverables/csk3022_htt_clothes_airer/reports/20260423_204338_htt_active_only_phrase_probe_r1/summary.md`
  - `29` phrase cases = `PASS 0 / FAIL 29`
  - `10` alias groups = `0` group hit
  - ???????? group ?????????????
- [done] ??????? + ?? baseline ?? active-only ?? clean ???
  - `deliverables/csk3022_htt_clothes_airer/reports/20260423_210937_htt_active_only_remaining_r1_clean_utf8_full/summary.md`
  - `21` cases = `PASS 0 / FAIL 21 / BLOCKED 0`
  - ?????????? `0x0001`??????????????
- [done] ???????????
  - `deliverables/csk3022_htt_clothes_airer/plan/20260423_???????????????_v2.md`
  - ?? persistence PASS?`0x008C` FAIL?active-only 21 ? FAIL ??? v1 ???????
- [done] ???? FAIL ????
  - `PASSIVE-VOICE-ON-001`
  - ?? `0x008C`
  - active-only ?????? `21` ?
- [todo] ???????????????????????????????????? fixed-passive `play id sweep` ? `77/123/10s` ?????


## 2026-04-23 关闭语音受限窗口与播报ID收敛 Round
- [done] 再次读取 `plan.md`，复核当前最后两个值级空缺：`关闭语音受限窗口=10s` 与受限态 `play id 77 / 123`。
- [done] 新增专项脚本 `tools/debug/run_htt_voice_restricted_probe.py`，用于：
  - 被动 `0x0012` 关闭语音后测量“受限唤醒 -> TIME_OUT / MODE=0”的真实时长；
  - 同时验证受限态唤醒提示 `77` 与普通命令阻断提示 `123`。
- [done] 首轮专项探针 `20260423_221858_htt_voice_restricted_probe_r1` 暴露方法问题：
  - 等待窗口取值不合理，导致 `123` 未稳定命中；
  - 该轮结果不作为最终口径，仅保留为中间调参证据。
- [done] 复跑修正后的专项探针：
  - `deliverables/csk3022_htt_clothes_airer/reports/20260423_222404_htt_voice_restricted_probe_r1/summary.md`
  - `result/csk3022_htt_clothes_airer/20260423_222404_htt_voice_restricted_probe_r1/`
- [done] 最终新增结论：
  - `play id 77` PASS：关闭语音后再次唤醒，受限态提示为 `77`
  - `play id 123` PASS：受限态下说普通命令，提示为 `123`，且无 `0x0009`
  - `关闭语音受限窗口=10s` FAIL：实测 `受限唤醒 -> TIME_OUT / MODE=0 = 25.881s`，`受限响应结束 -> TIME_OUT / MODE=0 = 25.185s`
- [done] 刷新最终文档：
  - `deliverables/csk3022_htt_clothes_airer/plan/20260423_完整需求测试方案与当前覆盖状态_v4.md`
  - `deliverables/csk3022_htt_clothes_airer/plan/20260423_功能点_协议_播报ID矩阵_v3.md`
- [done] 当前稳定 FAIL 总数已从 `23` 项更新为 `24` 项：
  - `G-07` 关闭语音受限窗口 `10s`
  - `PASSIVE-VOICE-ON-001`
  - `G-08 / 0x008C`
  - active-only 当前有效功能 `21` 项
- [doing] 准备对外输出最终收敛结果，明确：
  - 哪些需求点已 PASS
  - 哪些需求点稳定 FAIL
  - 哪些仅因需求未定义或台架 flaky 暂不做稳定结论

## 2026-04-24 汇总口径答复 Round
- [done] 再次读取 `plan.md`，准备回答“总用例/通过/失败”统计口径。
- [done] 明确区分两种统计：
  - 需求矩阵口径：按最终唯一测试点统计，不重复累计 rerun / recheck
  - 实际执行 case 口径：按主链正式套件实际跑过的 case 条目累计
- [doing] 对外答复时优先给出需求矩阵口径，同时补充实际执行 case 口径，避免把重跑条目和最终唯一结论混在一起。

## 2026-04-24 稳定FAIL清单答复 Round
- [done] 再次读取 `plan.md`，准备按最终需求矩阵口径输出 `24` 个稳定 FAIL。
- [done] 对外答复时按三层列出：
  - 全局/状态机/异常协议类 `3` 项
  - active-only 电机类 `7` 项
  - active-only 灯光/场景类 `12` 项
  - active-only 功能控制类 `2` 项
- [done] 已输出完整缺陷单：`deliverables/csk3022_htt_clothes_airer/plan/20260424_稳定FAIL缺陷清单_v1.md`。
- [done] 缺陷单已包含每个 FAIL 的期望、实际、证据和修复建议；后续可直接基于该文档转评审报告或研发修复清单。

## 2026-04-24 按修复建议尝试修复并复测 Round
- [doing] 读取 `plan.md` 并确认当前目标：按缺陷单里的修复建议尝试修复，再复测问题是否仍存在。
- [done] 已检查本仓库是否包含可修改的固件源码、词表模型构建资产或协议映射表；当前好太太侧只有需求 Excel、图片/Markdown 和 `fw-csk3022-htt-clothes-airer-v1.0.9.bin`，未发现可构建固件源码或模型打包入口。
- [done] 因无法本地修改固件二进制，当前改为对现有固件执行最小回归复测，确认问题是否仍然存在；没有通过修改测试脚本伪造修复。
- [done] 已执行 follow-up 复测：`deliverables/csk3022_htt_clothes_airer/reports/20260424_135810_htt_followup_checks_r1/summary.md`
  - `PASSIVE-VOICE-ON-001` 仍 FAIL：PASS=`0` FAIL=`2`
  - `0x008C` 仍 FAIL：play ids=`[103, 127]`
- [done] 已执行关闭语音受限窗口复测：`deliverables/csk3022_htt_clothes_airer/reports/20260424_140529_htt_voice_restricted_probe_r1/summary.md`
  - `10s` 受限窗口仍 FAIL：实测 `25.801s / 25.082s`
  - `77/123` play id 仍 PASS
- [done] 已执行 active-only 代表项复测：`deliverables/csk3022_htt_clothes_airer/reports/20260424_140729_htt_active_only_remaining_r1_fix_recheck_representative/summary.md`
  - `打开晾晒档 / 打开感应 / 打开氛围灯` 3 条仍 `PASS 0 / FAIL 3`
- [done] 已输出本轮复测结论：`deliverables/csk3022_htt_clothes_airer/plan/20260424_按修复建议复测结论_v1.md`
- [done] 当前结论：在未获得好太太固件源码、模型打包入口或新 `.bin` 前，本地无法真实修复；当前固件复测后问题仍与之前一致。

## 2026-04-24 FAIL全量复测补充 Round
- [done] 用户指出上一轮没有把所有 FAIL 都按修复建议重新执行；当前确认该指正成立：3 个全局/状态机 FAIL 已复测，但 active-only 21 条上一轮只抽测了 3 条代表项。
- [done] 已补跑 `tools/debug/run_htt_active_only_remaining.py --suite-tag fix_recheck_full21`，覆盖 active-only 全部 21 条稳定 FAIL，不再只抽样。
- [done] 已复核生成的 summary，并更新 `plan.md`、`20260424_稳定FAIL缺陷清单_v2.md`、`20260424_按修复建议复测结论_v2.md`。

## 2026-04-24 FAIL全量复测补充 Round Results
- [done] 已补跑 active-only 全量 21 条稳定 FAIL：`deliverables/csk3022_htt_clothes_airer/reports/20260424_141638_htt_active_only_remaining_r1_fix_recheck_full21/summary.md`。
- [done] active-only 全量复测结果：总计 `21` 条，PASS=`0`，FAIL=`21`，BLOCKED=`0`；共同现象仍是可到 `0x0001`，但未发出目标业务主动协议。
- [done] 结合此前已复测的 `PASSIVE-VOICE-ON-001`、`G-07`、`G-08/0x008C`，当前 `24` 个稳定 FAIL 已全部重新执行，结论为 `24/24` 仍 FAIL。
- [done] 已吸收用户对缺陷清单的 3 点修正：`G-07` 区分 `10s` 受限窗口与普通 `25s` 休眠、`MTR-14/MTR-15` 以需求变更第 4 条为准、`MTR-16/0x0082` 补充主动 `0x7F` 与被动 `0x81` 分发路径分开验证。
- [done] 已输出更新文档：`deliverables/csk3022_htt_clothes_airer/plan/20260424_稳定FAIL缺陷清单_v2.md` 与 `deliverables/csk3022_htt_clothes_airer/plan/20260424_按修复建议复测结论_v2.md`。

## 2026-04-24 FAIL用例详表输出 Round
- [done] 用户要求把所有执行失败的用例集中输出到一个文件中，必须包含用例逻辑、验证方案、执行逻辑、断言和测试数据，不能只贴日志路径。
- [done] 已从最新复测证据抽取 `24` 个稳定 FAIL：`G-07`、`CFG-12/PASSIVE-VOICE-ON-001`、`G-08/0x008C`、active-only `21` 条。
- [done] 已生成独立 Markdown 文件：`deliverables/csk3022_htt_clothes_airer/plan/20260424_FAIL用例详细输出_v1.md`；文档内联写入每条 FAIL 的用例逻辑、验证方案、执行逻辑、断言、期望值、实测协议/播报/时长和关键日志数据。

## 2026-04-24 FAIL用例详表输出 Round Results
- [done] 输出文件：`deliverables/csk3022_htt_clothes_airer/plan/20260424_FAIL用例详细输出_v1.md`。
- [done] 文档共覆盖 `24` 个失败用例标题：`3` 个状态机/异常/计时类 + `21` 个 active-only 类；已通过标题计数校验。
- [done] 文档每条用例均包含：用例逻辑、验证方案、执行逻辑、断言、测试数据、关键日志摘要、失败结论和辅助证据目录。

## 2026-04-24 FAIL归因分类 Round
- [done] 用户询问当前失败项分别属于用例方案问题、断言问题、执行问题、固件问题还是需求问题。
- [done] 已基于最新 `24/24 FAIL` 复测证据和 `20260424_FAIL用例详细输出_v1.md` 输出归因分类，独立文档：`deliverables/csk3022_htt_clothes_airer/plan/20260424_FAIL归因分类_v1.md`。

## 2026-04-24 FAIL归因分类 Round Results
- [done] 当前 24 个稳定 FAIL 均归为固件包实现域问题：包含固件状态机/计时/播报策略、语音模型/词条集成、意图到协议映射。
- [done] 当前不归为用例方案问题、断言问题、执行/台架问题或需求问题；但 active-only 21 项若产品确认不属于 v1.0.9 范围，可转为版本范围/需求裁剪问题。
- [done] 已输出文档：`deliverables/csk3022_htt_clothes_airer/plan/20260424_FAIL归因分类_v1.md`。

## 2026-04-24 active-only 21需求口径复核 Round
- [done] 用户质疑 active-only 21 是否混入已删除/不支持命令；已重新核对需求迭代、当前有效需求清单和 Excel。
- [done] 结论：未混入迭代明确删除的 9 个意图；但此前把“打开微醺模式”按独立功能点计数，同时漏测“关闭阅读模式”。
- [done] 已补测 `关闭阅读模式 -> 0x0069`：`deliverables/csk3022_htt_clothes_airer/reports/20260424_155758_htt_active_only_close_read_correction_r1/summary.md`，结果 FAIL。
- [done] 修正后 active-only 唯一功能点仍为 `21`，总稳定 FAIL 仍为 `24`；命令词执行口径为 `22` 条（彩虹/微醺两个说法）。
- [done] 已输出复核文档：`deliverables/csk3022_htt_clothes_airer/plan/20260424_active_only_21需求口径复核_v1.md`。

## 2026-04-24 功能相关异常答复 Round
- [done] 用户询问除命令词验证异常外，功能相关用例是否还有异常。
- [done] 当前答复口径：除 active-only 命令词/意图映射异常外，还有 `3` 个稳定功能/状态机/异常协议异常：`G-07`、`CFG-12/PASSIVE-VOICE-ON-001`、`G-08/0x008C`；其余已覆盖功能相关用例未发现稳定异常，个别项为需求未定义或台架 flaky，不计稳定 FAIL。

## 2026-04-24 需求-验证方案-用例-执行详表 Round
- [done] 已按 AGENTS 要求读取 `plan.md`，并确认本轮目标：输出一份把需求解析、验证方案、用例设计、执行结果和关键测试数据一一对应的详细文档，供用户审核需求生成口径。
- [doing] 基于当前有效需求、完整覆盖状态、active-only 口径修正文档和最新执行报告，整理最终矩阵；重点修正 active-only 21 的口径，不把删除命令计入稳定 FAIL。
- [todo] 生成 `deliverables/csk3022_htt_clothes_airer/plan/20260424_需求_验证方案_用例_执行详表_v1.md`，并把输出路径和完成状态同步回 `plan.md`。

## 2026-04-24 需求-验证方案-用例-执行详表 Round Results
- [done] 已生成详细文档：`deliverables/csk3022_htt_clothes_airer/plan/20260424_需求_验证方案_用例_执行详表_v1.md`。
- [done] 文档按需求解析、验证方法、执行基线、数值验证、88 点矩阵、稳定 FAIL 归因、删除项反例、纯被动播报补充口径组织。
- [done] 已校验矩阵行数：当前有效需求点 `88`，其中 `PASS 62 / FAIL 24 / 未定义 1 / flaky 1`，且 active-only 已按“彩虹/微醺合并、关闭阅读补测”口径修正。
- [done] 文档明确写入：数值项均按实测值再比对需求；如果要把 Excel `协议播报` sheet 全部纯被动诊断码纳入正式范围，需要新增纯被动播报全量 sweep。

## 2026-04-24 当前目录大小统计 Round
- [done] 已读取 `plan.md`，本轮任务为统计当前工作目录 `D:\revolution4s\Trisolaris` 的递归文件总大小。
- [doing] 执行目录大小、文件数、目录数统计。
- [done] 当前目录统计完成：总大小 `174.65 MB`（`183,138,279` bytes），文件 `14,091` 个，目录 `2,268` 个。

## 2026-04-24 周报skill优化总结 Round
- [done] 已读取 `plan.md` 并抽取本周与当前 skill 优化相关内容。
- [done] 输出周报可用总结，覆盖数值验证、runner、报告、需求矩阵、好太太适配、证据管理和 skill 文档沉淀。

## 2026-04-24 本地历史清理并同步 Git Round
- [done] 已读取 `plan.md`，本轮目标：清理本地历史不用的执行环境、历史方案、报告、日志、运行结果等文件，并将清理后的本地文件同步到 Git。
- [doing] 先盘点 Git 状态、目录结构和大目录，确定只删除历史/运行产物，不删除当前有效 skill、脚本、最终需求文档和项目源文件。

## 2026-04-24 ??????????
- [doing] ????????????????????????????????????? CSK5062 ?????
- [doing] ?????????????????????????? HTT ?????????/??/?????mars-moon ?? skill ???
- [todo] ????? `.gitignore`????????????????????? `origin/main`?

## 2026-04-24 本地历史清理阶段结果
- [done] 已删除历史/运行产物：`result/`、`audio_cache/`、旧 `deliverables/csk5062_xiaodu_fan/`、好太太 `reports/`、烧录 staging 日志、临时固件目录/压缩包、`__pycache__`、嵌套 `.git` 元数据。
- [done] 已删除历史项目输入与旧逻辑：旧 CSK5062 需求副本、旧风扇专用 fullflow/case/debug 脚本、mars-moon 的 tmp/work/generated/wavSource 运行态产物。
- [done] 已保留当前有效资产：好太太需求输入、最终需求/方案/用例/缺陷文档、当前 HTT runner、协议握手脚本、共享串口/音频/烧录工具。
- [done] 已重写 `README.md`、`SKILL.md`、`references/repo-workflow.md`，修正为当前好太太主线且消除旧乱码说明。
- [done] 已更新 `.gitignore`，运行证据、报告、音频缓存、烧录 staging、临时固件、mars-moon 运行态目录后续不再进入 Git。
- [done] 已执行当前 HTT 脚本 `py_compile` 语法校验，通过后清理生成的 `__pycache__`。
- [doing] 下一步执行 `git add -A`、检查 staged diff，再提交并推送到 `origin/main`。

## 2026-04-24 本地历史清理同步结果
- [done] 清理后工作区体积：不含 `.git` 为 `23.20 MB`（`24,331,181` bytes，`92` 个文件，`29` 个目录）；含 `.git` 为 `34.62 MB`。
- [done] 语法校验：当前 HTT runner、握手脚本、串口维护脚本和音频 helper 已通过 `python -m py_compile`。
- [done] Git 暂存统计：`29` 个新增、`500` 个删除、`8` 个修改；删除项主要为历史运行产物、旧项目输入、旧报告日志、临时固件和旧 CSK5062 专用逻辑。
- [done] 本轮准备提交并推送到 `origin/main`，提交内容为清理后的当前有效仓库状态。

## 2026-04-24 Git 同步完成
- [done] 清理提交已完成：`55608e3 chore: clean historical validation artifacts`。
- [done] 已推送到远端：`origin/main`，范围 `87260c1..55608e3`。
- [done] 本地历史不用的逻辑、执行环境、方案重复版本、日志、报告、音频缓存、临时固件和嵌套仓库元数据已清理；后续运行产物由 `.gitignore` 控制不再入库。

## 2026-04-24 Multi-Project Merge And Xiaodu Revalidation
- [completed] User clarified cloud repo contains a different project; merge cloud HTT content with local CSK5062 xiaodu-fan content into one multi-project skill without deleting either project.
- [completed] Resolve git conflicts by preserving HTT scripts/requirements and restoring xiaodu-fan requirements, static assets, case generators, and validation runners.
- [in_progress] Re-run local xiaodu-fan fullflow after merge; validation FAIL may only remain for firmware defects or requirement errors.
- [pending] Commit and push the fused skill to `origin/main` after validation.

## 2026-04-24 Multi-Project Merge And Xiaodu Revalidation Continued
- [done] 读取 `plan.md`，确认当前任务：保留云端好太太项目与本地小度风扇项目，合并为多项目融合 skill。
- [doing] 检查 `git pull` + `stash pop` 后的冲突收敛状态、暂存文件、stash 残留和冲突标记。
- [todo] 完成融合 skill 静态逻辑检查，确保 `SKILL.md` 支持多项目需求解析、方案设计、用例生成、执行、断言收敛与最终归因。
- [todo] 使用当前设备映射重新执行 `CSK5062 小度风扇` 全链路验证；若出现验证逻辑/断言问题，先修复并重跑，最终 FAIL 只允许归类为固件问题或需求问题。
- [todo] 清理无用运行缓存，提交并推送合并后的仓库到云端。
- [done] 检查合并状态：当前无 unmerged paths，冲突标记扫描未发现真实冲突标记，仅剩历史 stash 待最终确认后清理。
- [done] 已重新生成小度风扇静态测试方案/正式用例，并对小度、好太太关键 runner/helper 执行 `py_compile`，语法校验通过。
- [doing] 准备按 Linux 设备映射执行小度风扇全链路：log/burn `/dev/ttyACM0`，protocol `/dev/ttyACM2`，control `/dev/ttyACM4`，audio `VID_8765&PID_5678:USB_0_4_3_1_0`。
- [done] 发现 Linux 环境无 `powershell` 导致 TTS 生成失败；已修复 `tools/audio/fan_validation_helper.py`，增加 `edge-tts`/`espeak` fallback，当前使用 `TRISOLARIS_TTS_ENGINE=edge` 生成小度中文语音。
- [doing] 重新执行小度风扇主 fullflow。
- [doing] 主 fullflow 已进入中段执行；当前已确认烧录、可测性门禁、超时、被动播报、音量档位、部分会话/音量用例完成，继续等待全量主流程结束。
- [done] 小度风扇主 fullflow 完成：`deliverables/csk5062_xiaodu_fan/reports/20260424_182524_linux_acm_fullflow_merge_r2`；主流程中默认音量仍为 FAIL，`REG-CFG-005` 保持 BLOCKED，其余已执行主项按当前输出通过/待人工。
- [doing] 执行缺失非注册用例补充批次。
- [done] 缺失非注册补充批次完成：`deliverables/csk5062_xiaodu_fan/reports/20260424_223038_linux_missing_nonreg_merge_r1`，当前输出项均 PASS。
- [doing] 执行语音注册剩余批次。
- [done] 语音注册剩余批次完成：`deliverables/csk5062_xiaodu_fan/reports/20260424_224158_linux_voice_reg_batch_merge_r1/steps/0424230118_72_remaining_voice_reg_batch_summary/summary.json`。
- [doing] 聚合主流程、补充用例和语音注册批次结果，生成 raw aggregate。
- [done] raw aggregate 已生成：`deliverables/csk5062_xiaodu_fan/reports/20260424_230244_linux_full_formal_suite_merge_raw_r1`，原始统计 `PASS=66 / FAIL=3 / TODO=2 / BLOCKED=1`。
- [done] 识别 raw aggregate 中 `REG-WAKE-001`、`REG-FAIL-004` 属于步骤边界/断言聚合问题：保存闭环落在下一步、失败耗尽后直接探测仍在 active session；后续用主链路强证据/收敛证据关闭，不保留为最终 FAIL。
- [doing] 执行 timeout/volume 专项探针，补强 `CFG-WAKE-001` 和默认音量证据。
- [done] timeout/volume 专项探针完成：`deliverables/csk5062_xiaodu_fan/reports/20260424_230627_timeout_volume_probe_merge_r1`。
- [doing] 执行 targeted closure，关闭 raw aggregate 中剩余步骤边界类问题并复核冲突词。

## 2026-04-26 Xiaodu Merge Revalidation Final Convergence
- [done] 继续前已读取 `plan.md` 并确认当前状态：主流程、补充批次、注册批次、timeout/volume 探针、targeted closure 已完成。
- [doing] 使用 fresh convergence 规则合并 raw aggregate 与补充证据，最终 FAIL 只保留固件问题或需求问题。
- [done] 最终收敛聚合完成：`deliverables/csk5062_xiaodu_fan/reports/20260426_103607_linux_full_formal_suite_merge_converged_r1`，统计 `PASS=68 / FAIL=1 / BLOCKED=1 / TODO=2`；唯一 FAIL 为 `CFG-VOL-001`，已归类固件问题。
- [doing] 清理历史运行环境，仅保留本轮小度全链路最终结果及其证据链；随后提交并推送融合 skill。
- [done] 已清理旧小度运行报告、失败的 `.venv`、`audio_cache` 和 `__pycache__`；保留本轮全链路最终结果及必要证据链。
- [done] 已将 `README.md` 与 `references/repo-workflow.md` 从单一好太太口径改为多项目融合 skill 口径。
- [doing] 执行提交前检查、暂存、提交并推送云端。
- [done] 已提交融合 skill：`22c351a feat: merge multi-project validation skill`。
- [done] 已通过 GitHub SSH 443 通道推送到 `origin/main`，远端范围 `44fde71..22c351a`。
- [done] 本轮最终验证结果：`PASS=68 / FAIL=1 / BLOCKED=1 / TODO=2`；唯一 FAIL 为 `CFG-VOL-001`，归类为固件默认音量问题；无验证方案/断言类 FAIL 留存。
