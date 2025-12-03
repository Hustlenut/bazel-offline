import os
import argparse

def main(registry_root, output_file):
    modules_dir = os.path.join(registry_root, "modules")

    all_modules = {}
    not_added = []

    # Walk registry/modules/<module>/<version>
    for module_name in os.listdir(modules_dir):
        module_path = os.path.join(modules_dir, module_name)
        if not os.path.isdir(module_path):
            continue

        versions = [
            version
            for version in os.listdir(module_path)
            if os.path.isdir(os.path.join(module_path, version))
        ]

        if versions:
            all_modules[module_name] = sorted(versions)
        else:
            not_added.append(module_name)

    # ---------------------------------------------
    # Write MODULE.bazel
    # ---------------------------------------------
    with open(output_file, "w") as f:
        f.write('module(name = "offline_prefetch_workspace")\n\n')

        for module_name, versions in sorted(all_modules.items()):
            for version in versions:
                f.write(f'bazel_dep(name = "{module_name}", version = "{version}")\n')

    print(f"\n✔ Written MODULE.bazel at: {output_file}")

    # ---------------------------------------------
    # Print skipped modules
    # ---------------------------------------------
    if not_added:
        print("\n⚠️  The following modules had no valid version directories and were NOT added:")
        for mod in sorted(not_added):
            print(f"  - {mod}")

        # Write them to not_added_modules.txt
        out_file = os.path.join(os.path.dirname(output_file), "not_added_modules.txt")
        with open(out_file, "w") as f:
            for mod in sorted(not_added):
                f.write(mod + "\n")

        print(f"\n⚠️  Written list of skipped modules to: {out_file}\n")
    else:
        print("\n✔ All modules successfully added to MODULE.bazel!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("registry_root")
    parser.add_argument("output_file")
    args = parser.parse_args()

    main(args.registry_root, args.output_file)
