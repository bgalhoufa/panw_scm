# SCM folder hierarchy managed by Terraform.
#
# Each level is its own resource so a child folder always depends on its parent.
# To add a folder, add an entry to the map for its level; `parent` must be the
# name of a folder in the level above.

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
}
