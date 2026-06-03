# Push repo-root .env secrets to Fly (Windows PowerShell).
# From repo root:
#   powershell -ExecutionPolicy Bypass -File backend\scripts\Set-FlySecrets.ps1
# Or:
#   make fly-secrets

param(
    [string]$App = "",
    [string]$EnvFile = ""
)

$ErrorActionPreference = "Stop"

$BackendRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $BackendRoot
if (-not (Test-Path (Join-Path $BackendRoot "fly.toml"))) {
    throw "Expected fly.toml in $BackendRoot"
}

if (-not $EnvFile) {
    $EnvFile = Join-Path $RepoRoot ".env"
}
if (-not (Test-Path $EnvFile)) {
    throw "Missing .env at: $EnvFile"
}

$allowed = @(
    "DATABASE_URL",
    "REDIS_URL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GREEN_API_INSTANCE",
    "GREEN_API_TOKEN",
    "SLACK_WEBHOOK_URL",
    "LANGGRAPH_RECURSION_LIMIT"
)

# Read without UTF-8 BOM (Windows Notepad adds BOM; Fly rejects "\ufeffDATABASE_URL")
$bytes = [System.IO.File]::ReadAllBytes($EnvFile)
$offset = 0
if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    $offset = 3
}
$text = [System.Text.Encoding]::UTF8.GetString($bytes, $offset, $bytes.Length - $offset)

$lines = $text -split "`r?`n" | ForEach-Object {
    $line = $_.Trim().TrimStart([char]0xFEFF)
    if (-not $line -or $line.StartsWith("#")) { return }
    if ($line -match "fly\s+secrets") { return }
    if ($line -notmatch "^([A-Za-z_][A-Za-z0-9_]*)=(.*)$") { return }
    $name = $Matches[1].TrimStart([char]0xFEFF)
    if ($allowed -notcontains $name) { return }
    if ([string]::IsNullOrWhiteSpace($Matches[2])) { return }
    "$name=$($Matches[2])"
} | Where-Object { $_ }

if (-not $lines) {
    throw "No secrets to import. Check $EnvFile has KEY=value lines for: $($allowed -join ', ')"
}

$redisLine = $lines | Where-Object { $_ -like "REDIS_URL=*localhost*" }
if ($redisLine) {
    Write-Warning "REDIS_URL is localhost - set your Upstash rediss:// URL in .env before production."
}

Write-Host "Importing $($lines.Count) secret(s) from $EnvFile into Fly..."
Push-Location $BackendRoot
try {
    $flyArgs = @("secrets", "import")
    if ($App) {
        $flyArgs += @("-a", $App)
    }
    $lines | & fly @flyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "fly secrets import failed (exit $LASTEXITCODE)"
    }
    Write-Host "Done. Run: fly secrets list"
}
finally {
    Pop-Location
}
