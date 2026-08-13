$envFile = Join-Path $PSScriptRoot "..\.env"
$exampleFile = Join-Path $PSScriptRoot "..\.env.example"

if (Test-Path $envFile) {
    Write-Host ".env already exists. Leaving it unchanged."
    exit 0
}

Copy-Item $exampleFile $envFile
Write-Host "Created .env from .env.example. Edit it with your real Toss and API credentials."
