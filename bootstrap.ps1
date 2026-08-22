$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python est introuvable dans le PATH."
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r .\backend\requirements.txt

Write-Host ""
Write-Host "OpenForge est prêt." -ForegroundColor Green
Write-Host "Lancez : .\run.ps1"
