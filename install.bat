@echo off
rem Install the `picasso` command into a PATH folder so it works from any directory.
setlocal
cd /d "%~dp0"

if defined LOCALAPPDATA (
    set "TARGET=%LOCALAPPDATA%\picasso"
) else (
    set "TARGET=%USERPROFILE%\AppData\Local\picasso"
)

if not exist "%TARGET%" mkdir "%TARGET%"

rem The installed command is a shim that delegates back to the real launcher in
rem this repo folder - copying picasso.cmd alone would break it, because the
rem copy's designlib.py / .venv live next to the ORIGINAL, not in %TARGET%.
rem Substitution happens in PowerShell (reads the template raw, so the shim's
rem own %* arg-forwarding survives untouched; a for /f loop would eat it).
powershell -NoProfile -Command ^
  "$t = Get-Content -Raw '%~dp0install\picasso-shim.tpl';" ^
  "$t = $t.Replace('__REPO_DIR__', '%~dp0'.TrimEnd('\'));" ^
  "Set-Content -Path '%TARGET%\picasso.cmd' -Value $t -NoNewline"

rem Add %TARGET% to the USER PATH if missing. Done in PowerShell so the PATH is
rem read-modify-written without truncation (setx would clip it at 1024 chars).
powershell -NoProfile -Command ^
  "$t = $env:LOCALAPPDATA + '\picasso';" ^
  "$p = [Environment]::GetEnvironmentVariable('Path','User');" ^
  "if ($p -and ($p -like ('*' + $t + '*'))) { Write-Host 'Installed. picasso is already on your PATH.' } else {" ^
  "  $new = if ($p) { $p.TrimEnd(';') + ';' + $t } else { $t };" ^
  "  [Environment]::SetEnvironmentVariable('Path', $new, 'User');" ^
  "  Write-Host 'Installed. A NEW terminal window is needed to pick up the PATH.'" ^
  "}"

echo Try:  picasso inspire
