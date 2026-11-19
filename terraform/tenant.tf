# One Terraform workspace (= one local state) per SCM tenant: "default" is the lab tenant,
# others are named after their .env.<tenant> file. scripts/load-env.ps1 -Tenant <name> sets the
# credentials, TF_WORKSPACE and TF_VAR_scm_tenant together.
#
# Guard: credentials, state and generated code must all be for the same tenant, or plan stops.
variable "scm_tenant" {
  type        = string
  description = "Tenant whose credentials are loaded (set by scripts/load-env.ps1)"
}

output "tenant" {
  value = terraform.workspace

  precondition {
    condition     = var.scm_tenant == terraform.workspace
    error_message = "Credentials are for tenant '${var.scm_tenant}' but the Terraform workspace is '${terraform.workspace}'. Reload them: . .\\scripts\\load-env.ps1 -Tenant <name>"
  }
  precondition {
    condition     = local.generated_for == terraform.workspace
    error_message = "gen_*.tf was generated for tenant '${local.generated_for}', not '${terraform.workspace}'. Regenerate it from this tenant's workbook (SCM_TENANT set) or restore one of its deployment tags."
  }
}
