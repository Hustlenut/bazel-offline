#!/usr/bin/env bash

docker run \
  -e USER="$(id -u)" \
  -u="$(id -u)" \
  -v /<PATH>/workspace/bazel:/<PATH>/workspace/bazel \
  -v /<PATH>/workspace/bazel/bazel-offline/build_output:/tmp/build_output \
  -v /<PATH>/workspace/bazel/bazel-central-registry/shared/bcr-vendor:/<PATH>/workspace/bazel/bcr-vendor \
  -w $PWD \
  gcr.io/bazel-public/bazel:latest \
  --output_base=/<PATH>/bazel8/bazel-offline/build_output \
  "$@" 
