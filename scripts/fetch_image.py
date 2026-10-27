#!/usr/bin/env python3
"""从 Docker Hub 下载基础镜像并组装成 docker load 可用的 tar。

有些 NAS 连不上 docker.io，所以这里在能联网的构建机上直接走 Registry API 取 layer，
解包成标准 docker-save 格式（layer.tar 未压缩），再打进 FPK，由 install_callback 导入。

用法：
    python scripts/fetch_image.py [image] [tag] [输出文件]
    python scripts/fetch_image.py library/node 20-bookworm-slim

输出的 RepoTags 由环境变量 IMAGE_TAG 指定（默认 registry.hub.docker.com 官方名），
必须和 docker-compose.yaml 里的 image: 保持一致。
"""
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
import urllib.request

REPO = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("IMAGE_REPO", "library/node")
REF = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("IMAGE_REF", "20-bookworm-slim")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "node-20-bookworm-slim.tar")

# 默认用华为云 SWR 的 docker.io 镜像：目标 NAS 连不上 docker.io，但这个可达。
# 要改回官方名，设 IMAGE_TAG=node:20-bookworm-slim
IMAGE_TAG = os.environ.get(
    "IMAGE_TAG",
    "swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/node:20-bookworm-slim",
)

AUTH = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:%s:pull" % REPO
REG = "https://registry-1.docker.io/v2/%s" % REPO
MANIFEST_ACCEPT = ",".join([
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.index.v1+json",
])

TOKEN = {}


def get(url, accept=None):
    req = urllib.request.Request(url)
    if accept:
        req.add_header("Accept", accept)
    req.add_header("Authorization", "Bearer " + TOKEN["token"])
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def fetch_blob(digest):
    req = urllib.request.Request(
        "%s/blobs/%s" % (REG, digest),
        headers={"Authorization": "Bearer " + TOKEN["token"]})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def main():
    global TOKEN
    TOKEN = json.loads(urllib.request.urlopen(AUTH, timeout=60).read())

    m = get("%s/manifests/%s" % (REG, REF), MANIFEST_ACCEPT)
    if "manifests" in m:  # manifest list：挑 linux/amd64
        picked = None
        for entry in m["manifests"]:
            plat = entry.get("platform", {})
            if plat.get("architecture") == "amd64" and plat.get("os") == "linux" \
                    and not plat.get("variant"):
                picked = entry
        if picked is None:
            sys.exit("no amd64 manifest")
        print("manifest list ->", picked["digest"])
        m = get("%s/manifests/%s" % (REG, picked["digest"]), MANIFEST_ACCEPT)

    cfg_digest = m["config"]["digest"]
    cfg = json.loads(fetch_blob(cfg_digest))
    diff_ids = cfg["rootfs"]["diff_ids"]
    layers = m["layers"]
    if len(layers) != len(diff_ids):
        sys.exit("layer count mismatch")

    layer_files = []
    for i, (l, did) in enumerate(zip(layers, diff_ids)):
        blob = fetch_blob(l["digest"])
        try:
            raw = gzip.decompress(blob)
        except Exception:
            raw = blob
        if hashlib.sha256(raw).hexdigest() != did.replace("sha256:", ""):
            sys.exit("diff id mismatch at layer %d" % i)
        name = "%s/layer.tar" % did.replace("sha256:", "")
        layer_files.append((name, raw))
        print("layer %d: %s %.1f MB -> %.1f MB" % (
            i, l["digest"][:19], len(blob) / 1e6, len(raw) / 1e6))

    cfg_bytes = json.dumps(cfg).encode()
    cfg_name = cfg_digest.replace("sha256:", "") + ".json"
    manifest = [{
        "Config": cfg_name,
        "RepoTags": [IMAGE_TAG],
        "Layers": [n for n, _ in layer_files],
    }]

    if os.path.exists(OUT):
        os.remove(OUT)
    with tarfile.open(OUT, "w") as tf:
        def add(name, data):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
        add(cfg_name, cfg_bytes)
        add("manifest.json", json.dumps(manifest).encode())
        for n, data in layer_files:
            add(n, data)
    print("built", OUT, "%.1f MB" % (os.path.getsize(OUT) / 1e6))
    print("image tag:", IMAGE_TAG)


if __name__ == "__main__":
    main()
