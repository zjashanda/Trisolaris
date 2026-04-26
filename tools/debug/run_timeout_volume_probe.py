#!/usr/bin/env python
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from run_post_restructure_fullflow import (
    FullflowRunner,
    REPORT_ROOT,
    ROOT,
    ensure_dir,
    extract_runtime_volume_levels,
    ordered_unique,
)

WAKE_TEXT = '\u5c0f\u5ea6\u5c0f\u5ea6'
NORMAL_CMD = '\u6253\u5f00\u7535\u98ce\u6247'
VOL_MIN_CMD = '\u6700\u5c0f\u97f3\u91cf'
VOL_UP_CMD = '\u5927\u58f0\u70b9'
VOL_DOWN_CMD = '\u5c0f\u58f0\u70b9'
MAX_STEPS = 8


def last_runtime_level(step) -> int | None:
    values = extract_runtime_volume_levels(step.log_text)
    return values[-1] if values else None


def main() -> int:
    tag = os.environ.get('TRISOLARIS_BUNDLE_TAG', 'timeout_volume_probe')
    runner = FullflowRunner()
    runner.bundle_dir = REPORT_ROOT / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{tag}"
    runner.static_dir = ensure_dir(runner.bundle_dir / '01_static')
    runner.burn_dir = ensure_dir(runner.bundle_dir / '02_burn')
    runner.exec_dir = ensure_dir(runner.bundle_dir / '03_execution')
    runner.steps_dir = ensure_dir(runner.exec_dir / 'steps')
    runner.stream_dir = ensure_dir(runner.exec_dir / 'streams')
    runner.case_results_path = runner.exec_dir / 'case_results.json'
    runner.summary_md_path = runner.exec_dir / 'execution_summary.md'
    runner.failure_analysis_path = runner.exec_dir / 'failure_analysis.md'
    runner.testability_gate_path = runner.exec_dir / 'testability_gate.json'
    runner.events_path = runner.exec_dir / 'events.jsonl'

    runner.prepare_static_assets()
    result = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'bundle_dir': str(runner.bundle_dir.relative_to(ROOT)),
        'timeout_probe': {},
        'volume_probe': {},
        'evidence': {},
    }

    runner.open_ports()
    try:
        startup = runner.run_powercycle_step('probe_startup', capture_s=10.0, ready_wait_s=5.0)
        clear_cfg = runner.run_shell_step('probe_config_clear', 'config.clear', capture_s=3.0, ready_wait_s=1.0)
        reboot = runner.run_shell_step('probe_reboot_after_clear', 'reboot', capture_s=10.0, ready_wait_s=8.0)

        wake_only = runner.run_wake_timeout_probe('probe_wake_only_timeout', WAKE_TEXT, wait_s=32.0)
        settle_1 = runner.run_idle_wait_step('probe_wake_only_settle', duration_s=3.0)
        wake_cmd = runner.run_post_command_timeout_probe('probe_wake_cmd_timeout', WAKE_TEXT, NORMAL_CMD, wait_s=45.0)
        settle_2 = runner.run_idle_wait_step('probe_wake_cmd_settle', duration_s=3.0)

        timeout_probe = {
            'wake_only_timeout_from_response_end_s': wake_only.detail.get('timeout_from_response_end_s'),
            'wake_only_timeout_from_response_end_to_timeout_marker_s': wake_only.detail.get('timeout_from_response_end_to_timeout_marker_s'),
            'wake_only_wake_to_timeout_s': wake_only.detail.get('wake_to_timeout_s'),
            'wake_only_wake_to_mode_zero_s': wake_only.detail.get('wake_to_mode_zero_s'),
            'wake_cmd_timeout_from_response_end_s': wake_cmd.detail.get('timeout_from_response_end_s'),
            'wake_cmd_timeout_from_response_end_to_timeout_marker_s': wake_cmd.detail.get('timeout_from_response_end_to_timeout_marker_s'),
            'wake_only_markers': wake_only.detail.get('markers', {}),
            'wake_cmd_markers': wake_cmd.detail.get('markers', {}),
        }
        if isinstance(timeout_probe['wake_only_timeout_from_response_end_s'], (int, float)) and isinstance(timeout_probe['wake_cmd_timeout_from_response_end_s'], (int, float)):
            timeout_probe['delta_s'] = round(abs(timeout_probe['wake_only_timeout_from_response_end_s'] - timeout_probe['wake_cmd_timeout_from_response_end_s']), 3)
        else:
            timeout_probe['delta_s'] = None
        result['timeout_probe'] = timeout_probe
        result['evidence']['timeout_probe'] = [
            str(wake_only.step_dir.relative_to(ROOT)),
            str(wake_cmd.step_dir.relative_to(ROOT)),
        ]

        volume_steps = []
        min_step = runner.run_voice_sequence('probe_volume_min_anchor', [WAKE_TEXT, VOL_MIN_CMD], post_wait_s=3.0)
        min_level = last_runtime_level(min_step)
        volume_steps.append({'direction': 'anchor_min', 'cmd': VOL_MIN_CMD, 'level': min_level, 'evidence': str(min_step.step_dir.relative_to(ROOT))})

        asc_levels = []
        current_level = min_level
        for idx in range(1, MAX_STEPS + 1):
            step = runner.run_voice_sequence(f'probe_volume_up_{idx}', [WAKE_TEXT, VOL_UP_CMD], post_wait_s=3.0)
            level = last_runtime_level(step)
            asc_levels.append(level)
            volume_steps.append({'direction': 'up', 'cmd': VOL_UP_CMD, 'level': level, 'evidence': str(step.step_dir.relative_to(ROOT))})
            if level is None:
                break
            if current_level is not None and level <= current_level:
                break
            current_level = level

        max_step = runner.run_voice_sequence('probe_volume_max_anchor', [WAKE_TEXT, '\u6700\u5927\u97f3\u91cf'], post_wait_s=3.0)
        max_level = last_runtime_level(max_step)
        volume_steps.append({'direction': 'anchor_max', 'cmd': '\u6700\u5927\u97f3\u91cf', 'level': max_level, 'evidence': str(max_step.step_dir.relative_to(ROOT))})

        desc_levels = []
        current_level = max_level
        for idx in range(1, MAX_STEPS + 1):
            step = runner.run_voice_sequence(f'probe_volume_down_{idx}', [WAKE_TEXT, VOL_DOWN_CMD], post_wait_s=3.0)
            level = last_runtime_level(step)
            desc_levels.append(level)
            volume_steps.append({'direction': 'down', 'cmd': VOL_DOWN_CMD, 'level': level, 'evidence': str(step.step_dir.relative_to(ROOT))})
            if level is None:
                break
            if current_level is not None and level >= current_level:
                break
            current_level = level

        asc_unique = ordered_unique([level for level in [min_level, *asc_levels, max_level] if isinstance(level, int)])
        desc_unique = ordered_unique([level for level in [max_level, *desc_levels] if isinstance(level, int)])
        desc_norm = list(reversed(desc_unique))
        result['volume_probe'] = {
            'min_level': min_level,
            'max_level': max_level,
            'asc_levels_raw': asc_levels,
            'desc_levels_raw': desc_levels,
            'asc_unique_levels': asc_unique,
            'desc_unique_levels': desc_unique,
            'desc_reversed_levels': desc_norm,
            'count_up': len(asc_unique),
            'count_down': len(desc_unique),
            'symmetric': asc_unique == desc_norm,
            'steps': volume_steps,
        }
        result['evidence']['volume_probe'] = [item['evidence'] for item in volume_steps]
    finally:
        runner.save_streams()
        runner.close_ports()

    (runner.exec_dir / 'probe_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = [
        '# Timeout And Volume Probe',
        '',
        f"- bundle: `{result['bundle_dir']}`",
        f"- wake-only response-end -> MODE=0: `{result['timeout_probe'].get('wake_only_timeout_from_response_end_s')}`s",
        f"- wake-only response-end -> TIME_OUT: `{result['timeout_probe'].get('wake_only_timeout_from_response_end_to_timeout_marker_s')}`s",
        f"- wake-only wake -> TIME_OUT: `{result['timeout_probe'].get('wake_only_wake_to_timeout_s')}`s",
        f"- wake+cmd response-end -> MODE=0: `{result['timeout_probe'].get('wake_cmd_timeout_from_response_end_s')}`s",
        f"- wake+cmd response-end -> TIME_OUT: `{result['timeout_probe'].get('wake_cmd_timeout_from_response_end_to_timeout_marker_s')}`s",
        f"- timeout delta: `{result['timeout_probe'].get('delta_s')}`s",
        f"- volume up levels: `{result['volume_probe'].get('asc_unique_levels')}`",
        f"- volume down levels: `{result['volume_probe'].get('desc_unique_levels')}`",
        f"- volume symmetric: `{result['volume_probe'].get('symmetric')}`",
    ]
    (runner.bundle_dir / 'probe_summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(runner.bundle_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
