---
name: scm-change
description: Safe workflow for any Terraform change that will create, modify or delete configuration in Strata Cloud Manager (SCM). Use whenever adding/changing SCM resources or running terraform plan/apply in this repo.
---

# SCM change workflow

1. **Scope check** — confirm the target folder is listed under "Scope" in `CLAUDE.md`.
   If not, stop and ask.
2. **Write code** — edit files under `terraform/`. Keep one file per object type
   (e.g. `addresses.tf`, `address_groups.tf`, `security_rules.tf`).
3. **Format & validate**
   ```
   terraform -chdir=terraform fmt
   terraform -chdir=terraform validate
   ```
4. **Plan** — `terraform -chdir=terraform plan -out=tfplan`.
   Summarise for the user: number of adds / changes / destroys, and list every
   resource being changed or destroyed by name.
5. **Stop if anything is destroyed or replaced** that the user did not explicitly ask for.
6. **Ask for approval** — wait for an explicit "yes" before applying.
7. **Apply the saved plan only** — `terraform -chdir=terraform apply tfplan`
   (never `apply -auto-approve` without a reviewed plan).
8. **Verify** — re-run `plan` and confirm "No changes".
9. **Commit** the code change to git with a message describing what changed in SCM.
10. **Remind the user** that the change is in the SCM candidate config and must be
    pushed from SCM to take effect. Never push it yourself.
