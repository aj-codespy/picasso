@echo off
rem Picasso launcher for Windows - creates its own venv on first run, then runs the CLI.
rem Install once with:  install.bat   (copies picasso.cmd into a PATH folder)
setlocal
cd /d "%~dp0"

rem Prefer the py launcher (python.org installer) - plain `python` can be the
rem Microsoft Store alias stub which just opens the Store instead of running.
set "PY=python"
where py >nul 2>nul && set "PY=py"

set "VENV=.venv"
set "VENV_PY=%VENV%\Scripts\python.exe"

rem A polluted PYTHONPATH can shadow the venv's site-packages - neutralize it.
set "PYTHONPATH="

if not exist "%VENV_PY%" (
    echo Picasso first run: creating virtual environment ...
    "%PY%" -m venv "%VENV%"
    if errorlevel 1 goto :fail
    rem Some Pythons don't bundle pip into venvs - bootstrap it.
    if not exist "%VENV%\Scripts\pip.exe" (
        if not exist "%VENV%\Scripts\pip3.exe" (
            "%VENV_PY%" -m ensurepip --upgrade
            if errorlevel 1 goto :fail
        )
    )
    "%VENV_PY%" -m pip install --quiet --upgrade pip
    if errorlevel 1 goto :fail
    rem The Google provider uses the official SDK; install it upfront so every
    rem provider works without extra steps. The other providers are stdlib-only.
    "%VENV_PY%" -m pip install --quiet google-genai
    if errorlevel 1 goto :fail
    echo Virtual environment ready.
)

"%VENV_PY%" designlib.py %*
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo Picasso failed - see the message above.
exit /b 1
