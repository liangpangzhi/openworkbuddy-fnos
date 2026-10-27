#!/usr/bin/env python3
"""fnOS FPK 构建：fnpack 打包 + 修正生命周期脚本的可执行位。

fnpack 在 Windows 上打出的 fpk 里，cmd/* 的 mode 是 0666，
飞牛直接执行这些脚本会 Permission denied，所以这里重写一遍外层 tar，
把 cmd/* 和 *.sh 设成 0755。

用法：
    python scripts/build_fpk.py [源目录] [输出文件名]
    FNPACK=/path/to/fnpack python scripts/build_fpk.py
"""
import os
import re
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SRC = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "fpk-src")
FNPACK = os.environ.get("FNPACK") or os.path.join(ROOT, "fnpack.exe")


def read_version(src):
    try:
        with open(os.path.join(src, "manifest"), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("version="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "0.0.0"


def main():
    if not os.path.isdir(SRC):
        sys.exit(f"source not found: {SRC}")
    if not (os.path.exists(FNPACK) or _which(FNPACK)):
        sys.exit("fnpack not found; set FNPACK=/path/to/fnpack or put it in repo root")

    r = subprocess.run([FNPACK, "build", "--directory", SRC], cwd=ROOT,
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        sys.exit("fnpack build failed")

    produced = os.path.join(ROOT, os.path.basename(SRC) + ".fpk")
    if not os.path.exists(produced):
        sys.exit(f"fnpack output not found: {produced}")

    version = read_version(SRC)
    out = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else \
        os.path.join(ROOT, f"openworkbuddy-{version}.fpk")

    tmp = out + ".tmp"
    with tarfile.open(produced, "r:gz") as src, tarfile.open(tmp, "w:gz", compresslevel=6) as dst:
        for m in src:
            if m.name.startswith("cmd/") or m.name.endswith(".sh"):
                m.mode = 0o755
                m.uid = 0
                m.gid = 0
                m.uname = "root"
                m.gname = "root"
            dst.addfile(m, src.extractfile(m) if m.isfile() else None)

    if os.path.exists(out):
        os.remove(out)
    os.replace(tmp, out)
    os.remove(produced)
    print(f"built {out}  {os.path.getsize(out)/1024/1024:.1f} MB")


def _which(cmd):
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, cmd)
        if os.path.exists(p):
            return p
    return None


if __name__ == "__main__":
    main()
