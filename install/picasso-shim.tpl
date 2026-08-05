@echo off
rem Picasso installed command - delegates to the real launcher in the repo,
rem so designlib.py / .venv (which live next to the real picasso.cmd) are found
rem regardless of which directory picasso is run from.
call "__REPO_DIR__\picasso.cmd" %*