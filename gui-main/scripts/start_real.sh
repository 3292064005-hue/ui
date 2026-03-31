#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${SPINE_CORE_BUILD_DIR:-$ROOT_DIR/cpp_robot_core/build_runtime}"
CORE_BIN="$BUILD_DIR/spine_robot_core"
VENDORED_SDK_ROOT="$ROOT_DIR/third_party/rokae_xcore_sdk/robot"
SDK_ROOT="${XCORE_SDK_ROOT:-${ROKAE_SDK_ROOT:-$VENDORED_SDK_ROOT}}"
SDK_LIB_DIR="$SDK_ROOT/lib/Linux/cpp/x86_64"

python3 "$ROOT_DIR/scripts/doctor_runtime.py"

CMAKE_ARGS=(
  -S "$ROOT_DIR/cpp_robot_core"
  -B "$BUILD_DIR"
  -DXCORE_SDK_ROOT="$SDK_ROOT"
  -DROBOT_CORE_WITH_XCORE_SDK=ON
)

if [[ -f "$SDK_LIB_DIR/libxMateModel.a" ]]; then
  CMAKE_ARGS+=( -DROBOT_CORE_WITH_XMATE_MODEL=ON )
else
  CMAKE_ARGS+=( -DROBOT_CORE_WITH_XMATE_MODEL=OFF )
fi

cmake "${CMAKE_ARGS[@]}"
cmake --build "$BUILD_DIR" -j

export LD_LIBRARY_PATH="$SDK_LIB_DIR:${LD_LIBRARY_PATH:-}"
"$CORE_BIN" &
CORE_PID=$!
trap 'kill $CORE_PID >/dev/null 2>&1 || true' EXIT
sleep 1

SPINE_UI_BACKEND=core python3 "$ROOT_DIR/run.py" --backend core
