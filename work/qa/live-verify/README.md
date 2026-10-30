# 线上站点验证记录（GitHub Pages / itch.io）

本目录保存的是**对公开线上站的实跑记录**，不是本地 `dist/` 的结果。
区别很重要：本地构建通过 ≠ 线上可访问、≠ 线上部署的产物与仓库一致。

建立于 2026-10-30 上线后验收整改，回应验收报告"补验门槛"第 4 条：
> 有可复现的当前站点测试日志与双平台真实可访问证据。

---

## 1. GitHub Pages 全量回归

| 项 | 值 |
|---|---|
| 被测地址 | `https://tbj0623.github.io/zero-dossier-office/` |
| 测试脚本 | `tests/browser/e2e.py`（仓库内既有脚本，未为本次验证改动） |
| 命令 | `python tests/browser/e2e.py --base "https://tbj0623.github.io/zero-dossier-office/"` |
| 执行时间 | 2026-10-30T12:50(+0800) |
| 结果 | **38 / 38 PASS，六案 6/6 通关** |
| 原始报告 | `pages-live-report.json`（`base` 字段即被测 URL，可直接核对不是本地） |

覆盖到的要点：

- 首页 / 档案柜 6 案 / NA-001 完整纵切（证据展开、错误反馈、三级提示、结案两段复盘）
- 归档进度写入与刷新恢复
- **六案逐一实玩通关**（用 UI 按钮排列，不走作弊接口）
- 键盘全流程（Tab / Enter / 方向键 / 焦点轮廓）
- **手机与平板 360 / 390 / 768 三档无横向溢出，交互目标 ≥ 44px**
- `prefers-reduced-motion`、图片失败降级
- **第三方网络请求 0 个**、控制台错误 0 条

## 2. itch.io 托管实例回归

| 项 | 值 |
|---|---|
| 被测地址 | `https://tbj0623.itch.io/zero-dossier-office` |
| 测试脚本 | `tests/browser/test_itch_live.py`（匿名访客上下文，未登录） |
| 命令 | `python tests/browser/test_itch_live.py` |
| 结果 | **20 / 20 PASS，六案 6/6 通关** |
| 原始报告 | `../../screenshots/itch-live-report.json` |

真正的被测对象是 itch CDN 里的 iframe：
`https://html-classic.itch.zone/html/20141202/index.html?v=17` —— 即 itch 重新托管后的发行包，
不是本地 iframe 模拟。

## 3. 为什么 GitHub Pages 的报告不覆盖 `screenshots/browser-report.json`

`screenshots/browser-report.json` 记录的是**本地 `dist/` + `127.0.0.1:8080`** 的 CI 同款运行，
是"构建产物本身是否正确"。本目录的 `pages-live-report.json` 是"线上部署是否可用"。
两者口径不同，都需要保留，所以本次验证把线上结果单独存到这里，没有覆盖前者。

## 4. 复跑方式

```bash
cd zero-dossier-office

# 线上 Pages（约 60–90 秒，会写 screenshots/ 下的 PNG 与 browser-report.json）
python tests/browser/e2e.py --base "https://tbj0623.github.io/zero-dossier-office/"

# 线上 itch.io（约 3–4 分钟，六案逐个通关）
python tests/browser/test_itch_live.py
```

> 注意：直接跑上面第一条会覆盖 `screenshots/browser-report.json`（它是本地口径的报告）。
> 若只想留存线上记录而不动本地报告，跑完把报告复制到本目录再
> `git checkout -- screenshots/browser-report.json` 还原即可——本次就是这么做的。
