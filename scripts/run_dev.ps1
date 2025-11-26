# PowerShell script: run from project root
if (Test-Path .\.venv\Scripts\Activate.ps1) {
    Write-Host "Activating venv..."
    . .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "No .venv found. Create with: python -m venv .venv"
}
Write-Host "Starting dev server..."
uvicorn truthlens.backend.app.main:app --reload --port 8000
