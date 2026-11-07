# Project rules for Claude

Terraform automation for Palo Alto Networks Strata Cloud Manager (SCM), using the
`PaloAltoNetworks/scm` provider. These rules are owned by the repo owner — edit freely.
Hard limits are also enforced in `.claude/settings.json`.

## Claude CAN (without asking)
- Read, write and refactor Terraform, Python scripts and docs in this repo.
- Run read-only commands: `terraform fmt`, `init`, `validate`, `plan`, `show`, `output`,
  `providers`, and `python scripts/scm_auth_check.py`.
- Make read-only (GET) calls to the SCM API.
- Commit to git and push to `origin` (github.com/bgalhoufa/panw_scm).

## Claude must ASK first
- `terraform apply`, `import`, `state rm|mv`, `taint`, `force-unlock` — always show the
  plan summary (adds / changes / destroys) and wait for explicit "yes".
- Any non-GET call to the SCM API (POST / PUT / DELETE).
- Adding new Terraform providers, modules from the registry, or Python dependencies.
- Creating GitHub Actions workflows or anything that runs automatically.

## Claude must NEVER
- Run `terraform destroy` or `terraform apply -destroy`.
- Push / commit the SCM candidate configuration to devices or Prisma Access
  ("Push Config" / jobs API). The repo owner does this manually in SCM.
- Touch folders other than the ones listed under "Scope" below.
- Print, log, commit or paste secrets (`.env`, client secret, tokens, `*.tfvars`, state files).
- Modify or delete objects in SCM that are not managed by this Terraform code.
- Force-push or rewrite git history on `main`.

## Scope (SCM folders Claude may manage)
- PANW (child of `ngfw-shared` / "All Firewalls") and every folder below it.
  The folder tree is defined in `terraform/folders.tf`; new levels only on the owner's request.
- All other folders (HOME-LAB, BALCOES, DATACENTERS, FLIGHT, Prisma Access, ...) are
  read-only for Claude.

## Conventions
- Credentials come only from environment variables / `.env` (see `.env.example`).
  Load them in PowerShell with `. .\scripts\load-env.ps1`.
- Invoke Terraform as `terraform ...` from the `terraform/` directory (not via a full
  path) so the permission rules in `.claude/settings.json` match.
- Follow the `scm-change` skill for any change that will reach SCM.
- Before automating anything, check `docs/api/SCM_API_ENDPOINTS.md`: prefer Terraform when the
  endpoint has a `scm_*` resource; if it is API-only, propose a script and ask first; if it is not
  listed, the API cannot do it.
