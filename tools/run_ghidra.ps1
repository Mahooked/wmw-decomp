<#
  Decompile libwmw.so with Ghidra in headless mode.

  Usage (from PowerShell):
    tools\run_ghidra.ps1 [-NoAnalyze] [-Project <name>]

  Writes  out/ghidra/apply.log  (Ghidra stdout/stderr)
         out/src/**.cpp         (decompiled C++)
         out/src/_index.tsv      (function -> file, address, size, status)

  The Ghidra project and install live outside the repo; only the produced
  sources are tracked.
#>
param(
  [string]$Tools = (Join-Path $env:TEMP "opencode"),
  [string]$So = (Join-Path $env:TEMP "opencode\wmw\lib\arm64-v8a\libwmw.so"),
  [string]$Project = "wmw",
  [string]$Out = "C:\AIC\wmw-decomp\out",
  [int]$Timeout = 180
)

$ErrorActionPreference = "Stop"
$ghidra = Join-Path $Tools "ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat"
$jdk = Join-Path $Tools "jdk-21.0.12.1+1"
$scriptDir = Join-Path $PSScriptRoot "ghidra"
$projDir = Join-Path $Tools "ghidra_proj"
$logDir = Join-Path $Out "ghidra"

if (-not (Test-Path $ghidra)) { throw "analyzeHeadless not found at $ghidra" }
if (-not (Test-Path $So))      { throw "libwmw.so not found at $So" }
New-Item -ItemType Directory -Path $projDir -Force | Out-Null
New-Item -ItemType Directory -Path $logDir  -Force | Out-Null

$env:JAVA_HOME = $jdk
$env:Path = (Join-Path $jdk "bin") + ";" + $env:Path

$srcDir = Join-Path $Out "src"
$log = Join-Path $logDir "apply.log"

# The postScript arguments: <nameMap> <outRoot> <timeoutSec>
$postArgs = @(
  (Join-Path $Out "symbols\functions.tsv"),
  $srcDir.Replace('\','/'),
  "$Timeout"
)

$arguments = @(
  $projDir, $Project,
  "-import", $So,
  "-scriptPath", $scriptDir,
  "-postScript", "DecompileAll.java"
) + $postArgs + @("-deleteProject")

Write-Host "Launching Ghidra headless..." -ForegroundColor Cyan
Write-Host "  project : $projDir\$Project"
Write-Host "  input   : $So"
Write-Host "  output  : $srcDir"
Write-Host "  log     : $log"

$p = Start-Process -FilePath $ghidra -ArgumentList $arguments `
  -RedirectStandardOutput $log -RedirectStandardError "$log.err" `
  -NoNewWindow -PassThru

Write-Host "pid $($p.Id) started; polling..."
$last = 0
while (-not $p.HasExited) {
  Start-Sleep -Seconds 30
  if (Test-Path $log) {
    $lines = Get-Content $log -ErrorAction SilentlyContinue
    $d = $lines | Where-Object { $_ -match "DecompileAll:" } | Select-Object -Last 1
    if ($d) { Write-Host ("  " + $d) }
  }
  $n = (Get-ChildItem $srcDir -Recurse -Filter *.cpp -ErrorAction SilentlyContinue).Count
  if ($n -ne $last) { Write-Host ("  files written: " + $n); $last = $n }
}
Write-Host "Ghidra exited with code $($p.ExitCode)"
if (Test-Path "$log.err") {
  $e = Get-Content "$log.err" -ErrorAction SilentlyContinue | Where-Object { $_ -match "ERROR|Exception" } | Select-Object -First 20
  if ($e) { Write-Host "--- errors ---"; $e | ForEach-Object { Write-Host "  $_" } }
}
