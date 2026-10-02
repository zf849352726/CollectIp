$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $project ".playwright-browsers"
& ".\.venv\Scripts\python.exe" manage.py run_worker
