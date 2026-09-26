<#
.SYNOPSIS
    Run Ghidra analyzeHeadless.bat without hanging on its "Press any key" pause.

.DESCRIPTION
    analyzeHeadless.bat ends with a `pause` on error. In a non-interactive shell
    that blocks forever waiting for a keypress, which looks exactly like a hang.
    This wrapper feeds the batch file an empty stdin so `pause` returns
    immediately, and always echoes the exit code.

    Usage:
        gh.ps1 import  <so-path>
        gh.ps1 script  <so-name> <symbolTsv> <outDir> <timeoutSec> <maxFunctions>
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('import', 'script')][string]$Mode,
    [Parameter(Mandatory = $true)][string[]]$Rest,
    [string]$Script = 'DecompileAll.java'
)

$ErrorActionPreference = 'Stop'
$Temp = Join-Path $env:LOCALAPPDATA 'Temp\opencode'
$Jdk = Join-Path $Temp 'jdk-21.0.12.1+1'
$Ghidra = Join-Path $Temp 'ghidra_12.1.4_PUBLIC'
$Project = Join-Path $Temp 'ghidra_proj'
$ProjectName = 'wmw'
$Bat = Join-Path $Ghidra 'support\analyzeHeadless.bat'
$ScriptDir = Join-Path $PSScriptRoot 'ghidra'
$LogDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'out\ghidra'

if (-not (Test-Path $Jdk)) { throw "JDK not found at $Jdk" }
if (-not (Test-Path $Bat)) { throw "analyzeHeadless.bat not found at $Bat" }
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$env:JAVA_HOME = $Jdk
$env:Path = (Join-Path $Jdk 'bin') + ';' + $env:Path
$env:GHIDRA_MAX_MEM = '6G'

if ($Mode -eq 'import') {
    $so = $Rest[0]
    $tag = 'import'
    $gargs = @($Project, $ProjectName, '-import', $so,
        '-analysisTimeoutPerFile', '1800', '-log', (Join-Path $LogDir "$tag.log"))
}
else {
    $soName = $Rest[0]
    $symTsv = $Rest[1]
    $outDir = $Rest[2]
    $timeout = if ($Rest.Count -gt 3) { $Rest[3] } else { '60' }
    $maxFn = if ($Rest.Count -gt 4) { $Rest[4] } else { '0' }
    $tag = 'decompile'
    $gargs = @($Project, $ProjectName, '-process', $soName, '-noanalysis',
        '-scriptPath', $ScriptDir, '-postScript', $Script,
        $symTsv, $outDir, $timeout, $maxFn, '-log', (Join-Path $LogDir "$tag.log"))
}

# Write a tiny .cmd shim: analyzeHeadless.bat ends with `pause`, which blocks
# forever without a console. Redirecting stdin from NUL makes pause return at
# once. Doing this via a shim file avoids all cmd.exe quoting problems.
$quoted = ($gargs | ForEach-Object { '"' + $_ + '"' }) -join ' '
$shim = Join-Path $Temp ("gh_run_" + [guid]::NewGuid().ToString('N').Substring(0, 8) + '.cmd')
@(
    '@echo off'
    ('call "{0}" {1} < nul' -f $Bat, $quoted)
    'exit /b %ERRORLEVEL%'
) | Set-Content -Path $shim -Encoding ASCII

Write-Host "[gh] $Mode"
$p = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', "`"$shim`"" -NoNewWindow -PassThru -Wait
Remove-Item -Force $shim -ErrorAction SilentlyContinue
Write-Host "[gh] exit=$($p.ExitCode)"
if (Test-Path (Join-Path $LogDir "$tag.log")) {
    Write-Host "[gh] ---- script output ----"
    # Match any postScript's "INFO  <Script>: " lines, not just DecompileAll, so
    # a different -Script still shows its progress and summary output.
    $stem = [IO.Path]::GetFileNameWithoutExtension($Script)
    Get-Content (Join-Path $LogDir "$tag.log") |
        Select-String -Pattern "$stem`: |error:|ERROR .*Analysis|Save succeeded" |
        ForEach-Object { $_.Line -replace "^.*?$([regex]::Escape($stem))\.java> ", '' }
}
exit $p.ExitCode
