---
name: trisolaris
description: Trisolaris offline-voice fullflow skill for `D:\revolution4s\Trisolaris`. Use when the task needs to read requirement docs, analyze function points, write the test plan, generate or refresh formal Excel test cases, burn firmware with the local burn wrappers, validate behavior through `COM36`/`COM38`/`COM39`, drive the specified playback device, and sync evidence/reports for the CSK5062 xiaodu-fan workflow.
---

# Trisolaris

Use this skill to execute the current Trisolaris offline-voice workflow end to end inside `D:\revolution4s\Trisolaris`.

## Start Here

1. Read repo-root `plan.md` first. Create it if missing.
2. Follow repo `AGENTS.md`: after each meaningful step, sync done / in-progress / pending items back to `plan.md`.
3. Read `references/repo-workflow.md` before choosing the next action.
4. Read `references/evidence-rules.md` before judging protocol, playback, persistence, PASS/FAIL/BLOCKED, or manual-only items.

## What this skill can own

This skill is the orchestration layer for the whole flow:

- read requirement inputs
- decompose function points
- write or refresh the test plan
- write or refresh the formal Excel cases
- burn firmware through the local bundle rule
- run validation on the fixed serial ports
- drive the specified playback device
- collect evidence under `result/`
- sync conclusions into `plan.md` and deliverables

## Independence boundary

Treat the skill as self-contained for workflow knowledge and decision rules, not as a single-file executable that can run without project resources.

It still requires these external runtime inputs:

- the current Trisolaris repo
- requirement documents and target firmware
- burn bundle/toolchain
- serial devices on `COM36` / `COM38` / `COM39`
- the target playback device when audio validation is needed

Do not depend on another skill such as `mars-moon` for the main flow. Use `mars-moon` only as an optional idea source when a brand-new feature needs decomposition hints.

## Fallback rule when repo scripts are missing

Prefer repo-local tools when they exist because they match the project conventions:

- `tools/burn_bundle/run_fan_burn.ps1`
- `tools/burn_bundle/run_fan_burn.sh`
- `tools/cases/generate_formal_assets.py`
- `tools/cases/export_case_md_to_xlsx.py`
- `tools/debug/run_post_restructure_fullflow.py`
- `tools/debug/run_timeout_volume_probe.py`
- `tools/debug/generate_detailed_bundle_report.py`
- `tools/audio/fan_dual_capture.py`
- `tools/serial/fan_protocol_probe.py`
- `tools/audio/sync_listenai_play.py`
- `tools/audio/listenai-play/scripts/listenai_play.py`
- `tools/audio/listenai-play/scripts/install_laid_windows.ps1`
- `tools/audio/listenai-play/scripts/install_laid_linux.sh`

If one of them is missing or stale, continue with shell/Python directly instead of declaring the flow blocked too early, as long as the local burn bundle, firmware, ports, and evidence path are still available.

## Core Inputs

Treat the requirement directory as input-only. Keep it clean.

Typical inputs are:

- requirement markdown
- terms/phrase Excel
- `tone.h`
- voice-registration Excel
- optional `algo res/`
- target firmware `.bin`
- later user clarifications that override ambiguous document text

If the user clarified behavior after the documents were written, use the latest user clarification as project truth and sync that understanding into the plan, cases, and reports.

## Main Outputs

Write stable outputs outside the requirement directory:

- test plan: `deliverables/csk5062_xiaodu_fan/plan/`
- formal cases: `deliverables/csk5062_xiaodu_fan/cases/`
- reports: `deliverables/csk5062_xiaodu_fan/reports/`
- raw execution evidence: `result/<timestamp_case_name>/`
- supporting references: `references/voice_registration/`

Use Markdown for plan/design/report documents. Use Excel for the formal case table.

Report-writing rules:

- Markdown reports must use Chinese headings/body text.
- Prefer a Windows-friendly encoding such as `UTF-8 with BOM` for user-facing Markdown deliverables.
- The detailed report default filename should stay consistent with the project convention, for example `测试报告-详细.md`.
- Detailed reports must not only expand FAIL items; they must include a clear structure for PASS, FAIL, `待人工`, and `阻塞`.

## Workflow

### 1. Parse the requirements into testable function points

Extract these explicitly:

- default state and power-on behavior
- entry actions and exit conditions
- state changes and post-state behavior
- persistence rules and reboot expectations
- registration rules and conflict boundaries
- protocol hooks and tone/log clues

Treat functional correctness as the primary judgment. Treat protocol, playback, and logs as supporting evidence unless the case is specifically about protocol behavior.

### 2. Build or refresh the test plan

Write or update the test plan under `deliverables/csk5062_xiaodu_fan/plan/`.

Prefer the repo generation chain when refreshing the static assets:

- `tools/cases/generate_formal_assets.py` to refresh the plan / formal case markdown source
- `tools/cases/export_case_md_to_xlsx.py` to export the formal Excel case table

For each feature, capture:

- what the feature does
- how to test it
- what counts as PASS
- how to write negative cases
- how to write abnormal scenarios

Do not stop at single-point validation. Add cross-validation where the feature changes state, such as wake-word switching, voice on/off, or registration results affecting later normal interaction.

### 3. Build or refresh the formal test cases

Maintain the formal case set in Excel under `deliverables/csk5062_xiaodu_fan/cases/`.

Rules:

- MD is for plan/design/reporting; formal cases live in Excel.
- One case should answer one question whenever possible.
- Use `PASS`, `FAIL`, `BLOCKED`, and `TODO` honestly.
- A `FAIL` is valid when the case exposes a firmware defect; do not force every case to pass.
- Keep the case fields explicit: module, test point, preconditions, steps, primary assertion, supporting assertion, status, evidence.

### 4. Burn firmware with the local burn wrappers

Always use the repo-local burn entry scripts. Follow the fixed burn rule exactly:

1. run `tools/burn_bundle/run_fan_burn.ps1` on Windows or `tools/burn_bundle/run_fan_burn.sh` on Linux
2. let the wrapper delete the previously staged local `app.bin` inside `tools/burn_bundle/`
3. let the wrapper copy the target firmware into the local `burn_bundle` staging area and rename it to `app.bin`
4. inspect burn success markers in the local logs
5. confirm the running version from the `COM38` boot log

Keep `tools/burn_bundle/` as the synced local tool payload, but do not bypass the wrapper to call the inner bundle script directly. Also do not burn directly from an arbitrary source path. If the burn logs and the running version do not both match, stop and resolve burn closure first.

### 5. Normalize the device baseline when needed

After burn or after heavy registration testing, normalize the device state before the next batch when appropriate, for example with `config.clear` and reboot. Keep the normalization evidence in `result/`.

### 6. Run the mandatory testability gate first

Every firmware run must start with a gate after burn and version confirmation.

Minimum gate requirements:

- no reboot loop during the startup observation window
- the default wake word can wake the device
- a normal non-volume command can complete one basic interaction
- first-boot default volume is captured immediately after burn from the first startup config

If the gate fails, stop the fullflow immediately and report the firmware as untestable. Do not continue into the main case batch and do not force later cases into fake PASS/FAIL conclusions.

### 7. Execute validation serially

Use repo tools or the direct shell/Python fallback instead of ad-hoc manual steps.

Execution rules:

- `COM36` protocol, `COM38` burn/log, and `COM39` power/boot are the fixed current ports.
- Do not run `COM36`/`COM38` capture batches in parallel.
- Keep serial actions strictly sequential.
- When sending consecutive voice materials, wait for the previous response to finish; if a clean finish signal is not detected, use the project wait window rather than a hard-coded 5 s assumption.
- Use the specified playback device key when the task requires controlled audio playback.
- If `tools/audio/listenai-play` is missing, sync it into `tools/audio/` first. If local playback tooling already exists but the latest cloud version is required, use the update parameter before execution.
- Do not rely on hearing as the formal evidence source.

### 8. Validate parameters with the corrected assertion logic

When a case is about requirement parameters, use the project-approved measurement method instead of a shortcut:

- wake timeout:
  - pure wake case: measure from wake-response playback end to `TIME_OUT` / `MODE=0`
  - wake-plus-command case: measure from command-response playback end to `TIME_OUT` / `MODE=0`
  - only accept the timeout conclusion when both paths are close enough to each other and to the requirement target
- volume step count:
  - anchor at minimum and maximum boundaries first
  - climb from minimum to maximum one step at a time
  - descend from maximum to minimum one step at a time
  - use runtime `mini player set vol` levels to build the actual step ladder
  - require min->max and max->min to be symmetric before judging the step count as valid
- default volume:
  - judge it from the first boot after burn, not after later volume cases have already modified the state
- persistence:
  - follow the live requirement meaning dynamically
  - for save-required items, confirm save completion before power loss
  - for non-save-required items, compare the rebooted state against the requirement default

### 9. Judge results carefully

Use the evidence rules in the reference file. In short:

- protocol proof comes from `COM36` raw capture
- recognition / playback / save / boot clues come from `COM38`
- power-cycle proof comes from `COM39` plus the follow-up boot/behavior evidence
- persistence cannot be claimed before save completion is observed
- manual-only items should stay manual instead of being force-closed automatically

### 10. Sync evidence and conclusions

After each batch:

- store raw artifacts in `result/`
- update `plan.md`
- sync the current truth into the Excel case file and reports
- when generating detailed reports, keep the structure complete: summary table, PASS details, FAIL analysis, and `待人工` / `阻塞` sections
- call out verified items, real defects, blocked items, and manual-only items separately
- clean invalid or empty result directories caused by port contention so they do not pollute formal evidence

## Done Criteria

Treat the fullflow as closed-loop only when all of these are true:

- requirement points are decomposed
- the test plan reflects the latest clarifications
- formal Excel cases exist
- burn and version confirmation are closed-loop
- real device validations exist under `result/`
- conclusions are synced to `plan.md` and the deliverables
- defects, blocked items, and manual-only items are separated clearly
