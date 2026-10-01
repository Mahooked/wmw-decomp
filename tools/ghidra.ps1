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
    [string]$Script = 'DecompileAll.java',
    # Appended after the standard postScript arguments, so a script can take
    # extra options without editing this wrapper (e.g. -Extra 'symbol').
    [string[]]$Extra = @(),
    # Point at a scratch project when the checked-in one has been touched by an
    # earlier headless run: headless runs save the program, so any functions
    # created last time persist and pollute a re-import.
    [string]$ProjectDir,
    [string]$ProjectName
)

$ErrorActionPreference = 'Stop'
$Temp = Join-Path $env:LOCALAPPDATA 'Temp\opencode'
$Jdk = Join-Path $Temp 'jdk-21.0.12.1+1'
$Ghidra = Join-Path $Temp 'ghidra_12.1.4_PUBLIC'
$Project = if ($ProjectDir) { $ProjectDir } else { Join-Path $Temp 'ghidra_proj' }
$ProjectName = if ($ProjectName) { $ProjectName } else { 'wmw' }
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
    # -loader-imagebase 0 is load-bearing. Ghidra defaults a PIE .so to
    # 0x100000, which shifts every address by 1 MB relative to the ELF. Our
    # symbol table is in ELF vaddr space, so with the default the decompiler
    # script would build functions at the right *numbers* over the wrong
    # bytes and emit plausible, entirely incorrect C.
    $gargs = @($Project, $ProjectName, '-import', $so,
        '-loader', 'ElfLoader', '-loader-imagebase', '0x0',
        '-loader-dataImageBase', '0x0',
        '-analysisTimeoutPerFile', '1800', '-log', (Join-Path $LogDir "$tag.log"))
}
else {
    $soName = $Rest[0]
    $symTsv = $Rest[1]
    $outDir = $Rest[2]
    $timeout = if ($Rest.Count -gt 3) { $Rest[3] } else { '60' }
    $maxFn = if ($Rest.Count -gt 4) { $Rest[4] } else { '0' }
    $tag = 'decompile'
    $postArgs = @($symTsv, $outDir, $timeout, $maxFn) + $Extra
    $gargs = @($Project, $ProjectName, '-process', $soName, '-noanalysis',
        '-scriptPath', $ScriptDir, '-postScript', $Script) + $postArgs + @(
        '-log', (Join-Path $LogDir "$tag.log"))
}

# Write a tiny .cmd shim: analyzeHeadless.bat ends with `pause`, which blocks
# forever without a console. Redirecting stdin from NUL makes pause return at
# once. Doing this via a shim file avoids all cmd.exe quoting problems.
$quoted = ($gargs | ForEach-Object { '"' + $_ + '"' }) -join ' '
$shim = Join-Path $Temp ("gh_run_" + [guid]::NewGuid().ToString('N').Substring(0, 8) + '.cmd')
$exitFile = Join-Path $Temp ("gh_exit_" + [guid]::NewGuid().ToString('N').Substring(0, 8) + '.txt')
@(
    '@echo off'
    ('call "{0}" {1} < nul' -f $Bat, $quoted)
    ('echo %ERRORLEVEL%> "{0}"' -f $exitFile)
    'exit /b %ERRORLEVEL%'
) | Set-Content -Path $shim -Encoding ASCII

Write-Host "[gh] $Mode"
# Ghidra's analyzers are extremely chatty on AArch64 shared libraries (the
# GCC exception-table analyzer alone emits tens of thousands of "Failed to
# disassemble" lines), and with -NoNewWindow that all lands on our console and
# looks like a hang. Send the child's stdout/stderr to a file instead and
# surface only the lines worth reading.
$Console = Join-Path $LogDir "$tag.console.txt"
$GhidraLog = Join-Path $LogDir "$tag.log"
# Truncate before the run, never after: Ghidra appends to the -log file, and
# deleting it afterwards would throw away the only record of what happened.
Remove-Item -Force $GhidraLog, $Console, "$Console.err" -ErrorAction SilentlyContinue
$p = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', "`"$shim`"" -NoNewWindow `
    -RedirectStandardOutput $Console -RedirectStandardError "$Console.err" -PassThru
$sw = [Diagnostics.Stopwatch]::StartNew()
$lastLine = ''
while (-not $p.HasExited) {
    Start-Sleep -Seconds 15
    # Progress comes from the Ghidra log, not stdout: script println() output
    # goes to the -log file, so a stdout heartbeat would just sit at 0 bytes
    # and look like a hang.
    if (Test-Path $GhidraLog) {
        $prog = Get-Content $GhidraLog -Tail 200 |
            Select-String -Pattern "$([regex]::Escape([IO.Path]::GetFileNameWithoutExtension($Script)))`: " |
            Select-Object -Last 1
        if ($prog) {
            $line = ($prog.Line -replace "^.*?$([regex]::Escape([IO.Path]::GetFileNameWithoutExtension($Script)))\.java> ", '')
            if ($line -ne $lastLine) { Write-Host "[gh] $line"; $lastLine = $line }
        }
    }
    if ((-not $lastLine) -or ($sw.Elapsed.TotalSeconds % 300 -lt 15)) {
        Write-Host ("[gh] running {0,5:N0}s" -f $sw.Elapsed.TotalSeconds)
    }
}
$p.WaitForExit()
$sw.Stop()
Remove-Item -Force $shim -ErrorAction SilentlyContinue
# $p.ExitCode comes back empty from Start-Process -PassThru when stdout is
# redirected, so the shim writes the real code out for us to read.
$code = $p.ExitCode
if ($null -eq $code -or $code -eq '') {
    if (Test-Path $exitFile) { $code = [int](Get-Content $exitFile | Select-Object -First 1) }
    else { $code = -1 }
}
Remove-Item -Force $exitFile -ErrorAction SilentlyContinue
Write-Host "[gh] exit=$code after $([int]$sw.Elapsed.TotalSeconds)s"

if (Test-Path $GhidraLog) {
    Write-Host "[gh] ---- script output ----"
    # Match any postScript's "INFO  <Script>: " lines, not just DecompileAll, so
    # a different -Script still shows its progress and summary output.
    $stem = [IO.Path]::GetFileNameWithoutExtension($Script)
    Get-Content $GhidraLog |
        Select-String -Pattern "$stem`: |SCRIPT ERROR|REPORT SCRIPT ERROR|Save succeeded|Analysis succeeded" |
        ForEach-Object { $_.Line -replace "^.*?$([regex]::Escape($stem))\.java> ", '' }
}
exit $code
