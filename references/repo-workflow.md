# Repo Workflow

## Scope

This reference captures the current Trisolaris workflow for the CSK5062 xiaodu-fan offline-voice project.

## Required Bootstrap

Every turn in `D:\revolution4s\Trisolaris` should:

1. read `plan.md`
2. analyze the next task
3. sync the current plan/progress back to `plan.md`
4. keep executed / in-progress / pending items updated

## Current Input/Output Layout

### Requirement-side inputs

Keep the requirement directory clean. It should contain only input-side artifacts such as:

- requirement markdown
- terms Excel
- `tone.h`
- voice-registration Excel
- optional `algo res/`
- target firmware `.bin`

### Stable outputs

Write generated deliverables outside the requirement directory:

- `deliverables/csk5062_xiaodu_fan/plan/`
- `deliverables/csk5062_xiaodu_fan/cases/`
- `deliverables/csk5062_xiaodu_fan/reports/`
- `result/<timestamp_case_name>/`
- `references/voice_registration/`

## Current Repo Tools

Preferred repo-local tools are:

- `tools/burn_bundle/run_fan_burn.ps1`: local burn entry on Windows
- `tools/burn_bundle/run_fan_burn.sh`: local burn entry on Linux
- `tools/audio/fan_dual_capture.py`: voice + protocol + log capture
- `tools/serial/fan_protocol_probe.py`: protocol injection and log capture
- `tools/cases/export_case_md_to_xlsx.py`: export/refresh formal Excel cases
- `tools/audio/sync_listenai_play.py`: sync or update the local playback helper repo into `tools/audio/`
- `tools/audio/listenai-play/scripts/listenai_play.py`: stable-device playback bound to a device key
- `tools/audio/listenai-play/scripts/install_laid_windows.ps1`: install the Windows `laid` query helper from the synced git-backed repo
- `tools/audio/listenai-play/scripts/install_laid_linux.sh`: install the Linux `laid` query helper from the synced git-backed repo
- `audio_cache/tts/`: reuse generated speech and avoid repeated synthesis
- `audio_cache/manifest.json`: cache index for generated audio assets

If one of these tools is missing, stale, or not suitable for the current machine, fall back to direct shell/Python execution instead of assuming the workflow cannot continue.

## Fixed Burn Rule

Use this exact burn behavior:

1. run `tools/burn_bundle/run_fan_burn.ps1` on Windows or `tools/burn_bundle/run_fan_burn.sh` on Linux
2. let the wrapper delete the previously staged local `app.bin` inside `tools/burn_bundle/`
3. let the wrapper copy the target firmware into the local `burn_bundle` staging area and rename it to `app.bin`
4. check local burn logs for success markers
5. confirm the running version from the `COM38` boot log

Keep `tools/burn_bundle/` as the synced local tool payload, but do not burn directly from the original firmware path or by calling the inner bundle scripts directly.

## Current Serial Mapping

- `COM36`: protocol UART at `9600`
- `COM38`: burn/log UART at `115200`
- `COM39`: power / boot control UART

## Execution Rhythm

Recommended order for a fresh validation push:

1. parse or refresh requirement understanding
2. refresh the test plan if clarifications changed the behavior model
3. refresh the formal cases for the features you will actually run
4. burn and confirm firmware closure
5. normalize baseline when needed
6. execute a small serial batch of cases
7. sync evidence and conclusions immediately
8. clean invalid result directories if port contention created empty artifacts
9. move to the next batch
