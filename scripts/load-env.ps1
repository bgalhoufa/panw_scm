# Load SCM_* credentials from the repo-root .env into the current PowerShell session.
# Usage (dot-source it):  . .\scripts\load-env.ps1
$envFile = Join-Path $PSScriptRoot '..\.env'
if (-not (Test-Path $envFile)) { throw ".env not found at $envFile (copy .env.example)" }
Get-Content $envFile | Where-Object { $_ -match '^\s*[^#\s][^=]*=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
}
Write-Host "Loaded SCM credentials from .env"
