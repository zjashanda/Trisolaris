# Plan

## 2026-04-19 Current Round
- [completed] Read `plan.md` and reload the current repo / requirement / fullflow state.
- [completed] Preserve every evidence path referenced by the latest formal deliverables inside `deliverables/csk5062_xiaodu_fan/reports/20260419_162517_post_restructure_fullflow/04_preserved_result_refs/`.
- [completed] Delete earlier test data: remove old report bundles and clear the old `result/` raw-history directory while keeping the latest bundle intact.
- [completed] Verify only the latest report bundle remains and that the current formal outputs no longer depend on deleted external `result/` paths.
- [completed] Check Git preconditions for publishing the current directory: no root `.git`, GitHub auth is available, and nested repos exist under `mars-moon/` and `tools/audio/listenai-play/`.
- [completed] Initialize `D:\revolution4s\Trisolaris` as a root Git repository and avoid nested-repo gitlink capture by temporarily moving nested `.git` directories.
- [completed] Add a minimal root `.gitignore` for local Python/runtime noise and the ephemeral `result/` workspace.
- [completed] Commit the current root directory as the initial root commit: `f8d1705` / `Initial import of Trisolaris`.
- [completed] Create the remote GitHub repository `zjashanda/Trisolaris` and push `main` to `origin`.
- [completed] Restore nested repo metadata for `mars-moon/` and `tools/audio/listenai-play/`, then verify root status is clean and tracking `origin/main`.
- [in_progress] Add a root `README.md`, switch the GitHub repository visibility to public, and clarify whether `mars-moon/` has been uploaded.
- [pending] Commit and push the new `README.md` plus the latest `plan.md` update.

## Current Focus
- The current directory is now published as the Git repository `Trisolaris`.
- Remote URL: `github-zjashanda:zjashanda/Trisolaris.git`
- Web URL: `https://github.com/zjashanda/Trisolaris`

## Execution Rules Still In Force
- Fixed ports: `COM36 @ 9600`, `COM38 @ 115200`, `COM39`.
- Burn entry: `tools/burn_bundle/run_fan_burn.ps1`.
- Protocol conclusions must come from `COM36`; `COM38` is only auxiliary evidence.
- Save-related conclusions require the save-finished log first.
- Wait until the previous playback ends before the next audio; default cadence is `4.5s`, but playback completion allows earlier continuation.
- Requirement validation must cover: function enablement, parameter consistency, and abnormal behavior.
- For save / non-save behavior, verify both the functional effect before power loss and the post-reboot persistence expectation.
