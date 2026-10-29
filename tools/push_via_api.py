#!/usr/bin/env python3
"""把本地 git-tracked 文件同步到 GitHub（走 REST API，绕开 git push 的网络问题）。

只推送 `git ls-files` 的结果 —— 构建产物（site/cases、site/engine、dist、release）
因为已被 .gitignore 排除，不会误传。

用法：
  python tools/push_via_api.py            # 推送到 tbj0623/zero-dossier-office 的 main
  python tools/push_via_api.py --dry-run  # 只报告将推送的文件数

退出码 0 = 推送成功；1 = 失败。
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "tbj0623/zero-dossier-office"
BRANCH = "main"


def token() -> str:
    return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()


def api(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"https://api.github.com{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return {"__error__": exc.code, "body": exc.read().decode()[:400]}


def tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    ).stdout
    return [f for f in out.split("\n") if f.strip()]


def main() -> int:
    dry = "--dry-run" in sys.argv
    files = tracked()
    print(f"受版本控制文件：{len(files)}")
    if dry:
        return 0

    ref = api("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
    if "__error__" in ref:
        print("无法读取远端 ref：", ref, file=sys.stderr)
        return 1
    remote_sha = ref["object"]["sha"]

    entries = []
    for i, rel in enumerate(files, 1):
        content = (ROOT / rel).read_bytes()
        blob = api("POST", f"/repos/{REPO}/git/blobs", {
            "content": base64.b64encode(content).decode(),
            "encoding": "base64",
        })
        if "__error__" in blob:
            print(f"上传失败：{rel} -> {blob}", file=sys.stderr)
            return 1
        entries.append({
            "path": rel,
            "mode": "100755" if rel.endswith((".py", ".sh")) else "100644",
            "type": "blob",
            "sha": blob["sha"],
        })
        if i % 40 == 0:
            print(f"  … {i}/{len(files)}")

    # 不使用 base_tree：远端已有的、但本地未跟踪的文件会被移除（例如误提交的构建产物）
    tree = api("POST", f"/repos/{REPO}/git/trees", {"tree": entries})
    if "__error__" in tree:
        print("创建 tree 失败：", tree, file=sys.stderr)
        return 1

    message = subprocess.run(
        ["git", "log", "-1", "--format=%s"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip() or "sync"

    commit = api("POST", f"/repos/{REPO}/git/commits", {
        "message": message,
        "tree": tree["sha"],
        "parents": [remote_sha],
    })
    if "__error__" in commit:
        print("创建 commit 失败：", commit, file=sys.stderr)
        return 1

    updated = api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {
        "sha": commit["sha"],
        "force": True,
    })
    if "__error__" in updated:
        print("更新 ref 失败：", updated, file=sys.stderr)
        return 1

    print(f"OK  远端 HEAD -> {commit['sha'][:8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
