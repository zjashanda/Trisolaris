#!/usr/bin/env bash

set -euo pipefail

FIRMWARE_BIN=""
CTRL_PORT="COM39"
BURN_PORT="COM38"
CTRL_BAUD=115200
LOG_BAUD=115200
BURN_BAUD=1500000
CMD_DELAY_MS=300
PRE_BURN_WAIT_MS=6000
POST_POWER_ON_READ_SECONDS=8
POST_LOGLEVEL_READ_SECONDS=3
MAX_RETRY=3
VERIFY_ONLY=0
SKIP_LOGLEVEL=0

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/../.." && pwd)"
BUNDLE_DIR="$ROOT_DIR/linux"
BUNDLE_SCRIPT="$BUNDLE_DIR/burn.sh"
STAGED_FIRMWARE="$BUNDLE_DIR/app.bin"

usage() {
    cat <<'EOF'
Usage: run_fan_burn.sh [options]

Options:
  -FirmwareBin <path>
  -CtrlPort <device>
  -BurnPort <device>
  -CtrlBaud <int>
  -LogBaud <int>
  -BurnBaud <int>
  -CmdDelayMs <int>
  -PreBurnWaitMs <int>    Hold BOOT after power-on, before releasing BOOT
  -PostPowerOnReadSeconds <int>
  -PostLoglevelReadSeconds <int>
  -MaxRetry <int>
  -VerifyOnly
  -SkipLoglevel
  -h, --help
EOF
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -FirmwareBin) FIRMWARE_BIN="$2"; shift 2 ;;
        -CtrlPort) CTRL_PORT="$2"; shift 2 ;;
        -BurnPort) BURN_PORT="$2"; shift 2 ;;
        -CtrlBaud) CTRL_BAUD="$2"; shift 2 ;;
        -LogBaud) LOG_BAUD="$2"; shift 2 ;;
        -BurnBaud) BURN_BAUD="$2"; shift 2 ;;
        -CmdDelayMs) CMD_DELAY_MS="$2"; shift 2 ;;
        -PreBurnWaitMs) PRE_BURN_WAIT_MS="$2"; shift 2 ;;
        -PostPowerOnReadSeconds) POST_POWER_ON_READ_SECONDS="$2"; shift 2 ;;
        -PostLoglevelReadSeconds) POST_LOGLEVEL_READ_SECONDS="$2"; shift 2 ;;
        -MaxRetry) MAX_RETRY="$2"; shift 2 ;;
        -VerifyOnly) VERIFY_ONLY=1; shift ;;
        -SkipLoglevel) SKIP_LOGLEVEL=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ ! -f "$BUNDLE_SCRIPT" ]]; then
    echo "Local Linux burn bundle not found: $BUNDLE_SCRIPT" >&2
    exit 1
fi

if [[ -z "$FIRMWARE_BIN" ]]; then
    PROJECT_REQ_ROOT="$REPO_ROOT/项目需求"
    if [[ -d "$PROJECT_REQ_ROOT" ]]; then
        mapfile -t CANDIDATE_BINS < <(find "$PROJECT_REQ_ROOT" -mindepth 2 -maxdepth 2 -type f -name '*.bin' | sort)
    else
        CANDIDATE_BINS=()
    fi
    if [[ "${#CANDIDATE_BINS[@]}" -eq 1 ]]; then
        FIRMWARE_BIN="${CANDIDATE_BINS[0]}"
    elif [[ "${#CANDIDATE_BINS[@]}" -gt 1 ]]; then
        printf 'Multiple firmware bins found under 项目需求/*, please specify -FirmwareBin explicitly:\n' >&2
        printf '  %s\n' "${CANDIDATE_BINS[@]}" >&2
        exit 1
    else
        echo "No firmware bin found under 项目需求/*; please specify -FirmwareBin explicitly." >&2
        exit 1
    fi
fi

if [[ "$VERIFY_ONLY" -eq 0 ]]; then
    # Fixed rule: always burn a local staged app.bin to avoid source-path issues.
    rm -f "$STAGED_FIRMWARE"
    cp -f "$FIRMWARE_BIN" "$STAGED_FIRMWARE"
    chmod +x "$BUNDLE_DIR/Uart_Burn_Tool" || true
    echo "Staged firmware -> $STAGED_FIRMWARE"
    FIRMWARE_BIN="$STAGED_FIRMWARE"
fi

exec bash "$BUNDLE_SCRIPT" \
    -FirmwareBin "$FIRMWARE_BIN" \
    -CtrlPort "$CTRL_PORT" \
    -BurnPort "$BURN_PORT" \
    -CtrlBaud "$CTRL_BAUD" \
    -LogBaud "$LOG_BAUD" \
    -BurnBaud "$BURN_BAUD" \
    -CmdDelayMs "$CMD_DELAY_MS" \
    -PreBurnWaitMs "$PRE_BURN_WAIT_MS" \
    -PostPowerOnReadSeconds "$POST_POWER_ON_READ_SECONDS" \
    -PostLoglevelReadSeconds "$POST_LOGLEVEL_READ_SECONDS" \
    -MaxRetry "$MAX_RETRY" \
    $([[ "$VERIFY_ONLY" -eq 1 ]] && printf '%s ' "-VerifyOnly") \
    $([[ "$SKIP_LOGLEVEL" -eq 1 ]] && printf '%s ' "-SkipLoglevel")
