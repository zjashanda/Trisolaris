#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='replace')


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def find_requirement_md(bundle_dir: Path) -> Path:
    files = sorted((bundle_dir / '01_static' / 'requirement').glob('*.md'))
    if not files:
        raise FileNotFoundError('requirement markdown not found')
    return files[0]


def find_case_md(bundle_dir: Path) -> Path:
    files = sorted((bundle_dir / '01_static' / 'cases').glob('*.md'))
    if not files:
        raise FileNotFoundError('case markdown not found')
    return files[0]


def parse_requirement_text(text: str) -> dict[str, Any]:
    def expect(pattern: str, cast=str, default: Any = None) -> Any:
        match = re.search(pattern, text)
        if not match:
            return default
        value = match.group(1).strip()
        return cast(value) if cast is not str else value

    return {
        'project_name': expect(r'\u9879\u76ee\u540d\u79f0[:\uff1a]\s*([^\n]+)', default='unknown project'),
        'branch_name': expect(r'\u5206\u652f\u540d\u79f0[:\uff1a]\s*([^\n]+)', default='unknown branch'),
        'chip': expect(r'\u82af\u7247\u578b\u53f7[:\uff1a]\s*([^\n]+)', default='unknown chip'),
        'version': expect(r'\u56fa\u4ef6\u7248\u672c[:\uff1a]\s*([^\n]+)', default='unknown version'),
        'wake_timeout_s': expect(r'\u5524\u9192\u65f6\u957f[:\uff1a]\s*(\d+)s', int, 0),
        'volume_steps': expect(r'\u97f3\u91cf\u6863\u4f4d[:\uff1a]\s*(\d+)', int, 0),
        'default_volume': expect(r'\u521d\u59cb\u5316\u9ed8\u8ba4\u97f3\u91cf[:\uff1a]\s*(\d+)', int, 0),
        'mic_analog_gain_db': expect(r'mic\u6a21\u62df\u589e\u76ca[:\uff1a]\s*(\d+)', int, 0),
        'mic_digital_gain_db': expect(r'mic\u6570\u5b57\u589e\u76ca[:\uff1a]\s*(\d+)', int, 0),
        'proto_baud': expect(r'\u534f\u8bae\u4e32\u53e3[:\uff1a]\s*UART1\u3001\u6ce2\u7279\u7387(\d+)', int, 0),
        'log_baud': expect(r'\u65e5\u5fd7\u4e32\u53e3[:\uff1a]\s*UART0\u3001\u6ce2\u7279\u7387(\d+)', int, 0),
        'wake_power_save': expect(r'\u5524\u9192\u8bcd\u6389\u7535\u4fdd\u5b58[:\uff1a]\s*([^\n]+)', default='unknown'),
        'volume_power_save': expect(r'\u97f3\u91cf\u6389\u7535\u4fdd\u5b58[:\uff1a]\s*([^\n]+)', default='unknown'),
    }


def parse_case_markdown(path: Path) -> dict[str, dict[str, str]]:
    case_map: dict[str, dict[str, str]] = {}
    for line in read_text(path).splitlines():
        if not line.startswith('| `'):
            continue
        cells = [cell.strip() for cell in line[1:-1].split('|')]
        if len(cells) != 10:
            continue
        case_id = cells[0].strip('`')
        case_map[case_id] = {
            'module': cells[1],
            'case_type': cells[2],
            'test_point': cells[3],
            'precondition': cells[4],
            'steps': cells[5],
            'main_assertion': cells[6],
            'aux_assertion': cells[7],
        }
    return case_map


def html_lines(text: str) -> list[str]:
    if not text:
        return []
    return [line.strip() for line in text.replace('<br>', '\n').splitlines() if line.strip()]


def load_case_results(bundle_dir: Path) -> list[dict[str, Any]]:
    path = bundle_dir / '03_execution' / 'case_results.json'
    if not path.exists():
        return []
    return json.loads(read_text(path)).get('case_results', [])


def load_gate(bundle_dir: Path) -> dict[str, Any]:
    for path in [bundle_dir / 'testability_gate.json', bundle_dir / '03_execution' / 'testability_gate.json']:
        if path.exists():
            return json.loads(read_text(path))
    return {}


def firmware_name(bundle_dir: Path) -> str:
    bins = sorted((bundle_dir / '01_static' / 'requirement').glob('*.bin'))
    return bins[0].name if bins else 'unknown firmware'


def status_label(status: str) -> str:
    return {'PASS': 'PASS', 'FAIL': 'FAIL', 'BLOCKED': 'BLOCKED', 'TODO': 'MANUAL'}.get(status, status)


def extract_startup_gain_fragment(bundle_dir: Path) -> str:
    path = bundle_dir / '03_execution' / 'steps' / '01_assist_startup_powercycle_capture' / 'com38_utf8.txt'
    if not path.exists():
        return 'startup log missing'
    text = read_text(path)
    match = re.search(r'AGAIN=(\d+)dB.*?=+(\d+)dB', text, re.S)
    if match:
        return f"{match.group(1)}/{match.group(2)}dB"
    line_match = re.search(r'AADC: AGAIN=.*', text)
    if line_match:
        return line_match.group(0).strip()
    return 'gain fragment not extracted'


def summarize_fail_reason(case_id: str, item: dict[str, Any], req: dict[str, Any]) -> list[str]:
    detail = item.get('detail', {}) or {}
    if case_id == 'CFG-VOL-001':
        actual = detail.get('boot_config', {}).get('volume', 'missing')
        return [
            f'default volume on first boot is {actual}, but requirement is {req.get("default_volume")}.',
            'Likely a default-config/init mismatch rather than a test-step issue.',
        ]
    if case_id == 'CFG-WAKE-001':
        return [
            f'timeout measured from response playback end to MODE=0 is about {detail.get("timeout_from_response_end_s", detail.get("measured_upper_bound_s"))}s; wake to TIME_OUT is about {detail.get("wake_to_timeout_s")}s, which does not match the required {req.get("wake_timeout_s")}s.',
            'Check timeout config and the runtime timeout state-machine implementation.',
        ]
    if case_id == 'CFG-VOL-002':
        return [
            f'volume levels observed: {detail.get("values")}, which does not match requirement count {req.get("volume_steps")}.',
            'Check volume mapping and boundary definition.',
        ]
    if case_id == 'CFG-PROTO-003':
        return [
            'Passive-report protocol did not complete a full receive-to-playback chain.',
            'Check A5 FB 12 CC mapping, resource binding, and playback branch.',
        ]
    if case_id == 'REG-CONFLICT-001':
        return [
            'Reserved function-word conflict protection did not hold.',
            'Add blacklist/protected-word checks in learning flow and regression-test the conflict set.',
        ]
    return [item.get('summary', 'result mismatches requirement.'), 'See evidence for more detail.']


def render_overview(case_results: list[dict[str, Any]]) -> list[str]:
    pass_count = sum(1 for item in case_results if item['status'] == 'PASS')
    fail_count = sum(1 for item in case_results if item['status'] == 'FAIL')
    blocked_count = sum(1 for item in case_results if item['status'] == 'BLOCKED')
    todo_count = sum(1 for item in case_results if item['status'] == 'TODO')
    return [
        f'- recorded cases: `{len(case_results)}`',
        f'- PASS: `{pass_count}`',
        f'- FAIL: `{fail_count}`',
        f'- BLOCKED: `{blocked_count}`',
        f'- MANUAL: `{todo_count}`',
    ]


def build_report(bundle_dir: Path) -> str:
    req = parse_requirement_text(read_text(find_requirement_md(bundle_dir)))
    case_map = parse_case_markdown(find_case_md(bundle_dir))
    case_results = load_case_results(bundle_dir)
    gate = load_gate(bundle_dir)
    fw_name = firmware_name(bundle_dir)
    startup_gain_fragment = extract_startup_gain_fragment(bundle_dir)

    lines: list[str] = []
    lines.extend([
        f'# {fw_name} Detailed Test Report',
        '',
        '## 1. Target',
        '',
        f'- bundle: `{rel(bundle_dir)}`',
        f'- firmware: `{fw_name}`',
        f'- project: `{req.get("project_name")}`',
        f'- branch: `{req.get("branch_name")}`',
        f'- chip: `{req.get("chip")}`',
        f'- requirement version field: `{req.get("version")}`',
        '',
        '## 2. Requirement Baseline',
        '',
        f'- wake timeout: `{req.get("wake_timeout_s")}s`',
        f'- volume steps: `{req.get("volume_steps")}`',
        f'- default volume: `{req.get("default_volume")}`',
        f'- mic gain: `{req.get("mic_analog_gain_db")}` / `{req.get("mic_digital_gain_db")}` dB',
        f'- protocol uart: `COM36 @ {req.get("proto_baud")}`',
        f'- log uart: `COM38 @ {req.get("log_baud")}`',
        f'- wake-word power save: `{req.get("wake_power_save")}`',
        f'- volume power save: `{req.get("volume_power_save")}`',
        '',
        '## 3. Flow',
        '',
        '- read current requirement and formal cases',
        '- burn target firmware and verify version log',
        '- run mandatory testability gate before every firmware validation',
        '- continue full validation only when gate passes',
        '- use COM36 for protocol conclusion and COM38 for auxiliary log/status',
        '',
        '## 4. Testability Gate',
        '',
    ])
    if gate:
        lines.extend([
            '- mandatory gate: `executed`',
            f'- gate result: `{status_label("PASS" if gate.get("passed") else "FAIL")}`',
            f'- first-boot default volume: `{gate.get("first_boot_config", {}).get("volume", "missing")}`',
            f'- startup Running Config count: `{gate.get("startup_running_config_count", 0)}`',
            f'- startup RESET count: `{gate.get("startup_reset_count", 0)}`',
            f'- idle-window Running Config count: `{gate.get("idle_running_config_count", 0)}`',
            f'- idle-window RESET count: `{gate.get("idle_reset_count", 0)}`',
            f'- gate-stage algo error count: `{gate.get("algo_fail_count", 0)}`',
            f'- default wake + normal command frames: `{gate.get("interaction_frames", [])}`',
        ])
        if gate.get('reasons'):
            lines.append('- gate reasons:')
            for reason in gate.get('reasons', []):
                lines.append(f'  - {reason}')
        else:
            lines.append('- gate conclusion: firmware is testable for full validation.')
    else:
        lines.append('- gate record missing.')
    lines.append('')

    if gate and not gate.get('passed', True):
        lines.extend([
            '## 5. Why This Firmware Is Untestable',
            '',
            '- this firmware does not satisfy the minimum preconditions for requirement validation, so execution stops immediately after the gate.',
            '- minimum testable state requires: no reboot loop, default wake works, and wake + normal command can interact normally.',
            '- for this firmware, later PASS/FAIL conclusions are not meaningful before gate issues are fixed.',
            '',
            '## 6. Executed Scope',
            '',
        ])
        lines.extend(render_overview(case_results))
        lines.extend(['', '## 7. Evidence', ''])
        for path in [bundle_dir / 'burn.log', bundle_dir / 'com38.log', bundle_dir / 'com36.log', bundle_dir / 'testability_gate.json', bundle_dir / '03_execution' / 'failure_analysis.md']:
            if path.exists():
                lines.append(f'- `{rel(path)}`')
        lines.append('')
        return '\n'.join(lines)

    lines.extend(['## 5. Execution Overview', ''])
    lines.extend(render_overview(case_results))
    lines.extend([
        '',
        '## 6. Key Parameter Conclusions',
        '',
        f'- default volume is judged only from first boot after burn: actual `{gate.get("first_boot_config", {}).get("volume", "missing") if gate else "missing"}`, requirement `{req.get("default_volume")}`',
    ])
    wake_case = next((item for item in case_results if item['case_id'] == 'CFG-WAKE-001'), None)
    if wake_case:
        detail = wake_case.get('detail', {}) or {}
        lines.append(f'- wake-timeout probe: response-end to `MODE=0` about `{detail.get("timeout_from_response_end_s", detail.get("measured_upper_bound_s", "missing"))}s`, wake to `TIME_OUT` about `{detail.get("wake_to_timeout_s", "missing")}s`, requirement `{req.get("wake_timeout_s")}s`')
    audio_case = next((item for item in case_results if item['case_id'] == 'CFG-AUDIO-001'), None)
    if audio_case:
        lines.append(f'- mic gain remains manual-check item: {audio_case.get("summary", "")}')
        lines.append(f'- startup gain fragment: `{startup_gain_fragment}`')
    lines.append('')

    lines.extend(['## 7. Case Result Table', '', '| Case ID | Module | Test Point | Result | Conclusion |', '| --- | --- | --- | --- | --- |'])
    for item in case_results:
        meta = case_map.get(item['case_id'], {})
        lines.append(f'| `{item["case_id"]}` | {item.get("module", meta.get("module", "unknown"))} | {meta.get("test_point", "n/a")} | `{status_label(item["status"])}` | {item.get("summary", "")} |')
    lines.append('')

    fail_items = [item for item in case_results if item['status'] == 'FAIL']
    todo_items = [item for item in case_results if item['status'] in {'TODO', 'BLOCKED'}]

    lines.extend(['## 8. FAIL Details', ''])
    if not fail_items:
        lines.extend(['- no FAIL items in this run.', ''])
    else:
        for item in fail_items:
            meta = case_map.get(item['case_id'], {})
            lines.extend([
                f'### `{item["case_id"]}` {meta.get("test_point", item.get("module", "n/a"))}',
                '',
                f'- module: `{item.get("module", meta.get("module", "unknown"))}`',
                '- expected:',
            ])
            for line in html_lines(meta.get('main_assertion', '')) or ['not found in formal case table']:
                lines.append(f'  - {line}')
            aux = html_lines(meta.get('aux_assertion', ''))
            if aux:
                lines.append('- additional assertion:')
                for line in aux:
                    lines.append(f'  - {line}')
            lines.append('- how tested:')
            for line in html_lines(meta.get('steps', '')) or ['see execution step logs']:
                lines.append(f'  - {line}')
            lines.append(f'- actual result: {item.get("summary", "n/a")}')
            lines.append('- possible cause:')
            for reason in summarize_fail_reason(item['case_id'], item, req):
                lines.append(f'  - {reason}')
            lines.append('- evidence:')
            for evidence in item.get('evidence', []):
                lines.append(f'  - `{evidence}`')
            lines.append('')

    lines.extend(['## 9. MANUAL / BLOCKED', ''])
    if not todo_items:
        lines.extend(['- no MANUAL or BLOCKED items in this run.', ''])
    else:
        for item in todo_items:
            meta = case_map.get(item['case_id'], {})
            lines.extend([
                f'### `{item["case_id"]}` {meta.get("test_point", item.get("module", "n/a"))}',
                '',
                f'- status: `{status_label(item["status"])}`',
                f'- note: {item.get("summary", "n/a")}',
                '- evidence:',
            ])
            for evidence in item.get('evidence', []):
                lines.append(f'  - `{evidence}`')
            lines.append('')

    lines.extend(['## 10. Key Evidence', ''])
    for path in [bundle_dir / 'case_results.json', bundle_dir / 'failure_analysis.md', bundle_dir / 'burn.log', bundle_dir / 'com38.log', bundle_dir / 'com36.log', bundle_dir / 'testability_gate.json']:
        if path.exists():
            lines.append(f'- `{rel(path)}`')
    lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate detailed report for one bundle')
    parser.add_argument('--bundle-dir', required=True)
    parser.add_argument('--output', default='detailed_report.md')
    args = parser.parse_args()
    bundle_dir = Path(args.bundle_dir)
    if not bundle_dir.is_absolute():
        bundle_dir = (ROOT / bundle_dir).resolve()
    output_path = bundle_dir / args.output
    output_path.write_text(build_report(bundle_dir) + '\n', encoding='utf-8')
    print(output_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
