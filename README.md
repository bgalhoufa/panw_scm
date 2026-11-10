# panw_scm

Infrastructure-as-code automation for Palo Alto Networks **Strata Cloud Manager (SCM)**,
using the official [`PaloAltoNetworks/scm`](https://registry.terraform.io/providers/PaloAltoNetworks/scm/latest/docs) Terraform provider.

## Layout

```
terraform/      Root Terraform module (provider, versions, resources)
scripts/        Helper scripts (credential check, .env loader, template builder, firewall placement)
docs/api/       SCM API endpoint catalogue: what the API and Terraform can / cannot do
templates/      Excel bulk-input template (fill offline -> Terraform code + plan)
.env.example    Template for SCM API credentials (copy to .env, never commit)
```

## Prerequisites

- Terraform >= 1.5 (`winget install Hashicorp.Terraform`)
- An SCM service account (client ID + secret) with a role on the target Tenant Service Group (TSG)
- Python 3.11+ for the helper scripts:
  ```powershell
  python -m venv .venv
  .venv\Scripts\python -m pip install -r requirements.txt
  ```

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

## Bulk input (Excel)

1. Fill in a copy of `templates/SCM_bulk_template.xlsx` (one sheet per object type; see its README sheet).
2. Check it offline: `.venv\Scripts\python scripts\validate_workbook.py my-file.xlsx` (errors block, warnings
   flag references that must already exist in SCM).
3. Objects become Terraform code under `terraform/` and go through `terraform plan` / `apply`.
4. Firewalls (Firewalls sheet) have no Terraform resource; they are placed in folders through the API:
   ```powershell
   .venv\Scripts\python scripts\scm_devices.py my-file.xlsx           # dry run
   .venv\Scripts\python scripts\scm_devices.py my-file.xlsx --apply   # write to SCM
   ```
   Firewalls must already be registered to the tenant; the API cannot add a new serial number.

Rebuild the template after changing `scripts/build_template.py`:
`.venv\Scripts\python scripts\build_template.py`

## Usage

```powershell
cd terraform
terraform init
terraform plan
terraform apply
```

> Note: Terraform pushes changes to the SCM candidate configuration. Changes must still be
> **pushed/committed** in SCM to take effect on devices / Prisma Access.
