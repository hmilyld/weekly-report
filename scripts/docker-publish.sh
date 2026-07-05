#!/usr/bin/env bash
# ─── Docker Hub 一键发布脚本 ───────────────────────────────────
# 用法: ./scripts/docker-publish.sh [tag]
#   tag 可选，默认为 "latest"
#   会同时推送 <image>:<tag> 和 <image>:latest

set -euo pipefail

# ─── 配置 ─────────────────────────────────────────────────────
IMAGE_NAME="hmilyld/weekly-report"
TAG="${1:-latest}"
CONTAINER_NAME="weekly-report-smoke-test"

# ─── 预检查 ──────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "❌ 未找到 docker 命令，请先安装 Docker"
  exit 1
fi

# 检查是否已登录 Docker Hub
if ! docker info 2>/dev/null | grep -q "Username"; then
  echo "⚠️  未登录 Docker Hub，正在尝试登录..."
  docker login
fi

# ─── 构建 ────────────────────────────────────────────────────
echo "🔨 构建镜像 ${IMAGE_NAME}:${TAG} ..."
docker build -t "${IMAGE_NAME}:${TAG}" .

# ─── 冒烟测试 ────────────────────────────────────────────────
echo "🧪 冒烟测试 ..."
docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true
docker run -d --name "${CONTAINER_NAME}" -p 18001:18001 \
  -e JWT_SECRET_KEY=smoke-test-secret-key-12345678 \
  "${IMAGE_NAME}:${TAG}"

sleep 5
HEALTH=$(curl -sf http://localhost:18001/api/v1/health || echo "FAIL")
docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

if [[ "${HEALTH}" == *"ok"* ]]; then
  echo "✅ 冒烟测试通过"
else
  echo "❌ 冒烟测试失败: ${HEALTH}"
  exit 1
fi

# ─── 推送 ────────────────────────────────────────────────────
echo "📤 推送 ${IMAGE_NAME}:${TAG} ..."
docker push "${IMAGE_NAME}:${TAG}"

if [[ "${TAG}" != "latest" ]]; then
  docker tag "${IMAGE_NAME}:${TAG}" "${IMAGE_NAME}:latest"
  echo "📤 推送 ${IMAGE_NAME}:latest ..."
  docker push "${IMAGE_NAME}:latest"
fi

# ─── 完成 ────────────────────────────────────────────────────
echo ""
echo "✅ 发布完成！"
echo "   镜像: ${IMAGE_NAME}:${TAG}"
if [[ "${TAG}" != "latest" ]]; then
  echo "   镜像: ${IMAGE_NAME}:latest"
fi
echo ""
echo "使用方式:"
echo "   docker run -d -p 18001:18001 -v weekly-report-data:/app/data -e JWT_SECRET_KEY=your-secret ${IMAGE_NAME}:${TAG}"
