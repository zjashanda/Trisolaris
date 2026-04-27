---
name: trisolaris
description: Multi-project offline voice validation skill for Trisolaris. Use when tasks need to read a project requirement folder, design validation logic and formal cases, burn firmware, drive audio, capture protocol/log/control serial evidence, fix assertion gaps, execute fullflow validation, and publish reusable project-specific test logic for CSK5062 xiaodu-fan, CSK3022 HTT clothes-airer, or future offline voice projects.
---

# Trisolaris Multi-Project Offline Voice Validation

## Start Here

1. Read repo-root `plan.md` first; create it if missing.
2. After each meaningful step, sync done / in-progress / pending state back to `plan.md`.
3. Read `references/fullflow-validation-method.md` before handling a new requirement, a changed requirement, fullflow execution, assertion convergence, or skill publishing.
4. Read `references/evidence-rules.md` before judging protocol, playback, persistence, PASS/FAIL/BLOCKED, or manual-only items.
5. Select the active project from the user's requirement path or explicit project name; do not let one project's runtime artifacts overwrite another project's plan/cases/reports.

## Project Layout Rule

- Requirement inputs stay in the project input directory, for example `项目需求/CSK5062小度风扇需求/` or `项目需求/好太太晾衣机/`.
- Stable deliverables are project-scoped under `deliverables/<project_key>/plan/`, `deliverables/<project_key>/cases/`, and `deliverables/<project_key>/archive/`.
- Runtime evidence is local-only under `result/` or `deliverables/<project_key>/reports/`; do not commit raw logs, audio cache, burn staging, or temporary firmware payloads unless the user explicitly asks.
- Future projects should add a new `deliverables/<project_key>/` and project-specific runners only when shared runners cannot be parameterized safely.

## Current Project Profiles

### CSK5062 小度风扇

- Input: `项目需求/CSK5062小度风扇需求/`
- Outputs: `deliverables/csk5062_xiaodu_fan/`
- Main scripts:
  - `tools/cases/generate_formal_assets.py`
  - `tools/cases/export_case_md_to_xlsx.py`
  - `tools/debug/run_post_restructure_fullflow.py`
  - `tools/debug/run_missing_nonreg_cases.py`
  - `tools/debug/run_remaining_voice_reg_batch.py`
  - `tools/debug/generate_full_formal_aggregate.py`
  - `tools/debug/apply_fresh_full_suite_convergence.py`
  - `tools/debug/run_fresh_closure_targets.py`
  - `tools/debug/run_timeout_volume_probe.py`
- Linux device mapping is user-provided; the latest local mapping was log/burn `/dev/ttyACM0`, protocol `/dev/ttyACM2`, control/boot `/dev/ttyACM4`, audio key `VID_8765&PID_5678:USB_0_4_3_1_0`.

### CSK3022 好太太晾衣机

- Input: `项目需求/好太太晾衣机/`
- Outputs: `deliverables/csk3022_htt_clothes_airer/`
- Main scripts:
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
- Before functional judgment, close MCU readiness: brand query, heartbeat, and ready response must be handled; repeated `MCU is not ready!` blocks formal functional conclusions.

## Hardware And Burn Rules

- Default Windows mapping: `COM36 @ 9600` protocol, `COM38 @ 115200` log/burn, `COM39 @ 115200` power/boot.
- Linux mappings must come from the user or local probe; never assume `/dev/ttyACM*` order if the user gave explicit ports.
- Burn only through repo wrappers: `tools/burn_bundle/run_fan_burn.ps1` on Windows or `tools/burn_bundle/run_fan_burn.sh` on Linux.
- Burn timing for every project on the relay fixture is: power off -> BOOT on -> power on -> keep BOOT asserted for `PreBurnWaitMs` (default `6000ms`) -> BOOT off -> start `Uart_Burn_Tool`; the hold happens after `uut-switch1.on` and before `uut-switch2.off`.
- If the device supports `config.clear` or an equivalent full reset, execute `config.clear -> reboot -> burn` before validating firmware defaults.
- Burn closure requires burn success markers plus running-version confirmation from the boot/log UART.

## Validation Workflow

1. Parse requirements and latest user clarifications into testable function points.
2. Generate or refresh test plan and formal cases for the active project.
3. Burn and close a testability gate before broad execution.
4. Execute validation serially; do not run protocol/log captures in parallel on the same ports.
5. Aggregate project cases once all batches complete.
6. If raw FAIL is caused by assertion logic, empty capture, state contamination, missing save closure, or unmet precondition, fix the validation path and rerun the affected case. Final FAIL may only mean firmware defect or requirement error.
7. Sync final status to project case assets and `plan.md`.

## Evidence Rules

- Use protocol UART raw capture as formal protocol evidence; log `send msg::` is auxiliary.
- Use log UART for recognition, playback, save, boot config, timeout markers, and play-id evidence.
- Do not use hearing as formal evidence.
- Persistence conclusions require save completion before power loss.
- Negative cases must distinguish feature absence from capture failure, wrong state, port contention, or short windows.
- Manual-only items remain `TODO`/manual instead of weak automation PASS/FAIL.

## Assertion Rules That Must Stay Fixed

- Wake timeout: measure pure wake and wake+command from response playback end to `TIME_OUT` / `MODE=0`; both paths must agree with the requirement.
- Volume steps: anchor min/max, climb min->max, descend max->min, and compare runtime `mini player set vol` ladders for symmetry.
- Default volume: after `config.clear -> reboot -> burn`, capture first `Running Config`, probe from default to one boundary, probe both boundaries for total ladder, then compute default gear as `total_volume_gears - effective_steps_from_default_to_max` for upward probing.
- HTT active commands that change module-local state only after MCU confirmation must emulate the MCU passive reply before asserting the side effect. Examples: active volume `0x0041/0x0042` needs the same passive word returned before probing the volume ladder; active voice-off `0x0016` needs passive `0x0012` returned before asserting restricted-state behavior.
- For HTT full-chain command coverage, use a stable official alias from the same requirement row when a single synthetic-audio phrase causes deterministic cross-intent recognition; keep the alias-probe evidence, but do not leave a functional FAIL caused only by TTS phrase selection.
- Volume persistence: wait for `refresh config volume=` / save closure before reboot; compare reboot state to the live requirement, not to a hard-coded default.
- Command-word coexistence: require save closure, reboot, learned alias replay, and original default command replay; a target control frame inside an already active session is sufficient even if the wake frame is not repeated.
- Template-full checks: actively fill templates inside the case, observe save closure, reboot, then re-enter learning; never infer template-full from startup `regCmdCount` alone.
- Conflict-word checks: use the actual spoken phrase from the word table; for stochastic default-wake conflict, repeat from clean baselines before keeping a firmware FAIL.

## Reporting And Publishing

- Markdown reports use Chinese headings/body and Windows-friendly UTF-8 where practical.
- Reports must separate PASS, FAIL, BLOCKED, and TODO/manual items.
- Final FAIL list must not include validation-plan/assertion issues.
- Before pushing, run relevant `py_compile`, inspect `git status --short`, avoid committing runtime evidence, and do not delete another project's assets while merging.
