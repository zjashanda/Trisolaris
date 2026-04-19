# Evidence Rules

## Port Responsibilities

- `COM36` is the formal protocol evidence port.
- `COM38` is for recognition logs, playback logs, save logs, and boot config logs.
- `COM39` is for power-cycle and boot control actions.

## Formal Judgment Rules

### Functional-first rule

Judge the feature result by functional behavior first. Use protocol, playback, and logs as supporting evidence unless the case is explicitly about protocol correctness.

### Protocol conclusions

Use raw `COM36` capture as the formal protocol evidence. Do not use the `COM38` log print of `send msg:: ...` as the final protocol proof because that path may be truncated.

### Playback conclusions

Do not rely on hearing as formal evidence. Use `COM38` log behavior such as:

- `receive msg:: ...`
- `play start`
- `play id : ...`
- `play stop`

For negative playback conclusions, distinguish these cases:

- protocol was received but playback was suppressed
- nothing was received because the feature did not trigger
- logs were not captured because the port was busy or the capture path was wrong

### Settings and persistence conclusions

For settings-like or registration-save features, do not judge persistence until save completion was observed first, such as `save config success` or the corresponding registration save log.

Then power-cycle with `COM39` and verify boot config or post-reboot behavior.

### Registration-specific discipline

- Registration timeout should be judged by explicit timeout/recovery logs plus post-timeout recovery behavior.
- A sudden power loss during case execution is a valid abnormal case if the follow-up check proves that the device still boots and base features still work.
- Conflict-protection cases are allowed to fail; exposing a real firmware defect is a correct test result, not a test-design error.

### Manual-only items

If the project truth says a point requires human confirmation, keep it as manual verification instead of force-closing it with weak automation evidence.

### Negative-case discipline

Do not convert `this run captured nothing` directly into `the feature does not exist`.
Check first whether:

- the relevant serial port was occupied
- the capture window was too short
- the device was in the wrong state
- the test path skipped a required entry action
- a prior step left the device in a dirty state

### Result states

- `PASS`: feature path executed and evidence is sufficient
- `FAIL`: feature path executed and contradicted the expected result
- `BLOCKED`: the feature cannot be judged yet because of environment, firmware state, or missing entry conditions
- `TODO`: planned but not executed yet
