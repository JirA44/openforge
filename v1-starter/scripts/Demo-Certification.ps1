$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Body = Get-Content (Join-Path $Root "examples/certification-pass.json") -Raw
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/certifications/evaluate" -ContentType "application/json" -Body $Body | ConvertTo-Json -Depth 8

