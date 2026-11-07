# panw_scm

Infrastructure-as-code automation for Palo Alto Networks **Strata Cloud Manager (SCM)**,
using the official [`PaloAltoNetworks/scm`](https://registry.terraform.io/providers/PaloAltoNetworks/scm/latest/docs) Terraform provider.

## Layout

```
terraform/      Root Terraform module (provider, versions, resources)
scripts/        Helper scripts (credential check, .env loader)
docs/api/       SCM API endpoint catalogue: what the API and Terraform can / cannot do
.env.example    Template for SCM API credentials (copy to .env, never commit)
```

## Prerequisites

- Terraform >= 1.5 (`winget install Hashicorp.Terraform`)
- An SCM service account (client ID + secret) with a role on the target Tenant Service Group (TSG)

## Authentication

The provider reads credentials from environment variables:

| Variable            | Example                                         |
|---------------------|-------------------------------------------------|
| `SCM_CLIENT_ID`     | `my-sa@1234567890.iam.panserviceaccount.com`    |
| `SCM_CLIENT_SECRET` | service account secret                          |
| `SCM_SCOPE`         | `tsg_id:1234567890`                             |

PowerShell:

```powershell
$env:SCM_CLIENT_ID     = "..."
$env:SCM_CLIENT_SECRET = "..."
$env:SCM_SCOPE         = "tsg_id:..."
```

## Usage

```powershell
cd terraform
terraform init
terraform plan
terraform apply
```

> Note: Terraform pushes changes to the SCM candidate configuration. Changes must still be
> **pushed/committed** in SCM to take effect on devices / Prisma Access.
