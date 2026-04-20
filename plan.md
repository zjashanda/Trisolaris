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
- [doing] Add the current requirement baseline plus the generated plan / methods / formal cases into the publish set so the repo contains the complete static fullflow assets.
- [pending] Commit and push the added fullflow assets without bringing runtime logs, burn artifacts, or report bundles into Git.
- [pending] Sync the final uploaded file list back into `plan.md` and return it to the user.

