# Plan

## 2026-04-19 Current Round
- [completed] Read `plan.md` and reload the current repo / requirement / fullflow state.
- [completed] Preserve every evidence path referenced by the latest formal deliverables inside `deliverables/csk5062_xiaodu_fan/reports/20260419_162517_post_restructure_fullflow/04_preserved_result_refs/`.
- [completed] Delete earlier test data: remove old report bundles and clear the old `result/` raw-history directory while keeping the latest bundle intact.
- [completed] Verify only the latest report bundle remains and that the current formal outputs no longer depend on deleted external `result/` paths.
- [completed] Check Git preconditions for publishing the current directory: no root `.git`, GitHub auth is available, and nested repos exist under `mars-moon/` and `tools/audio/listenai-play/`.
- [in_progress] Initialize `D:\revolution4s\Trisolaris` as a root Git repository while avoiding accidental nested-repo gitlink capture.
- [pending] Create remote repository `zjashanda/Trisolaris` and push the current root directory.
- [pending] Restore any temporarily moved nested-repo metadata and re-check final Git status.

## Current Focus
- Publish the current `Trisolaris` directory as a Git repository named `Trisolaris`.
- Keep the root repo self-contained instead of accidentally committing nested repos as gitlinks.

## Execution Rules Still In Force
- Fixed ports: `COM36 @ 9600`, `COM38 @ 115200`, `COM39`.
- Burn entry: `tools/burn_bundle/run_fan_burn.ps1`.
- Protocol conclusions must come from `COM36`; `COM38` is only auxiliary evidence.
- Save-related conclusions require the save-finished log first.
- Wait until the previous playback ends before the next audio; default cadence is `4.5s`, but playback completion allows earlier continuation.
- Requirement validation must cover: function enablement, parameter consistency, and abnormal behavior.
- For save / non-save behavior, verify both the functional effect before power loss and the post-reboot persistence expectation.
