#!/usr/bin/env node
/**
 * 构建站点：
 *  1. 把 engine/solver.mjs 复制到 site/engine/solver.mjs（single source of truth）
 *  2. 把 cases/public/*.json 复制到 site/cases/*.json（只发布已过审的案卷）
 *  3. 注入 BUILD 版本串
 *
 * 用法：node tools/build.mjs [--out dist]
 * 不依赖任何 npm 包。
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync, cpSync, existsSync, readdirSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SITE = join(ROOT, 'site');
const DIST = join(ROOT, 'dist');

function sh(cmd) {
  try {
    return execSync(cmd, { cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] })
      .toString().trim();
  } catch {
    return null;
  }
}

const buildVersion = process.env.BUILD_VERSION
  || sh('git rev-parse --short HEAD')
  || new Date().toISOString().slice(0, 10);

/* 1) 校验源文件存在 */
const required = [
  join(ROOT, 'engine/solver.mjs'),
  join(SITE, 'index.html'),
  join(SITE, 'app.mjs'),
];
for (const p of required) {
  if (!existsSync(p)) {
    console.error(`缺少必需文件：${p}`);
    process.exit(1);
  }
}

/* 2) 同步求解核心 */
mkdirSync(join(SITE, 'engine'), { recursive: true });
cpSync(join(ROOT, 'engine/solver.mjs'), join(SITE, 'engine/solver.mjs'));

/* 3) 同步案件（只发布 cases/public 中在 RELEASED 白名单内的） */
const RELEASED = new Set(['NA-001', 'NA-002', 'NA-003', 'NA-004', 'NA-005', 'NA-006']);
const PUBLIC_DIR = join(ROOT, 'cases/public');
mkdirSync(join(SITE, 'cases'), { recursive: true });
let copied = 0;
for (const f of readdirSync(PUBLIC_DIR).filter((x) => x.endsWith('.json')).sort()) {
  const id = f.replace(/\.json$/, '');
  if (!RELEASED.has(id)) {
    console.log(`  · 跳过未过审案件 ${id}`);
    continue;
  }
  cpSync(join(PUBLIC_DIR, f), join(SITE, 'cases', f));
  copied += 1;
}
if (copied === 0) {
  console.error('没有可发布的案件');
  process.exit(1);
}

/* 4) 产出 dist/（源目录只读，绝不回写 site/） */
const outDir = process.env.npm_config_out ? resolve(process.env.npm_config_out) : DIST;

/**
 * 清空输出目录：先尝试删目录本身；Windows 上若目录被别的进程（如静态服务器）
 * 占住句柄，rmSync 会 EPERM。此时退化为「清空内容」——之后的 cpSync 会覆盖，
 * 少量残留也不会影响结果，且不再让整个构建失败。
 */
try {
  rmSync(outDir, { recursive: true, force: true });
} catch (err) {
  if (err && (err.code === 'EPERM' || err.code === 'EBUSY' || err.code === 'ENOTEMPTY')) {
    console.warn(`· 无法整体删除 ${outDir}（可能被其它进程占用），改为清空内容`);
    if (existsSync(outDir)) {
      for (const entry of readdirSync(outDir)) {
        try {
          rmSync(join(outDir, entry), { recursive: true, force: true });
        } catch {
          console.warn(`· 跳过被占用的 ${entry}`);
        }
      }
    }
  } else {
    throw err;
  }
}
mkdirSync(outDir, { recursive: true });
cpSync(SITE, outDir, {
  recursive: true,
  filter: (src) => {
    const rel = src.slice(SITE.length + 1).split(/[\\/]/);
    // 作者工具（案件编辑器）只留在仓库里，不随发布产物公开。
    // 需要临时带上看效果时：INCLUDE_TOOLS=1 node tools/build.mjs
    if (process.env.INCLUDE_TOOLS !== '1' && rel[0] === 'tools') return false;
    const base = rel[rel.length - 1];
    return !['node_modules', '.DS_Store', 'Thumbs.db'].includes(base);
  },
});

/* 4a) 自校验：dist 必须与 site 的每个源文件字节一致（防止占用导致静默跳过） */
const REQUIRED_TOP = ['index.html', 'app.mjs', 'styles', 'engine', 'cases', 'assets'];
for (const item of REQUIRED_TOP) {
  if (!existsSync(join(outDir, item))) {
    console.error(`构建产物缺少 ${item}`);
    process.exit(1);
  }
}

/** 递归列出目录下所有文件（相对路径）。 */
function listFiles(root, base = root) {
  const out = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const abs = join(root, entry.name);
    if (entry.isDirectory()) out.push(...listFiles(abs, base));
    else out.push(abs.slice(base.length + 1));
  }
  return out;
}

const stale = [];
for (const rel of listFiles(SITE)) {
  if (process.env.INCLUDE_TOOLS !== '1' && rel.split(/[\\/]/)[0] === 'tools') continue;
  const srcPath = join(SITE, rel);
  const dstPath = join(outDir, rel);
  if (!existsSync(dstPath)) {
    stale.push(`${rel}: 构建产物缺失`);
    continue;
  }
  const a = readFileSync(srcPath);
  const b = readFileSync(dstPath);
  // app.mjs 会被注入 BUILD 版本号，比较时忽略该行
  if (rel === 'app.mjs') {
    const norm = (buf) => buf.toString('utf8').replace(/const BUILD = '[^']*';/, 'const BUILD = X;');
    if (norm(a) !== norm(b)) stale.push(`${rel}: 与源文件不一致`);
  } else if (!a.equals(b)) {
    stale.push(`${rel}: 与源文件不一致`);
  }
}
if (stale.length) {
  console.error('构建产物与源码不一致（可能因文件被占用而跳过覆盖）：');
  for (const line of stale.slice(0, 20)) console.error('  ' + line);
  process.exit(1);
}
if (process.env.INCLUDE_TOOLS !== '1' && existsSync(join(outDir, 'tools'))) {
  console.error('发布包中出现了 site/tools/（作者工具不应公开）');
  process.exit(1);
}

/* 4a2) 发布包不得包含作者工具（防回归） */
if (process.env.INCLUDE_TOOLS !== '1' && existsSync(join(outDir, 'tools'))) {
  console.error('发布包中出现了 site/tools/（作者工具不应公开）');
  process.exit(1);
}

/* 4b) 只在 dist 副本里注入构建版本 */
const distApp = join(outDir, 'app.mjs');
const app = readFileSync(distApp, 'utf8');
if (!/const BUILD = '[^']*';/.test(app)) {
  console.error('app.mjs 中找不到 BUILD 占位符');
  process.exit(1);
}
writeFileSync(
  distApp,
  app.replace(/const BUILD = '[^']*';/, `const BUILD = '${buildVersion}';`),
  'utf8',
);

/* 4c) 把三张样式表内联进 dist/index.html
 *
 * 原来用 <link rel="preload" ... onload="this.rel='stylesheet'"> 异步加载 CSS，
 * 换取不阻塞首屏。但 Lighthouse 实测 CLS = 0.442（远超 0.1 的良好线）：
 * 样式表晚到时整页重排，正是"异步 CSS"最典型的代价。
 *
 * 站点 CSS 一共 44.6 KB（gzip 后约 9 KB），内联的代价远小于重排的代价：
 *   - 少 3 个请求、少 1 轮往返
 *   - 首帧就是最终版式，CLS 归零
 *   - 仍然没有任何第三方资源
 *
 * 只改 dist 副本，site/ 源文件保持"外链样式表"以便开发时热改。
 */
const distIndex = join(outDir, 'index.html');
let indexHtml = readFileSync(distIndex, 'utf8');
let inlinedCount = 0;
indexHtml = indexHtml.replace(
  /<link rel="preload" href="\.\/styles\/([\w-]+)\.css" as="style"[^>]*>/g,
  (match, name) => {
    const cssPath = join(outDir, 'styles', `${name}.css`);
    if (!existsSync(cssPath)) return match; // 文件不在就保留原标签，不静默丢样式
    const css = readFileSync(cssPath, 'utf8');
    inlinedCount += 1;
    return `<style data-inlined="${name}">\n${css}\n</style>`;
  },
);
if (inlinedCount !== 3) {
  console.error(`样式内联异常：只内联了 ${inlinedCount}/3 张`);
  process.exit(1);
}
writeFileSync(distIndex, indexHtml, 'utf8');
console.log(`· 已内联 ${inlinedCount} 张样式表，dist/index.html = ${(indexHtml.length / 1024).toFixed(1)} KB`);

/* 6) 自检：dist 内不得出现作者答案字段 */
const bad = [];
function scan(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name);
    if (entry.isDirectory()) { scan(p); continue; }
    if (!entry.name.endsWith('.json')) continue;
    const text = readFileSync(p, 'utf8');
    for (const field of ['expected_solution', 'editorial_note', 'logic_recap_check']) {
      if (text.includes(`"${field}"`)) bad.push(`${p} 含 ${field}`);
    }
  }
}
scan(outDir);
if (bad.length) {
  console.error('发布包泄漏内部字段：\n' + bad.join('\n'));
  process.exit(1);
}

console.log(`构建完成 · 版本 ${buildVersion} · ${copied} 个案件 · 输出 ${outDir}`);
