---
name: scm-change
description: Safe workflow for any Terraform change that will create, modify or delete configuration in Strata Cloud Manager (SCM), including deploying a filled-in workbook and undoing (rolling back) a deployment. Use whenever adding/changing SCM resources, running terraform plan/apply, or reverting what was sent to SCM.
---

# SCM change workflow

## Deploy a workbook

1. **Scope check** - every folder must be PANW or below it (see `CLAUDE.md`).
2. **Validate** - `.venv\Scripts\python scripts\validate_workbook.py <file>`. Fix errors; read the warnings.
3. **Generate** - `.venv\Scripts\python scripts\workbook_to_tf.py <file>` (replaces `terraform/gen_*.tf`),
   then `terraform -chdir=terraform fmt` and `terraform -chdir=terraform validate`.
   Never edit `gen_*.tf` by hand.
4. **Plan** - load credentials (`. .\scripts\load-env.ps1`), then
   `terraform -chdir=terraform plan -out=tfplan`. Summarise for the user: adds / changes / destroys,
   and list every resource being changed or destroyed by name.
5. **Stop if anything is destroyed or replaced** that the user did not explicitly ask for.
6. **Ask for approval** - wait for an explicit "yes".
7. **Apply the saved plan only** - `terraform -chdir=terraform apply tfplan`.
8. **Verify** - re-run `plan` and confirm "No changes".
9. **Record** - `.venv\Scripts\python scripts\deployments.py record <short-name>`: commits the generated
   code and tags it `deploy/<timestamp>-<name>` (this is the undo point).
10. **Firewalls** - `scripts\scm_devices.py <file>` dry run; `--apply` only after approval.
11. **Remind the user** the change is in the SCM candidate config and must be pushed from SCM.
    Never push it yourself.

## Undo a deployment

1. `.venv\Scripts\python scripts\deployments.py list` - pick the deployment to go back to
   (`restore empty` removes everything generated; the PANW folder always stays).
2. `.venv\Scripts\python scripts\deployments.py restore <tag>` - only rewrites `terraform/gen_*.tf`.
3. Plan, and show the user **every** resource that will be destroyed or changed.
4. Apply only after an explicit "yes", verify with a clean plan, then
   `deployments.py record rollback-<name>`.
5. If the config had already been pushed to firewalls, the owner must push again for the
   rollback to reach them. If a folder still contains firewalls, move them out first
   (SCM will not delete a folder with devices in it).

Never use `terraform destroy`, `apply -destroy`, `-target` deletions, or the SCM
"revert candidate config" API (it discards every admin's pending changes, not just ours).
