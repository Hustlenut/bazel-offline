#!/usr/bin/env python3
import base64
import hashlib
import json
import shutil
from pathlib import Path

# CONFIG
PACKAGES_DIR = Path("/home/huy/workspace/bazel/bazel-offline/packages")
BCR_DIR = Path("/home/huy/workspace/bazel/bazel-central-registry")
OUT_DIR = Path("/home/huy/workspace/bazel/bazel-offline/offline_cache")
# ---------------------------------------------------------------------

ARCHIVE_DIR = OUT_DIR / "archive" / "sha256"
MODULES_OUT = OUT_DIR / "modules"

OUT_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
MODULES_OUT.mkdir(parents=True, exist_ok=True)


# Helpers
def sri_to_hex(integrity: str) -> str | None:
    """Convert SRI integrity to a hex SHA."""
    for algo in ("sha256-", "sha384-", "sha512-"):
        if integrity.startswith(algo):
            raw = base64.b64decode(integrity[len(algo):])
            return raw.hex()
    return None


def sha256_file(path: Path) -> str:
    """Compute SHA256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(2**20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_local_tarball(url: str) -> Path | None:
    """Locate a tarball inside PACKAGES_DIR that matches the URL's filename."""
    filename = url.split("/")[-1]
    matches = [m for m in PACKAGES_DIR.rglob(filename) if m.is_file()]
    return matches[0] if matches else None


def copy_non_source_files(src_version_dir: Path, out_version_dir: Path):
    """
    Copies everything from a module version EXCEPT source.json,
    because we rewrite that file. Includes MODULE.bazel, patches/*,
    BUILD files, .bzl files, extensions, etc.
    """
    for item in src_version_dir.iterdir():
        if item.name == "source.json":
            continue
        dest = out_version_dir / item.name

        if item.is_file():
            shutil.copy2(item, dest)
        elif item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)


# Process a single version
def process_version(module: str, version: str, src_version_dir: Path):
    src_json = src_version_dir / "source.json"
    if not src_json.exists():
        # Some modules only have MODULE.bazel and no source.json
        out_version_dir = MODULES_OUT / module / version
        out_version_dir.mkdir(parents=True, exist_ok=True)
        copy_non_source_files(src_version_dir, out_version_dir)
        print(f"✔ No source.json, copied files for {module}@{version}")
        return

    with open(src_json) as f:
        data = json.load(f)

    integrity = data.get("integrity", "")
    expected_hex = sri_to_hex(integrity)

    # Extract URLs
    urls = []
    if "url" in data:
        urls = [data["url"]]
    if "urls" in data:
        urls = data["urls"]

    # Find local tarball
    tarball = None
    for url in urls:
        found = find_local_tarball(url)
        if found:
            tarball = found
            break

    if not tarball:
        print(f"⚠️  MISSING TARBALL — skipping {module}@{version}")
        return

    # Compute SHA
    sha_hex = sha256_file(tarball)
    if expected_hex and sha_hex != expected_hex:
        print(f"❌ SHA mismatch for {module}@{version}")
        print(f"    expected={expected_hex}")
        print(f"    got={sha_hex}")
        return

    # Copy archive
    out_tar = ARCHIVE_DIR / sha_hex
    if not out_tar.exists():
        shutil.copy2(tarball, out_tar)

    # Rewrite source.json
    new_url = f"file://{out_tar.resolve()}"
    new_data = data.copy()
    if "url" in new_data:
        new_data["url"] = new_url
    if "urls" in new_data:
        new_data["urls"] = [new_url]

    # Write output
    out_version_dir = MODULES_OUT / module / version
    out_version_dir.mkdir(parents=True, exist_ok=True)

    # Copy everything except source.json
    copy_non_source_files(src_version_dir, out_version_dir)

    # Write rewritten source.json
    with open(out_version_dir / "source.json", "w") as f:
        json.dump(new_data, f, indent=2, sort_keys=True)

    print(f"✔ Processed {module}@{version}")


def main():
    # Write registry.json
    reg = {
        "format_version": "1.0.0",
        "kind": "BazelRegistry",
        "mirrors": []
    }
    with open(OUT_DIR / "registry.json", "w") as f:
        json.dump(reg, f, indent=2)

    # Iterate all modules
    for module_dir in BCR_DIR.glob("modules/*"):
        module = module_dir.name
        out_mod = MODULES_OUT / module
        out_mod.mkdir(parents=True, exist_ok=True)

        versions = sorted([v.name for v in module_dir.iterdir() if v.is_dir()])

        # Write metadata.json
        metadata_file = module_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
        else:
            metadata = {}

        metadata["versions"] = versions

        with open(out_mod / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Process each version
        for ver in versions:
            process_version(module, ver, module_dir / ver)

    print("\n🏁 DONE — Offline registry written to:", OUT_DIR)


if __name__ == "__main__":
    main()
