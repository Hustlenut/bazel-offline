## Resources
https://mirror.bazel.build/

## Helpful commands
bazel run //tools:print_all_src_urls

## Alternative 1
Core deps clarification: mirror.bazel.build hosts ARCHIVES, BCR hosts METADATA
https://mirror.bazel.build/ = source tarballs (the actual .zip/.tar.gz files)
BCR = JSON metadata telling Bazel "use platforms@0.0.10 from this URL + SHA256"

Your MODULE.bazel (platforms, rules_cc) STILL requires BCR for metadata. The archives themselves may come from mirror.bazel.build, but Bazel first asks BCR what to download.

text
bazel_dep("platforms", "0.0.10") 
↓
Bazel → BCR: "Give me metadata for platforms@0.0.10"
↓  
BCR → "Download https://mirror.bazel.build/.../platforms-0.0.10.tar.gz (sha256=abc...)"
↓
Bazel → Downloads archive → Extracts to @platforms
What to transfer to offline machine AFTER building that MODULE.bazel:
Execute this EXACT sequence on online machine:

bash
# 1. Create minimal workspace with your MODULE.bazel
mkdir /tmp/cpp-offline-test && cd /tmp/cpp-offline-test

# Paste your exact MODULE.bazel (with rules_cc_toolchains added)
cat > MODULE.bazel << 'EOF'
module(name = "core_cpp", version = "1.0.0")
bazel_dep(name = "platforms", version = "0.0.10")
bazel_dep(name = "rules_cc", version = "0.0.10")
bazel_dep(name = "rules_cc_toolchains", version = "0.1.0")
bazel_dep(name = "googletest", version = "1.15.0")
EOF

echo "8.4.2" > .bazelversion
cat > .bazelrc << 'EOF'
common --enable_bzlmod
EOF

# Minimal BUILD file + source
mkdir src
cat > src/hello.cc << 'EOF'
#include <iostream>
#include <vector>
int main() { std::vector<int> v{1,2,3}; std::cout << v.size() << "\n"; return 0; }
EOF

cat > src/BUILD.bazel << 'EOF'
cc_binary(name = "hello", srcs = ["hello.cc"])
EOF
bash
# 2. Build → Forces ALL downloads
bazel build //src:hello
bash
# 3. HARVEST these 3 directories/files → COPY TO OFFLINE MACHINE:

# A. Repository cache (ALL downloaded archives)
REPO_CACHE=$(bazel info repository_cache)
tar czf core-deps-repo-cache.tar.gz -C "$(dirname "$REPO_CACHE")" "$(basename "$REPO_CACHE")"

# B. BCR mirror (for module metadata)
git clone https://github.com/bazelbuild/bazel-central-registry.git bcr-mirror
tar czf bcr-mirror.tar.gz bcr-mirror

# C. Your entire workspace (MODULE.bazel + source)
tar czf workspace.tar.gz .

# 4. TRANSFER these 3 files:
# core-deps-repo-cache.tar.gz (~200MB)
# bcr-mirror.tar.gz (~500MB)  
# workspace.tar.gz (~1KB)
Offline machine setup:
bash
# Extract everything
mkdir -p /opt/bazel-offline/{repo-cache,bcr}
tar xf core-deps-repo-cache.tar.gz -C /opt/bazel-offline/repo-cache
tar xf bcr-mirror.tar.gz -C /opt/bazel-offline/bcr
tar xf workspace.tar.gz

cd cpp-offline-test  # Your workspace

# Create .bazelrc pointing to local copies
cat > .bazelrc << 'EOF'
common --enable_bzlmod
common --registry=file:///opt/bazel-offline/bcr/bcr-mirror
build --repository_cache=/opt/bazel-offline/repo-cache/$(basename $(bazel info repository_cache))
EOF

# BUILD COMPLETELY OFFLINE:
bazel clean --expunge
bazel build //src:hello
bazel run //src:hello  # "3"
Summary:
You transfer:

core-deps-repo-cache.tar.gz = All tarballs (from mirror.bazel.build + everywhere)

bcr-mirror.tar.gz = BCR metadata (tells Bazel what archives exist)

workspace.tar.gz = Your MODULE.bazel + source + BUILD files

Total: ~700MB. No internet needed after transfer.​
