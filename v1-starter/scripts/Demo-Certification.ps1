$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Project = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/projects" -ContentType "application/json" -Body (@{ owner_id="hugo"; name="MOS Demo" } | ConvertTo-Json)
$Strategy = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/strategies" -ContentType "application/json" -Body (@{ project_id=$Project.id; name="Demo Strategy"; thesis="Pipeline vertical"; market="BTC"; venue="Lighter"; timeframe="5m" } | ConvertTo-Json)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/strategies/$($Strategy.id)/versions" -ContentType "application/json" -Body (@{ version="1.0.0"; code_hash=("a"*64); config_hash=("d"*64) } | ConvertTo-Json) | Out-Null
$Request = Get-Content (Join-Path $Root "examples/certification-pass.json") -Raw | ConvertFrom-Json
$Request.project_id = $Project.id
$Request.strategy_id = $Strategy.id
$Result = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/certifications/evaluate" -ContentType "application/json" -Body ($Request | ConvertTo-Json -Depth 8)
$Readiness = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/strategies/$($Strategy.id)/readiness"
@{ certification=$Result; persisted_readiness=$Readiness } | ConvertTo-Json -Depth 10
