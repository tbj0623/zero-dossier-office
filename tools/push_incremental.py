#!/usr/bin/env python3
"""把本地 git-tracked 文件同步到 GitHub（走 REST API，增量推送）。

与 push_via_api.py 的区别：**只上传内容有变化的 blob**。
远端已有的文件直接复用其 sha，请求数从「文件总数」降到「改动数」。

如果远端 ref 指向的 commit 树里已有相同 sha 的文件，就跳过上传。

用法：
  python tools/push_incremental.py            # 增量推送
  python tools/push_incremental.py --dry-run  # 只报告将上传多少文件
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


_TOKEN: str | None = None


def token() -> str:
    """缓存 token —— 原来每次 api() 都起一个 `gh auth token` 子进程，几百次调用会拖到几分钟。"""
    global _TOKEN
    if _TOKEN is None:
        _TOKEN = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True
        ).stdout.strip()
    return _TOKEN


def api(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"https://api.github.com{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return {"__error__": exc.code, "body": exc.read().decode()[:400]}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    ).stdout


def remote_tree_shas(remote_sha: str) -> dict[str, str]:
    """取远端最新 commit 的整棵树：path -> blob sha（递归展开子树）。"""
    out: dict[str, str] = {}

    def walk(tree_sha: str, prefix: str) -> None:
        data = api("GET", f"/repos/{REPO}/git/trees/{tree_sha}")
        if "__error__" in data:
            return
        for entry in data.get("tree", []):
            path = f"{prefix}{entry['path']}"
            if entry["type"] == "tree":
                walk(entry["sha"], path + "/")
            else:
                out[path] = entry["sha"]

    commit = api("GET", f"/repos/{REPO}/git/commits/{remote_sha}")
    if "__error__" in commit:
        return out
    walk(commit["tree"]["sha"], "")
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv

    files = [f for f in git("ls-files").split("\n") if f.strip()]
    print(f"受版本控制文件：{len(files)}")

    ref = api("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
    if "__error__" in ref:
        print("无法读取远端 ref：", ref, file=sys.stderr)
        return 1
    remote_sha = ref["object"]["sha"]

    print("读取远端树…")
    remote = remote_tree_shas(remote_sha)
    print(f"远端已有文件：{len(remote)}")

    # 必须用 git 对象库里的 blob，而不是工作树文件：
    # 仓库开了 autocrlf，工作树是 CRLF、blob 是 LF，两者 sha 不同。
    # `git rev-parse HEAD:path` 给出规范 blob sha，`git cat-file blob` 给出其字节。
    to_upload: list[str] = []
    entries: list[dict] = []
    for rel in files:
        local_sha = git("rev-parse", f"HEAD:{rel}").strip()
        if not local_sha:
            # 文件未入库（不应发生，ls-files 只列已跟踪）
            to_upload.append(rel)
            continue
        if remote.get(rel) == local_sha:
            entries.append({
                "path": rel, "mode": "100755" if rel.endswith((".py", ".sh")) else "100644",
                "type": "blob", "sha": local_sha,
            })
        else:
            to_upload.append(rel)

    print(f"需要上传：{len(to_upload)} 个（复用 {len(entries)} 个）")
    if dry:
        for rel in to_upload[:30]:
            print("  " + rel)
        return 0

    for i, rel in enumerate(to_upload, 1):
        # 从 git 对象库取，保证字节与 sha 一致（避免 CRLF 问题）
        content = subprocess.run(
            ["git", "cat-file", "blob", f"HEAD:{rel}"],
            cwd=ROOT, capture_output=True,
        ).stdout
        blob = api("POST", f"/repos/{REPO}/git/blobs", {
            "content": base64.b64encode(content).decode(),
            "encoding": "base64",
        })
        if "__error__" in blob:
            print(f"上传失败：{rel} -> {blob}", file=sys.stderr)
            return 1
        entries.append({
            "path": rel, "mode": "100755" if rel.endswith((".py", ".sh")) else "100644",
            "type": "blob", "sha": blob["sha"],
        })
        if i % 25 == 0:
            print(f"  … {i}/{len(to_upload)}")

    # 不用 base_tree：远端已删除/未跟踪的文件要能被移除
    tree = api("POST", f"/repos/{REPO}/git/trees", {"tree": entries})
    if "__error__" in tree:
        print("创建 tree 失败：", tree, file=sys.stderr)
        return 1

    message = git("log", "-1", "--format=%s").strip() or "sync"
    commit = api("POST", f"/repos/{REPO}/git/commits", {
        "message": message, "tree": tree["sha"], "parents": [remote_sha],
    })
    if "__error__" in commit:
        print("创建 commit 失败：", commit, file=sys.stderr)
        return 1

    updated = api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {
        "sha": commit["sha"], "force": True,
    })
    if "__error__" in updated:
        print("更新 ref 失败：", updated, file=sys.stderr)
        return 1

    print(f"OK  远端 HEAD -> {commit['sha'][:8]}  (上传 {len(to_upload)} 个文件)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
