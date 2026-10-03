$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $project ".playwright-browsers"
& ".\.venv\Scripts\python.exe" manage.py migrate --noinput
& ".\.venv\Scripts\python.exe" manage.py collectstatic --noinput --clear
& ".\.venv\Scripts\waitress-serve.exe" --listen=127.0.0.1:8000 webapp.wsgi:application
