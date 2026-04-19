param(
    [string]$FirmwareBin = "",
    [string]$CtrlPort = "COM39",
    [string]$BurnPort = "COM38",
    [int]$CtrlBaud = 115200,
    [int]$LogBaud = 115200,
    [int]$BurnBaud = 1500000,
    [int]$CmdDelayMs = 300,
    [int]$PreBurnWaitMs = 1500,
    [int]$PostPowerOnReadSeconds = 8,
    [int]$PostLoglevelReadSeconds = 3,
    [int]$MaxRetry = 3,
    [switch]$VerifyOnly,
    [switch]$SkipLoglevel
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundleScript = Join-Path $scriptRoot "windows\burn.ps1"
$bundleDir = Join-Path $scriptRoot "windows"
$stagedFirmware = Join-Path $bundleDir "app.bin"
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptRoot)

if (-not (Test-Path -LiteralPath $bundleScript)) {
    throw "Local burn bundle not found: $bundleScript"
}

if (-not $FirmwareBin) {
    $requirementDirs = Get-ChildItem -LiteralPath $repoRoot -Directory | Where-Object {
        (Test-Path -LiteralPath (Join-Path $_.FullName "tone.h")) -and
        ((Get-ChildItem -LiteralPath $_.FullName -File -Filter *.bin | Measure-Object).Count -ge 1)
    }
    $candidateBins = @()
    foreach ($dir in $requirementDirs) {
        $candidateBins += Get-ChildItem -LiteralPath $dir.FullName -File -Filter *.bin
    }
    if ($candidateBins.Count -eq 1) {
        $FirmwareBin = $candidateBins[0].FullName
    } elseif ($candidateBins.Count -gt 1) {
        $joined = ($candidateBins | ForEach-Object { $_.FullName }) -join "; "
        throw "Multiple firmware bins found under requirement directories, please specify -FirmwareBin explicitly: $joined"
    } else {
        throw "No firmware bin found under requirement directories; please specify -FirmwareBin explicitly."
    }
}

if (-not $VerifyOnly) {
    $resolvedFirmware = (Resolve-Path -LiteralPath $FirmwareBin).Path
    # Fixed rule: always burn a local staged app.bin to avoid source-path issues.
    if (Test-Path -LiteralPath $stagedFirmware) {
        Remove-Item -LiteralPath $stagedFirmware -Force
    }
    Copy-Item -LiteralPath $resolvedFirmware -Destination $stagedFirmware -Force
    Write-Host "Staged firmware -> $stagedFirmware"
    $FirmwareBin = $stagedFirmware
}

& $bundleScript `
    -FirmwareBin $FirmwareBin `
    -CtrlPort $CtrlPort `
    -BurnPort $BurnPort `
    -CtrlBaud $CtrlBaud `
    -LogBaud $LogBaud `
    -BurnBaud $BurnBaud `
    -CmdDelayMs $CmdDelayMs `
    -PreBurnWaitMs $PreBurnWaitMs `
    -PostPowerOnReadSeconds $PostPowerOnReadSeconds `
    -PostLoglevelReadSeconds $PostLoglevelReadSeconds `
    -MaxRetry $MaxRetry `
    -VerifyOnly:$VerifyOnly `
    -SkipLoglevel:$SkipLoglevel

exit $LASTEXITCODE
