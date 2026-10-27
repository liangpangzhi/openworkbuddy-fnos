#!/usr/bin/env bash
# 组装容器运行目录：上游源码 + 生产依赖 + 容器入口脚本
#
#   bash scripts/prepare-payload.sh [上游 tag，默认 v0.17.5]
#
# 产物：fpk-src/app/docker/app/（约 365MB，含 node_modules）
# 之后执行 scripts/fetch_image.py 取基础镜像，再执行 scripts/build_fpk.py 打包。
set -euo pipefail

TAG="${1:-v0.17.5}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
UPSTREAM_REPO="https://github.com/CatCatUncle/openworkbuddy.git"
APP_DIR="$ROOT/fpk-src/app/docker/app"
BUILD_DIR="$ROOT/.build"

echo "==> 上游版本: $TAG"

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR" "$BUILD_DIR/src" "$BUILD_DIR/deps"

# 1. 拉源码
if [ ! -d "$BUILD_DIR/src/.git" ]; then
    git clone --depth 1 --branch "$TAG" "$UPSTREAM_REPO" "$BUILD_DIR/src"
else
    git -C "$BUILD_DIR/src" fetch --depth 1 origin tag "$TAG" || true
    git -C "$BUILD_DIR/src" checkout -f "$TAG"
fi

# 2. 装生产依赖（放在干净目录里，避免 npm ci 清理旧 node_modules 出问题）
cp "$BUILD_DIR/src/package.json" "$BUILD_DIR/src/package-lock.json" "$BUILD_DIR/deps/"
(
    cd "$BUILD_DIR/deps"
    export ELECTRON_SKIP_BINARY_DOWNLOAD=1
    npm ci --omit=dev --no-audit --no-fund "${NPM_EXTRA_ARGS:---registry=https://registry.npmmirror.com}"
)

# 3. 拷源码（排除运行时数据、仓库元数据、文档等）
(
    cd "$BUILD_DIR/src"
    tar -cf - \
        --exclude=.git \
        --exclude=node_modules \
        --exclude=data \
        --exclude=workspace \
        --exclude=projects \
        --exclude=logs \
        --exclude=openworkbuddy-data \
        --exclude=dist \
        --exclude=config.json \
        --exclude='*.log' \
        . | (cd "$APP_DIR" && tar -xf -)
)

# 4. 拷依赖
cp -r "$BUILD_DIR/deps/node_modules" "$APP_DIR/node_modules"

# 5. 放回容器入口脚本（prepare 会清空目录，所以从仓库里拿）
cp "$ROOT/fpk-src/app/docker/docker-entrypoint.sh" "$APP_DIR/docker-entrypoint.sh"
cp "$ROOT/fpk-src/app/docker/docker-seed.js" "$APP_DIR/docker-seed.js"

echo "==> 运行目录就绪: $APP_DIR"
du -sh "$APP_DIR" 2>/dev/null || true
