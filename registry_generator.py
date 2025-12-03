import os
import re
import json
import hashlib
import argparse

not_added = []


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return "sha256-" + h.digest().hex()


def extract_module_and_version(path, filename):
    """
    Universal filename parser for Bazel registry module generation.
    Handles:
    - <module>-<version>.tar.gz
    - <module>-v<version>.tar.gz
    - v<version>.tar.gz  (module = parent dir)
    - <version>.tar.gz   (module = parent dir)
    - <git-hash>.tar.gz  (module = parent dir)
    - 2.0-rc1.tar.gz     (module = parent dir)
    """

    # Remove archive extension
    base = re.sub(r'\.(tar\.gz|zip)$', '', filename)

    # --------------------------
    # Case 1: module-version
    # --------------------------
    m = re.match(r'^(?P<module>.+)-v?(?P<version>[0-9][0-9A-Za-z.\-]*)$', base)
    if m:
        module = m.group("module").lower().replace("_", "-")
        version = m.group("version")
        return module, version

    # Folder above contains the module name
    module_from_folder = os.path.basename(os.path.dirname(path)).lower()

    # --------------------------
    # Case 2: v1.2.3 → version only
    # --------------------------
    m = re.match(r'^v(?P<version>[0-9].+)$', base)
    if m:
        return module_from_folder, m.group("version")

    # --------------------------
    # Case 3: pure version number (e.g. Abseil old releases)
    # --------------------------
    m = re.match(r'^[0-9][0-9A-Za-z.\-]*$', base)
    if m:
        return module_from_folder, base

    # --------------------------
    # Case 4: git hash (7–40 hex chars)
    # --------------------------
    m = re.match(r'^[0-9a-f]{7,40}$', base)
    if m:
        return module_from_folder, base

    # --------------------------
    # Case 5: rc versions (2.0-rc1 etc)
    # --------------------------
    m = re.match(r'^(?P<version>[0-9].*rc[0-9]*)$', base)
    if m:
        return module_from_folder, m.group("version")

    return None, None


def main(download_root, registry_root):
    for root, dirs, files in os.walk(download_root):
        for f in files:
            if not (f.endswith(".tar.gz") or f.endswith(".zip")):
                continue

            full_path = os.path.join(root, f)

            module, version = extract_module_and_version(full_path, f)
            if not module:
                print(f"Skipping unrecognized file name: {f}")
                not_added.append(os.path.relpath(full_path, download_root))
                continue

            # Compute integrity
            integrity = sha256_of_file(full_path)

            # Registry directory
            mod_dir = os.path.join(registry_root, "modules", module, version)
            os.makedirs(mod_dir, exist_ok=True)

            # MODULE.bazel
            with open(os.path.join(mod_dir, "MODULE.bazel"), "w") as mf:
                mf.write(f'module(name = "{module}", version = "{version}")\n')

            # source.json
            url = "file://" + os.path.abspath(full_path)
            with open(os.path.join(mod_dir, "source.json"), "w") as sf:
                json.dump({"url": url, "integrity": integrity}, sf, indent=2)

            print(f"Added module {module}@{version}")

    # --------------------------------
    # Write skipped files to not_added.txt
    # --------------------------------
    if not_added:
        out_file = os.path.join(registry_root, "not_added.txt")
        with open(out_file, "w") as f:
            for item in not_added:
                f.write(item + "\n")
        print(f"\n⚠️  Wrote list of skipped files to {out_file}")
    else:
        print("\n✔ All files successfully added!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("download_root")
    parser.add_argument("registry_root")
    args = parser.parse_args()

    main(args.download_root, args.registry_root)
