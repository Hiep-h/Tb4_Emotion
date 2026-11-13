#!/usr/bin/env bash
# Tải 2 model nhỏ về ~/.tb4_emotion: FER+ (nhận diện biểu cảm, 35 MB) và YuNet (tìm khuôn mặt, 0,2 MB).
# Chịu được mạng chập chờn: tự thử lại và TIẾP TỤC phần đã tải (curl -C -), kiểm tra SHA-256 cuối cùng.
# Chạy lại nhiều lần cũng được.
set -euo pipefail

DEST="${HOME}/.tb4_emotion"
mkdir -p "$DEST"

FERPLUS_FILE="emotion-ferplus-8.onnx"
FERPLUS_URL="https://media.githubusercontent.com/media/onnx/models/main/validated/vision/body_analysis/emotion_ferplus/model/${FERPLUS_FILE}"
FERPLUS_SHA="a2a2ba6a335a3b29c21acb6272f962bd3d47f84952aaffa03b60986e04efa61c"

YUNET_FILE="face_detection_yunet_2023mar.onnx"
YUNET_URL="https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/${YUNET_FILE}"
YUNET_SHA="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"

fetch() {  # name url sha
  local name="$1" url="$2" sha="$3" path="${DEST}/$1"
  if [ -f "$path" ] && echo "${sha}  ${path}" | sha256sum -c --quiet - 2>/dev/null; then
    echo "[có sẵn] ${path}"
    return
  fi
  echo "Đang tải ${name} ..."
  curl -L --fail -C - --retry 30 --retry-delay 3 --retry-all-errors --connect-timeout 20 \
       --progress-bar -o "${path}.part" "$url"
  if ! echo "${sha}  ${path}.part" | sha256sum -c --quiet - ; then
    echo "SAI SHA-256 cho ${name}: file tải lỗi, xóa và chạy lại script." >&2
    rm -f "${path}.part"
    exit 1
  fi
  mv "${path}.part" "$path"
  echo "[xong] ${path}"
}

fetch "$YUNET_FILE" "$YUNET_URL" "$YUNET_SHA"
fetch "$FERPLUS_FILE" "$FERPLUS_URL" "$FERPLUS_SHA"
echo "Xong. Chạy: ros2 launch tb4_emotion_control emotion_control.launch.py"
