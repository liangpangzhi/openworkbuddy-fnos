#!/bin/sh
# OpenWorkBuddy 容器入口
#  1) 首次启动补齐系统依赖（python3 / git / 中文字体）——失败不影响主流程
#  2) 依赖缺失时用 npm ci 自愈
#  3) 安装时填过 API Key 就生成一份 seed 配置
set -u

DATA="${OPENWORKBUDDY_HOME:-/data}"
mkdir -p "$DATA" 2>/dev/null

echo "[owb] 数据目录: $DATA"

# --- 1. 系统依赖，只做一次 ---
if [ ! -f "$DATA/.sysdeps-ok" ]; then
    if command -v apt-get >/dev/null 2>&1; then
        echo "[owb] 首次启动：安装 python3 / git / 中文字体（可选，失败不影响使用）"
        rm -f /var/lib/apt/lists/lock 2>/dev/null
        if timeout 45 apt-get update -qq >/dev/null 2>&1; then
            if timeout 240 apt-get install -y --no-install-recommends \
                python3 python3-pip git curl ca-certificates fonts-noto-cjk >/dev/null 2>&1; then
                echo "[owb] 系统依赖就绪（python3 / git / 中文字体）"
            else
                echo "[owb] 系统依赖安装失败（网络受限），功能不受影响"
            fi
        else
            echo "[owb] apt 源不可达，跳过系统依赖"
        fi
        # 无论成功与否都只试一次：否则每次重启都要干等 apt 超时
        touch "$DATA/.sysdeps-ok"
    else
        touch "$DATA/.sysdeps-ok"
    fi
fi

# --- 2. Node 依赖自愈 ---
cd /app || exit 1
if [ ! -d /app/node_modules/express ]; then
    echo "[owb] 未找到 node_modules，正在安装依赖..."
    if ! npm ci --omit=dev --no-audit --no-fund; then
        echo "[owb] npm ci 失败，改用 npm install"
        npm install --omit=dev --no-audit --no-fund || {
            echo "[owb] 依赖安装失败，请检查 NAS 出网情况后重启应用"
            exit 1
        }
    fi
fi

# --- 3. 安装时填写的模型配置 ---
if [ -f "$DATA/ai.env" ] && [ ! -f "$DATA/.ai-seeded" ]; then
    node /app/docker-seed.js && touch "$DATA/.ai-seeded" 2>/dev/null
fi

echo "[owb] 启动 OpenWorkBuddy ..."
exec node server.js
