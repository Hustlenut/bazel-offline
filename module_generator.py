#!/usr/bin/env python3
"""
Generate a top-level MODULE.bazel from a local registry.

Writes MODULE.bazel containing:
  module(name = "...")
  bazel_dep(name = "<module>", version = "<chosen-version>")

Logic:
  - Scans local_registry/modules/<module>/<version>
  - Picks lexicographically highest version per module by default
  - Writes MODULE.bazel and MODULE.selected.json (summary)
"""
import os
import json
from pathlib import Path

REG_ROOT = Path("local_registry")
OUT = Path("MODULE.bazel")
REG_MODULES = REG_ROOT / "modules"

def pick_version(versions):
    # lexicographic by default; consider semantic compare if you want
    return sorted(versions)[-1]

modules = {}
if not REG_MODULES.exists():
    raise SystemExit("local_registry/modules/ not found; run registry_generator.py first")

for m in sorted(os.listdir(REG_MODULES)):
    mpath = REG_MODULES / m
    if not mpath.is_dir():
        continue
    versions = [v for v in os.listdir(mpath) if (mpath / v).is_dir()]
    if not versions:
        continue
    modules[m] = pick_version(versions)

# write MODULE.bazel
with open(OUT, "w") as fh:
    fh.write('module(name = "offline_prefetch_workspace")\n\n')
    for mod, ver in sorted(modules.items()):
        fh.write(f'bazel_dep(name = "{mod}", version = "{ver}")\n')

# write a manifest summary
with open("MODULE.selected.json", "w") as fh:
    json.dump(modules, fh, indent=2)

print(f"Wrote {OUT} with {len(modules)} bazel_dep entries")
print("Wrote MODULE.selected.json (summary)")
