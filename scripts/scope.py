"""Which SCM folders this project may manage.

Only folders under one of MANAGED_ROOTS (or the roots themselves) are in scope. A managed
root sits directly under All Firewalls (ngfw-shared). Adding a root here is the owner's
decision; every script and the workbook checker read it from this file.
"""
TOP = "ngfw-shared"                      # "All Firewalls" - never managed itself
MANAGED_ROOTS = ("PANW", "SITES-1XX", "SITES-2XX", "SITES-3XX")  # PANW: lab folders until their firewalls move


def in_scope(folder: str, parents: dict[str, str]) -> bool:
    """True if folder is a managed root or below one. parents maps folder -> parent folder."""
    seen = set()
    while folder and folder not in seen and folder != TOP:
        if folder in MANAGED_ROOTS:
            return True
        seen.add(folder)
        folder = parents.get(folder, "")
    return False
