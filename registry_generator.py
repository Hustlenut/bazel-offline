#!/usr/bin/env python3
import os
import hashlib
import json
from pathlib import Path

DOWNLOAD_ROOT = Path("cpp_packages")
REGISTRY_ROOT = Path("local_registry")
REGISTRY_URL = "file:///home/huy/workspace/bazel/bazel-offline/local_registry"

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def to_module_name(org, repo):
    # Bazel modules require:
    # - lowercase
    # - no slashes
    return f"{org}_{repo}".lower()

def find_packages():
    """
    Walk cpp_packages and identify:
    - module name
    - version
    - file path
    """
    results = []
    for root, dirs, files in os.walk(DOWNLOAD_ROOT):
        for f in files:
            full = Path(root) / f

            # Must be an archive
            if not (f.endswith(".tar.gz") or f.endswith(".tgz") or f.endswith(".zip")):
                continue

            # Expect a structure:
            # cpp_packages/github.com/ORG/REPO/archive/refs/tags/VERSION/file
            parts = full.parts

            try:
                pkg_index = parts.index("github.com")
            except ValueError:
                # also support sourceware.org, etc.
                continue

            try:
                org = parts[pkg_index + 1]
                repo = parts[pkg_index + 2]
            except IndexError:
                continue

            module = to_module_name(org, repo)

            # Try to extract version from directory structure
            version = None

            # Case 1: archive/refs/tags/<tag>/<file>
            if "tags" in parts:
                idx = parts.index("tags")
                version = parts[idx + 1].replace(".tar.gz", "").replace(".zip", "")

            # Case 2: releases/download/<version>/<file>
            elif "download" in parts:
                idx = parts.index("download")
                version = parts[idx + 1]

            if version is None:
                print("WARN: Could not determine version for", full)
                continue

            results.append((module, version, full))

    return results


def write_metadata(module_dir, module_name):
    meta = {
        "homepage": "",
        "maintainers": [],
        "versions": sorted(os.listdir(module_dir)),
    }
    with open(module_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)


def write_module_bazel(path, module_name, version):
    content = f"""module(
    name = "{module_name}",
    version = "{version}",
)
"""
    with open(path, "w") as f:
        f.write(content)


def write_source_json(path, file_path):
    sha = sha256_file(file_path)
    url = f"file://{file_path.resolve()}"

    source = {
        "url": url,
        "integrity": f"sha256-{sha}",
        "strip_prefix": "",
    }

    with open(path, "w") as f:
        json.dump(source, f, indent=2)


def write_registry_json():
    root = {
        "kind": "BazelRegistry",
        "version": 1,
        "repository": REGISTRY_URL,
    }
    with open(REGISTRY_ROOT / "registry.json", "w") as f:
        json.dump(root, f, indent=2)


def main():
    packages = find_packages()

    if REGISTRY_ROOT.exists():
        print("Cleaning existing registry...")
        for item in REGISTRY_ROOT.iterdir():
            if item.is_dir():
                for sub in item.iterdir():
                    if sub.is_dir():
                        for f in sub.rglob("*"):
                            f.unlink()
                        sub.rmdir()
                item.rmdir()

    REGISTRY_ROOT.mkdir(exist_ok=True)

    module_paths = {}

    for module, version, file_path in packages:
        module_dir = REGISTRY_ROOT / "modules" / module / version
        module_dir.mkdir(parents=True, exist_ok=True)

        write_module_bazel(module_dir / "MODULE.bazel", module, version)
        write_source_json(module_dir / "source.json", file_path)

        module_paths.setdefault(module, set()).add(version)

    # Write metadata.json
    for module, versions in module_paths.items():
        module_dir = REGISTRY_ROOT / "modules" / module
        write_metadata(module_dir, module)

    write_registry_json()
    print("Registry successfully generated at:", REGISTRY_ROOT)


if __name__ == "__main__":
    main()
