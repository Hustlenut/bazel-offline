## Resources
https://mirror.bazel.build/

## Helpful commands
bazel run //tools:print_all_src_urls

## Introduction
This project aims to test out how difficult it is to take Bazels BCR fully offline.

**Core deps clarification:** mirror.bazel.build hosts ARCHIVES, BCR hosts METADATA
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
Execute this EXACT sequence on online machine...

#### 1. create a workspace somewhere else
```git clone git@github.com:Hustlenut/cpp-offline-test.git```
#### 2. clone the BCR into this project and stand in it
```git clone https://github.com/bazelbuild/bazel-central-registry.git```
#### 3. print out all deps
```../run.sh run //tools:print_all_src_urls > o.txt```
__This o.txt lists all the superficial deps of BCR, not the transitive ones. And we dont need all to test, so use the cpp_modules.txt i included in this project.__
#### 4. download
```download_modules.py cpp_modules.txt packages```
__packages contains just the tarballs__
#### 5. then build a new minimal offline registry
```python build_offline_repo_cache.py```
#### 6. try to build the cpp-offline-test project
```cd <path>/cpp-offline-test```
```../<path>/bazel-offline/run.sh build //...```
__TODO: Where I am today - Bazel can have transitive dependencies inside each of its MODULE.bazel files that is in each dependency from BCR. Look inside the 'offline_cache' output from the ```python build_offline_repo_cache.py```. I believe each MODULE.bazel file might make Bazel dynamically pull down repos to handle nested dependencies, hence the '+' repos:__
```
../bazel-offline/run.sh build //...
Starting local Bazel server (8.4.2) and connecting to it...
Computing main repo mapping: 
Loading: 
Loading: 0 packages loaded
INFO: Repository rules_shell+ instantiated at:
  <builtin>: in <toplevel>
Repository rule http_archive defined at:
  /tmp/build_output/30d53c91d337c7e4a6e9b9ac2bb21cdc/external/bazel_tools/tools/build_defs/repo/http.bzl:431:31: in <toplevel>
INFO: Repository protobuf+ instantiated at:
  <builtin>: in <toplevel>
Repository rule http_archive defined at:
  /tmp/build_output/30d53c91d337c7e4a6e9b9ac2bb21cdc/external/bazel_tools/tools/build_defs/repo/http.bzl:431:31: in <toplevel>
INFO: Repository rules_java+ instantiated at:
  <builtin>: in <toplevel>
Repository rule http_archive defined at:
  /tmp/build_output/30d53c91d337c7e4a6e9b9ac2bb21cdc/external/bazel_tools/tools/build_defs/repo/http.bzl:431:31: in <toplevel>
INFO: Repository rules_python+ instantiated at:
  <builtin>: in <toplevel>
Repository rule http_archive defined at:
  /tmp/build_output/30d53c91d337c7e4a6e9b9ac2bb21cdc/external/bazel_tools/tools/build_defs/repo/http.bzl:431:31: in <toplevel>
ERROR: /tmp/build_output/30d53c91d337c7e4a6e9b9ac2bb21cdc/external/bazel_tools/tools/build_defs/repo/http.bzl:155:45: An error occurred during the fetch of repository 'rules_shell+':
   Traceback (most recent call last):
	File "/tmp/build_output/30d53c91d337c7e4a6e9b9ac2bb21cdc/external/bazel_tools/tools/build_defs/repo/http.bzl", line 155, column 45, in _http_archive_impl
		download_info = ctx.download_and_extract(
Error in download_and_extract: java.io.IOException: Failed to download repository @@rules_shell+: download is disabled.
WARNING: Target pattern parsing failed.
ERROR: Skipping '//...': error loading package under directory '': no such package '@@rules_shell+//shell': java.io.IOException: Failed to download repository @@rules_shell+: download is disabled.
ERROR: error loading package under directory '': no such package '@@rules_shell+//shell': java.io.IOException: Failed to download repository @@rules_shell+: download is disabled.
INFO: Elapsed time: 2.591s
INFO: 0 processes.
ERROR: Build did NOT complete successfully
```
