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
rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });
cpSync(SITE, outDir, {
  recursive: true,
  filter: (src) => {
    const base = src.split(/[\\/]/).pop();
    return !['node_modules', '.DS_Store', 'Thumbs.db'].includes(base);
  },
});

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
