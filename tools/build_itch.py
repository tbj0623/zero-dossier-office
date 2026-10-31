#!/usr/bin/env python3
"""构建并验证 itch.io HTML5 发行包。

ZIP 根目录必须包含 index.html；案件文件必须严格等于已发布白名单。
先写临时 ZIP 并完整回读验证，成功后才原子替换旧发行包。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
ZIP_PATH = RELEASE / "itch-html5-release.zip"
MANIFEST_PATH = RELEASE / "RELEASE_MANIFEST.json"

RELEASED_IDS = ("NA-001", "NA-002", "NA-003", "NA-004", "NA-005", "NA-006")
EXPECTED_CASES = tuple(sorted(f"{case_id}.json" for case_id in RELEASED_IDS))
FORBIDDEN_FIELDS = {"expected_solution", "editorial_note", "logic_recap_check"}

MAX_FILES = 1000
MAX_TOTAL = 500 * 1024 * 1024
MAX_SINGLE = 200 * 1024 * 1024

# 这些仓库展示素材不属于游戏运行时。
EXCLUDE = {
    "assets/readme-hero.png",
    "assets/github-social-preview.png",
    "assets/archive-desk-background.webp",
    "status.html",  # GitHub Pages 状态页，不属于 itch 游戏本体
}


def forbidden_keys(value, location="$"):
    """返回 JSON 中所有作者侧字段路径，递归检查而非只查顶层。"""
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{location}.{key}"
            if key in FORBIDDEN_FIELDS:
                found.append(child_path)
            found.extend(forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(forbidden_keys(child, f"{location}[{index}]"))
    return found


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not (DIST / "index.html").is_file():
        print("先运行 node tools/build.mjs 生成 dist/", file=sys.stderr)
        return 1

    cases_dir = DIST / "cases"
    if not cases_dir.is_dir():
        print("发行目录缺少 cases/", file=sys.stderr)
        return 1
    actual_cases = tuple(sorted(path.name for path in cases_dir.iterdir()))
    if actual_cases != EXPECTED_CASES:
        print(
            "发行目录案件集合与白名单不一致："
            f"期望 {list(EXPECTED_CASES)}，实际 {list(actual_cases)}",
            file=sys.stderr,
        )
        return 1

    for case_name in EXPECTED_CASES:
        try:
            case_data = json.loads((cases_dir / case_name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"案件 JSON 无法读取：{case_name}: {error}", file=sys.stderr)
            return 1
        if not isinstance(case_data, dict):
            print(f"案件 JSON 顶层必须是对象：{case_name}", file=sys.stderr)
            return 1
        leaks = forbidden_keys(case_data)
        if leaks:
            print(f"案件 {case_name} 含作者侧字段：{', '.join(leaks)}", file=sys.stderr)
            return 1

    app_text = (DIST / "app.mjs").read_text(encoding="utf-8")
    version_match = re.search(r"const BUILD = '([^']+)';", app_text)
    if not version_match:
        print("dist/app.mjs 缺少 BUILD 版本标记", file=sys.stderr)
        return 1
    build_version = version_match.group(1)

    RELEASE.mkdir(parents=True, exist_ok=True)
    files = []
    for path in DIST.rglob("*"):
        if path.is_symlink():
            print(f"发行目录不允许符号链接：{path.relative_to(DIST)}", file=sys.stderr)
            return 1
        if not path.is_file():
            continue
        relative = path.relative_to(DIST).as_posix()
        if relative not in EXCLUDE:
            files.append((relative, path))
    files.sort(key=lambda item: item[0])
    total = sum(path.stat().st_size for _, path in files)

    if len(files) > MAX_FILES:
        print(f"文件数 {len(files)} 超过 {MAX_FILES}", file=sys.stderr)
        return 1
    if total > MAX_TOTAL:
        print(f"总体积 {total / 1024 / 1024:.1f}MB 超过限制", file=sys.stderr)
        return 1
    for relative, path in files:
        if path.stat().st_size > MAX_SINGLE:
            print(f"单文件过大：{relative}", file=sys.stderr)
            return 1

    tmp_zip = RELEASE / f".{ZIP_PATH.stem}.{os.getpid()}.tmp.zip"
    tmp_manifest = RELEASE / f".{MANIFEST_PATH.stem}.{os.getpid()}.tmp.json"
    if tmp_zip.exists() or tmp_manifest.exists():
        print("临时发行文件已存在，拒绝覆盖", file=sys.stderr)
        return 1

    try:
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, path in files:
                archive.write(path, relative)

        with zipfile.ZipFile(tmp_zip, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("ZIP 中存在重复路径")
            if "index.html" not in names:
                raise ValueError("ZIP 根目录缺少 index.html")
            excluded_in_zip = sorted(set(names) & EXCLUDE)
            if excluded_in_zip:
                raise ValueError(f"ZIP 混入非游戏文件：{excluded_in_zip}")
            bad = [
                name for name in names
                if "\\" in name or PurePosixPath(name).is_absolute()
                or ".." in PurePosixPath(name).parts
            ]
            if bad:
                raise ValueError(f"ZIP 存在绝对路径或路径穿越：{bad[:5]}")
            if any(name.startswith("tools/") or name.startswith("cases/author/") for name in names):
                raise ValueError("ZIP 中包含作者工具或作者案件目录")
            zip_cases = tuple(sorted(
                name.removeprefix("cases/")
                for name in names
                if name.startswith("cases/") and name.endswith(".json")
            ))
            if zip_cases != EXPECTED_CASES:
                raise ValueError(f"ZIP 案件集合不正确：{list(zip_cases)}")
            corrupt = archive.testzip()
            if corrupt:
                raise ValueError(f"ZIP CRC 校验失败：{corrupt}")
            for name in names:
                if not name.lower().endswith(".json"):
                    continue
                try:
                    data = json.loads(archive.read(name).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ValueError(f"ZIP JSON 无法解析：{name}: {error}") from error
                leaks = forbidden_keys(data)
                if leaks:
                    raise ValueError(f"ZIP JSON 泄漏作者字段：{name}: {', '.join(leaks)}")

        zip_bytes = tmp_zip.stat().st_size
        zip_sha256 = sha256_file(tmp_zip)
        manifest_data = {
            "itch_zip": ZIP_PATH.name,
            "build_version": build_version,
            "case_ids": list(RELEASED_IDS),
            "files": len(files),
            "uncompressed_bytes": total,
            "zip_bytes": zip_bytes,
            "zip_sha256": zip_sha256,
            "index_at_root": True,
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        tmp_manifest.write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        # os.replace 在 Windows 上遇到文件占用会失败，并保留旧包。
        os.replace(tmp_zip, ZIP_PATH)
        os.replace(tmp_manifest, MANIFEST_PATH)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"发行包构建/验证失败：{error}", file=sys.stderr)
        return 1
    finally:
        for temporary in (tmp_zip, tmp_manifest):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    size_mb = ZIP_PATH.stat().st_size / 1024 / 1024
    print(f"OK  itch 包：{ZIP_PATH}")
    print(f"    文件 {len(files)} 个 · 解压 {total / 1024 / 1024:.2f} MB · ZIP {size_mb:.2f} MB")
    print(f"    BUILD {build_version} · SHA-256 {zip_sha256}")
    print("    6 个白名单案件 · index.html 位于 ZIP 根目录 · CRC 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
