import argparse
import os
import subprocess
import json
from urllib.parse import quote, urlparse

# --------------------------
# CONFIG
# --------------------------
DOWNLOAD_TIMEOUT = 120
RETRIES = 3
GITLAB_PRIVATE_TOKEN = "YOUR_TOKEN_HERE"
# --------------------------

errors = []


def safe_remove_prefix(url):
    if url.startswith("https://"):
        return url[len("https://"):]
    if url.startswith("http://"):
        return url[len("http://"):]
    return url


def is_gitlab_release_url(url):
    return "/-/releases/" in url and "/downloads/" in url


def parse_gitlab_release_url(url):
    parsed = urlparse(url)
    host = f"{parsed.scheme}://{parsed.netloc}"

    parts = parsed.path.lstrip("/").split("/")

    project_path = "/".join(parts[0:2])
    tag = parts[4]
    filename = parts[6]

    return host, project_path, tag, filename


def gitlab_get_real_asset_url(host, project_path, tag, filename):
    # Step 1: get project ID
    project_api = f"{host}/api/v4/projects/{quote(project_path, safe='')}"
    out = subprocess.check_output(
        ["curl", "-s", "-H", f"PRIVATE-TOKEN: {GITLAB_PRIVATE_TOKEN}", project_api]
    )
    project_info = json.loads(out.decode("utf-8"))
    project_id = project_info["id"]

    # Step 2: release info
    release_api = f"{host}/api/v4/projects/{project_id}/releases/{tag}"
    out = subprocess.check_output(
        ["curl", "-s", "-H", f"PRIVATE-TOKEN: {GITLAB_PRIVATE_TOKEN}", release_api]
    )
    release_info = json.loads(out.decode("utf-8"))

    for asset in release_info["assets"]["links"]:
        if asset["name"] == filename or asset["url"].endswith(filename):
            return asset["url"]

    raise Exception(f"GitLab release asset '{filename}' not found for tag {tag}")


def download_gitlab_file(real_url, output_path):
    cmd = (
        f'curl --fail --location --header "PRIVATE-TOKEN: {GITLAB_PRIVATE_TOKEN}" '
        f'-o "{output_path}" "{real_url}"'
    )
    return subprocess.call(cmd, shell=True)


def download_normal(url, output_path):
    cmd = f'wget --timeout={DOWNLOAD_TIMEOUT} -O "{output_path}" "{url}"'
    return subprocess.call(cmd, shell=True)


def main(source_file, output_dir):
    global errors

    with open(source_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            line_no_prefix = safe_remove_prefix(line)
            parts = line_no_prefix.split("/")
            full_path = "/".join(parts)
            dir_path = os.path.join(output_dir, "/".join(parts[:-1]))

            os.makedirs(dir_path, exist_ok=True)

            final_path = os.path.join(output_dir, full_path)

            if os.path.exists(final_path):
                continue

            print(f"\n=== Downloading {line} ===")
            print(f"Saving to: {final_path}\n")

            # ----- GitLab special handling -----
            if is_gitlab_release_url(line):
                try:
                    host, project_path, tag, filename = parse_gitlab_release_url(line)
                    print("Detected GitLab release asset:")
                    print(f" project = {project_path}")
                    print(f" tag     = {tag}")
                    print(f" file    = {filename}")

                    real_url = gitlab_get_real_asset_url(host, project_path, tag, filename)
                    print(f"Resolved real asset URL:\n{real_url}\n")

                    success = False
                    for attempt in range(1, RETRIES + 1):
                        print(f"Attempt {attempt}/{RETRIES}:")
                        if download_gitlab_file(real_url, final_path) == 0:
                            print("✔ GitLab download OK\n")
                            success = True
                            break
                        print("✖ Error downloading GitLab asset")

                    if not success:
                        print(f"FAILED after {RETRIES} attempts: {line}")
                        errors.append(line)

                except Exception as ex:
                    print(f"GitLab API resolution failed: {ex}")
                    errors.append(line)

                continue

            # ----- Normal URL handling -----
            success = False
            for attempt in range(1, RETRIES + 1):
                print(f"Attempt {attempt}/{RETRIES}:")
                if download_normal(line, final_path) == 0:
                    print("✔ Download OK\n")
                    success = True
                    break
                print("✖ Error downloading")

            if not success:
                print(f"FAILED after {RETRIES} attempts: {line}")
                errors.append(line)

    # Write errors.json at end
    if errors:
        with open("errors.json", "w") as err_file:
            json.dump({"errors": errors}, err_file, indent=4)
        print("\n❗ Some downloads failed. See errors.json\n")
    else:
        print("\n✔ All downloads succeeded.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("output_directory")
    args = parser.parse_args()
    main(args.input_file, args.output_directory)
