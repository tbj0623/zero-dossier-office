# itch.io 发布资料 · DRAFT_READY

**状态：`DRAFT_READY`** —— 发行包已构建并通过解压自测，但**尚未上传到 itch.io**。
上传需要用户本人的 itch.io 账户授权，本项目没有该权限，也不会代为创建账号。

---

## 1. 发行包

| 项 | 值 |
|---|---|
| 文件 | `release/itch-html5-release.zip` |
| 大小 | 0.57 MB（ZIP）/ 0.65 MB（解压） |
| 文件数 | 21（限制 1000） |
| `index.html` 位置 | **ZIP 根目录** ✅（itch.io 硬性要求） |
| 路径 | 全部相对路径，无绝对 `/` 开头 ✅ |
| 单文件最大 | < 1 MB（限制 200 MB） |
| 解压自测 | 通过：另存到临时目录独立启动静态服务器，36 项浏览器检查全 PASS，六案全部通关 |

重新构建：

```bash
node tools/build.mjs
python tools/build_itch.py
```

## 2. 上传步骤（需要用户账户）

1. itch.io → **Create new project**
2. Kind of project：**HTML**
3. 上传 `release/itch-html5-release.zip`
4. **勾选** "This file will be played in the browser"
5. Embed options：
   - Viewport：`1280 × 800`（站点自适应，也可用 `Fullscreen button`）
   - 勾选 **Fullscreen button**
   - 勾选 **Mobile friendly**（已实测 360/390/768 无溢出、目标 ≥44px）
6. 按下文填写页面字段
7. Visibility：先选 **Draft** → 自己预览确认 → 再 **Public**

> ⚠️ 首次预览时请在 itch 的 iframe 里实际点开第 001 案走一遍。itch 的 iframe 沙箱与直接访问静态站点环境不同，这一步不能省。

## 3. 页面文案（可直接粘贴）

### Title
```
第零证物局 · The Zero Dossier Office
```

### Short description / tagline（≤ 160 字符）
```
在雾港的异常档案局里，你不是找凶手，而是把互相错位的真实记录重新归位。六份档案，三幕，一次分类错误。
```

### Classification
- **Genre**：Puzzle
- **Tags**：`puzzle` `mystery` `detective` `narrative` `point-and-click` `story-rich` `chinese` `short` `free` `browser`
- **Made with**：HTML5, JavaScript
- **Average session**：A few minutes
- **Languages**：中文 (Simplified)
- **Inputs**：Mouse, Keyboard, Touchscreen
- **Accessibility**：见第 5 节

### Description（正文）

```markdown
**这些记录，不应该同时成立。**

一张车票，一封从未寄出的回信，一张什么都没拍下的底片。
你是雾港第零室的记录修复员——你的工作不是判断谁在撒谎，而是把互相错位的真实记录排回它本来的秩序。

每一案解决的都不是"魔法"，而是**对事实的误读**：一次错误的分类、一份错版的图纸、一个被当成事件的校准动作。

---

### 怎么玩

1. **读证物** —— 每张证物都写明了一种可核实的关系：先后、相邻、间距、夹在中间、固定格位。
2. **排格位** —— 点击卡片选中，再点目标格位交换；也可以用 ↑↓ 按钮。三种操作等价。
3. **提交复原** —— 系统逐条核对，只告诉你"哪些关系不符"，绝不替你排好。

卡住了？每案有三档提示：先给方法，再点出关键组合，最后给较直接的推导。**提示不会自动完成排列，也不扣分。**

### 六案 · 三幕

| 幕 | 档案 |
|---|---|
| I · 错位的开端 | 末班车的四张车票 / 封存室的四格抽屉 / 静默分拣线上的五个包裹 |
| II · 灯塔与回信 | 灯塔没有亮起的第五盏灯 / 寄不到的第五封回信 |
| III · 第零张底片 | 第零号空白底片 |

六案之间藏着一条隐形主线：反复出现的半枚「0」章。漏看不会卡关，但看完整季，你会明白它到底是什么。

### 特点

- **免费、免注册**，打开就能玩
- 单案 3–12 分钟，随时可以停下
- **手机与键盘都能完整游玩**：所有拖放操作都有等价的按钮
- **不需要联网推理**：所有判定都在你的浏览器里完成，不上传你的答案
- **结案页把"逻辑"和"故事"分开**：哪些是能从证据严格推出来的，哪些是事后补写的叙述，一目了然

### 关于公平性

这不是"作者藏了一个答案让你猜"的游戏。每一案的证据都写明了自己是哪一种关系，程序可以验证这些关系只允许一种排列。我们还请了独立解题者只看剥离答案的证物、自己推导一遍，确认文字没有第二种读法。

发现某条证物有两种理解方式？欢迎告诉我们具体编号——这会直接帮助我们修复档案。

### 声明

所有人物、地点、机构与事件均为虚构的架空世界「雾港」。本作不影射真实死者、真实机构或现存个人。

**语言**：简体中文
```

### Credits
```
设计、编程、文本与美术：第零证物局 contributors
代码许可：MIT
叙事与美术许可：CC BY-NC-SA 4.0
```

## 4. 需要的图片

| 用途 | 素材 | 尺寸建议 |
|---|---|---|
| Cover image | `site/assets/github-social-preview.png`（或另做 630×500） | itch 建议 630×500 |
| Screenshots | `docs/screenshots/01..06*.png` | 上传 5–6 张 |
| Thumbnail | `site/assets/archive-emblem-512.png` | 512×512 |

**全部使用真实运行截图**（`docs/screenshots/` 目录，从已部署站点实拍），不使用概念稿冒充游戏画面。

## 5. 可访问性声明（填写 itch 的 Accessibility 栏）

已实测：
- ✅ 键盘可完成全部操作（Tab / Enter / ↑↓ / Esc）
- ✅ 所有拖放操作都有等价按钮替代
- ✅ 交互目标 ≥ 44px（360/390/768 断点实测）
- ✅ 尊重 `prefers-reduced-motion`
- ✅ 解谜信息全部为可复制文本，不依赖图片细节
- ✅ 无自动播放音频

**未验证**，因此不声明：
- ❌ 未做屏幕阅读器（NVDA / VoiceOver）实机测试
- ❌ 未声明达到任何 WCAG 等级

## 6. 定价

**Free**。可以勾选 "Downloadable" 否 / "In browser" 是。

## 7. 上传后必须做的验证

- [ ] 在 itch 的 iframe 预览里完成第 001 案
- [ ] 手机浏览器打开 itch 页面 → 启动游戏 → 无横向滚动
- [ ] 确认无 404（图片、case JSON、solver.mjs）
- [ ] 记录真实的 itch 游戏 URL 到 `ops/CHECKPOINT.md`
