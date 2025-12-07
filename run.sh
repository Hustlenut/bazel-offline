#!/usr/bin/env bash

docker run \
  -e USER="$(id -u)" \
  -u="$(id -u)" \
  -v /home/huy/workspace/bazel:/home/huy/workspace/bazel \
  -v /home/huy/workspace/bazel/bazel-offline/build_output:/tmp/build_output \
  -v /home/huy/workspace/bazel/bazel-central-registry/shared/bcr-vendor:/home/huy/workspace/bazel/bcr-vendor \
  -w $PWD \
  gcr.io/bazel-public/bazel:latest \
  --output_user_root=/tmp/build_output \
  "$@" 
