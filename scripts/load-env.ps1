# Load credentials into the current PowerShell session (dot-source it):
#   . .\scripts\load-env.ps1                     lab tenant: .env, Terraform workspace "default"
#   . .\scripts\load-env.ps1 -Tenant customer    .env, then .env.customer on top, workspace "customer"
# SCM_TENANT, TF_WORKSPACE and TF_VAR_scm_tenant are set together, so the credentials, the
# Terraform state (one workspace per tenant) and the Python scripts always point at one tenant.
param([string]$Tenant = '')

$root = Join-Path $PSScriptRoot '..'
$files = @(Join-Path $root '.env')
if ($Tenant) { $files += Join-Path $root ".env.$Tenant" }
foreach ($envFile in $files) {
    if (-not (Test-Path $envFile)) { throw "$envFile not found (copy .env.example)" }
    Get-Content $envFile | Where-Object { $_ -match '^\s*[^#\s][^=]*=' } | ForEach-Object {
        $name, $value = $_ -split '=', 2
        Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
    }
}

if ($Tenant) {
    $env:SCM_TENANT = $Tenant
    $env:TF_WORKSPACE = $Tenant
} else {
    Remove-Item Env:SCM_TENANT -ErrorAction SilentlyContinue
    $env:TF_WORKSPACE = 'default'
}
$env:TF_VAR_scm_tenant = $env:TF_WORKSPACE
Write-Host "Loaded credentials for tenant '$($env:TF_WORKSPACE)' ($($env:SCM_SCOPE)); Terraform workspace '$($env:TF_WORKSPACE)'"
