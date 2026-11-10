# Root of the project's SCM folder tree: PANW under "All Firewalls" (ngfw-shared).
#
# Everything below PANW comes from the workbook and lives in gen_*.tf
# (scripts/workbook_to_tf.py). PANW itself stays here so undoing a deployment
# never removes it.

locals {
  folders_level1 = {
    PANW = {
      parent      = "ngfw-shared" # "All Firewalls"
      description = "Managed by Terraform"
    }
  }
}

resource "scm_folder" "level1" {
  for_each = local.folders_level1

  name        = each.key
  parent      = each.value.parent
  description = each.value.description
  # Folder Snippets rows for PANW (generated in gen_00_structure.tf)
  snippets = length(local.panw_folder_snippets) > 0 ? local.panw_folder_snippets : null
}
