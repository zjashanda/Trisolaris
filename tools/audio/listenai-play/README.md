# listenai-play

Scan active device keys, install or refresh the laid command when needed, and play audio on the default render device or a specified stable device key on Windows or Linux. Use when Codex needs device probing, keyed playback, default-device playback, or dual-device playback that must stop immediately when a target device is missing or unavailable.

## Skill layout

- `agents/openai.yaml`
- `scripts/install_laid_linux.sh`
- `scripts/install_laid_windows.ps1`
- `scripts/listenai_play.py`
- `SKILL.md`

## Install the skill

Copy this folder into:

```text
~/.codex/skills/listenai-play
```

Then restart Codex.

## Usage and workflow

Use `scripts/listenai_play.py` as the single entrypoint for scan, laid bootstrap, probe, single-play, and dual-play tasks.

## Workflow

1. If the local shell does not expose `laid`, run `python scripts/listenai_play.py ensure-laid` first.
2. If the playback is part of device debug or a formal end-to-end test, make sure the DUT is powered on before probing or playback so a powered-off device is not misread as an audio-route failure.
3. If the user gives a device key, run `scan` or `probe` against that key before playback.
4. If the user does not give a device key, first scan active ListenAI Render devices:
   - if there are zero or one active ListenAI Render devices, default-device playback is allowed
   - if there are multiple active ListenAI Render devices, stop and report the active keys instead of guessing with the default device
5. Let `play` and `dual-play` keep their built-in preflight probe unless the user explicitly asks to skip it.
6. If device resolution or probe fails, stop immediately and report the failure. Do not silently fall back from an explicit bad key to the default device.

## Routing policy

- Prefer a stable device key for any multi-device bench or any workflow that needs repeatable routing.
- If a project keeps playback defaults in a config file, store the verified key there and treat it like the serial-port config:
  - `playback_device_key`
  - `default_device_mode`
  - `use_default_when_unavailable`
  - `last_verified_device_key`
  - `last_verified_device_name`
  - `last_verified_backend_target`
- If the configured key is unavailable and the project allows fallback, fallback to the default render device only when there is at most one active ListenAI Render device.
- If multiple ListenAI Render devices are active, do not fallback to the default render device; report the device list and require the tester to choose another explicit key or to force default-device mode intentionally.
- Keep the failure reason visible so the tester can tell apart a power issue, a missing device, and a real playback-tool issue.

## Key format

- Linux example: `VID_8765&PID_5678:USB_0_4_3_1_0`
- Windows example: `VID_8765&PID_5678:12345678_0000`
- The device key is a stable routing identifier, not a display name. Use the separate `Name` or `FriendlyName` field for operator-facing labels.

## Commands

- `python scripts/listenai_play.py ensure-laid [--platform auto|windows|linux] [--force]`
  - Detect whether `laid` is already available in the local shell profile.
  - Install or refresh it from the bundled installers when it is missing or when `--force` is given.
- `python scripts/listenai_play.py scan [--platform auto|windows|linux] [--direction All|Render|Capture] [--json]`
  - List the currently active device keys, channel counts, backend targets, and names.
- `python scripts/listenai_play.py probe [--platform auto|windows|linux] [--device-key KEY] [--force-default]`
  - Probe the default render device when no key is given.
  - Probe the specified render device when `--device-key` is given.
- `python scripts/listenai_play.py play --audio-file FILE [--device-key KEY] [--repeat N] [--gap SEC] [--skip-probe] [--force-default]`
  - Use the default render device when `--device-key` is omitted.
  - Resolve and validate the specified device key before playback when `--device-key` is provided.
- `python scripts/listenai_play.py dual-play --left-file FILE --right-file FILE [--left-device-key KEY] [--right-device-key KEY] [--repeat N] [--gap SEC] [--skip-probe] [--force-default-left] [--force-default-right]`
  - Run two worker threads in parallel.
  - Each side can target either the default render device or a specific device key.

## Platform backends

- **Windows**
  - Enumerate active ListenAI MMDevices through PowerShell.
  - Derive stable keys from the USB interface path in the form `VID_XXXX&PID_XXXX:TOKEN`.
  - Normalize input audio with `ffmpeg`.
  - Probe and playback through `pygame.mixer` with SDL `directsound`.
  - Install `laid` by writing the bundled PowerShell helper block into the user profile.
  - When no device key is given, open the DirectSound default render device.
- **Linux**
  - Enumerate active USB audio cards from `/dev/snd`, `/proc/asound`, and `udevadm` or sysfs fallback.
  - Derive stable keys in the same `VID_XXXX&PID_XXXX:TOKEN` form.
  - Normalize input audio with `ffmpeg`.
  - Probe and playback through ALSA `aplay`.
  - Install `laid` by writing the bundled shell helper block into `~/.bashrc` and `~/.zshrc`.
  - When no device key is given, use the ALSA default render device.

## Rules

- Prefer stable device keys over transient endpoint names or MMDevice GUIDs when the user needs a specific hardware target.
- Re-scan or re-probe before important playback tasks because the active endpoint set can change after replugging devices.
- Keep the script self-contained; other skills should call this script directly instead of re-implementing device binding logic.
- Report missing dependencies clearly:
  - all platforms: `ffmpeg`
  - Windows: `pygame`
  - Linux: `aplay`
- Keep `SKILL.md` frontmatter minimal and valid YAML, and keep `agents/openai.yaml` to the `interface` block only.

## Resources

- `scripts/listenai_play.py`: Cross-platform CLI for laid bootstrap, scanning device keys, probing default or specified devices, and running single or dual playback with preflight validation.
- `scripts/install_laid_windows.ps1`: Bundled PowerShell installer copied from `listenai-laid-installer` for profile-based laid installation.
- `scripts/install_laid_linux.sh`: Bundled bash/zsh installer copied from `listenai-laid-installer` for profile-based laid installation.
