#!/bin/bash
# Docker 构建脚本，自动获取版本号

set -e

# 获取版本号：yyyyMMdd-commit
VERSION=$(date +%Y%m%d)-$(git rev-parse --short HEAD)
echo "Building with version: $VERSION"

# 导出版本号环境变量
export APP_VERSION=$VERSION

# 构建 Docker 镜像
docker compose build

echo "Build complete! Version: $VERSION"
