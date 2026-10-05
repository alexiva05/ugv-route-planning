#!/usr/bin/env bash
# Run the Isaac Lab GUI tutorial with the File menu enabled.
set -euo pipefail

isaaclab_dir="${ISAACLAB_PATH:-/workspace/isaaclab}"
isaacsim_dir="${ISAACSIM_ROOT_PATH:-/isaac-sim}"

cd "$isaaclab_dir"
exec "$isaacsim_dir/python.sh" scripts/tutorials/00_sim/create_empty.py \
  --viz kit --kit_args="--enable omni.kit.menu.file"
