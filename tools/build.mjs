#!/usr/bin/env node
/**
 * 干净、隔离、可验证的静态站点构建。
 *
 * - 从 site/ 复制静态文件，但绝不信任其中生成的 cases/ 与 engine/
 * - 只从 cases/public/ 的固定白名单复制已审案件
 * - 在同卷临时目录构建，验证完成后再替换 dist/
 * - 旧输出无法安全移走时直接失败，不允许带残留继续发布
 *
 * 用法：node tools/build.mjs [--out dist]
 * 不依赖任何 npm 包。
 */
import {
  readFileSync, writeFileSync, mkdirSync, rmSync, cpSync, existsSync,
  readdirSync, renameSync, mkdtempSync, statSync,
} from 'node:fs';
import {
  join, dirname, resolve, relative, basename, isAbsolute,
} from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SITE = join(ROOT, 'site');
const PUBLIC_DIR = join(ROOT, 'cases', 'public');
const RELEASED_IDS = ['NA-001', 'NA-002', 'NA-003', 'NA-004', 'NA-005', 'NA-006'];
const INCLUDE_TOOLS = process.env.INCLUDE_TOOLS === '1';

function sh(cmd) {
  try {
    return execSync(cmd, { cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] })
      .toString().trim();
  } catch {
    return null;
  }
}

function getOutDir() {
  const indexes = process.argv
    .map((arg, index) => arg === '--out' ? index : -1)
    .filter((index) => index >= 0);
  if (indexes.length > 1) throw new Error('--out 只能指定一次');
  const index = indexes[0];
  if (index !== undefined && (!process.argv[index + 1] || process.argv[index + 1].startsWith('--'))) {
    throw new Error('--out 后必须提供输出目录');
  }
  const raw = index === undefined
    ? (process.env.npm_config_out || 'dist')
    : process.argv[index + 1];
  const outDir = resolve(ROOT, raw);
  const rel = relative(ROOT, outDir);
  if (!rel || rel === '..' || rel.startsWith('..\\') || isAbsolute(rel)) {
    throw new Error('输出目录必须是仓库根目录内的独立子目录');
  }
  const first = rel.split(/[\\/]/)[0].toLowerCase();
  const protectedRoots = new Set([
    '.git', 'site', 'cases', 'engine', 'tools', 'tests',
    'docs', 'work', 'review', 'release', 'ops', 'marketing',
  ]);
  if (protectedRoots.has(first)) {
    throw new Error('拒绝将构建输出写入受保护的源码/项目目录：' + rel);
  }
  return outDir;
}

function listFiles(root, base = root) {
  const out = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const abs = join(root, entry.name);
    if (entry.isDirectory()) out.push(...listFiles(abs, base));
    else out.push(abs.slice(base.length + 1));
  }
  return out;
}

function skipSiteRelative(rel) {
  const parts = rel.replace(/\\/g, '/').split('/');
  const first = parts[0];
  const base = parts[parts.length - 1];
  if (first === 'cases' || first === 'engine') return true;
  if (!INCLUDE_TOOLS && first === 'tools') return true;
  return ['node_modules', '.DS_Store', 'Thumbs.db'].includes(base);
}

function main() {
  let stageDir = null;
  try {
    const outDir = getOutDir();
    const buildVersion = process.env.BUILD_VERSION
      || sh('git rev-parse --short HEAD')
      || new Date().toISOString().slice(0, 10);
    if (!/^[A-Za-z0-9._-]{1,80}$/.test(buildVersion)) {
      throw new Error('BUILD_VERSION 只能包含字母、数字、点、下划线和连字符');
    }

    const required = [
      join(ROOT, 'engine', 'solver.mjs'),
      join(SITE, 'index.html'),
      join(SITE, 'app.mjs'),
      PUBLIC_DIR,
    ];
    for (const path of required) {
      if (!existsSync(path)) throw new Error('缺少必需文件：' + path);
    }

    const expectedNames = RELEASED_IDS.map((id) => id + '.json').sort();
    const actualNames = readdirSync(PUBLIC_DIR)
      .filter((name) => name.toLowerCase().endsWith('.json')).sort();
    const expectedSet = new Set(expectedNames);
    const extra = actualNames.filter((name) => !expectedSet.has(name));
    const missing = expectedNames.filter((name) => !actualNames.includes(name));
    if (extra.length || missing.length) {
      throw new Error(
        'cases/public 白名单不匹配；额外文件：' + (extra.join(', ') || '无')
        + '；缺失文件：' + (missing.join(', ') || '无'),
      );
    }
    for (const name of expectedNames) {
      const data = JSON.parse(readFileSync(join(PUBLIC_DIR, name), 'utf8'));
      if (!data || typeof data !== 'object' || Array.isArray(data)) {
        throw new Error('案件 JSON 结构无效：' + name);
      }
    }

    const parent = dirname(outDir);
    mkdirSync(parent, { recursive: true });
    stageDir = mkdtempSync(join(parent, '.' + basename(outDir) + '.stage-'));
    cpSync(SITE, stageDir, {
      recursive: true,
      filter: (src) => {
        if (src === SITE) return true;
        const rel = relative(SITE, src);
        return !skipSiteRelative(rel);
      },
    });

    // cases/ 与 engine/ 从可信源单独复制，完全忽略 site/ 中的旧缓存。
    mkdirSync(join(stageDir, 'engine'), { recursive: true });
    cpSync(
      join(ROOT, 'engine', 'solver.mjs'),
      join(stageDir, 'engine', 'solver.mjs'),
    );
    mkdirSync(join(stageDir, 'cases'), { recursive: true });
    for (const id of RELEASED_IDS) {
      cpSync(
        join(PUBLIC_DIR, id + '.json'),
        join(stageDir, 'cases', id + '.json'),
      );
    }

    const requiredTop = ['index.html', 'app.mjs', 'styles', 'engine', 'cases', 'assets'];
    for (const item of requiredTop) {
      if (!existsSync(join(stageDir, item))) {
        throw new Error('构建产物缺少 ' + item);
      }
    }

    const stagedCases = readdirSync(join(stageDir, 'cases')).sort();
    const stagedEngine = readdirSync(join(stageDir, 'engine')).sort();
    if (JSON.stringify(stagedCases) !== JSON.stringify(expectedNames)) {
      throw new Error('暂存目录案件集合与发布白名单不一致：' + stagedCases.join(', '));
    }
    if (JSON.stringify(stagedEngine) !== JSON.stringify(['solver.mjs'])) {
      throw new Error('暂存目录 engine/ 含有白名单外文件：' + stagedEngine.join(', '));
    }

    // 对静态站点源码逐文件核对；生成目录 cases/、engine/ 已单独验证。
    const mismatches = [];
    for (const rel of listFiles(SITE)) {
      if (skipSiteRelative(rel)) continue;
      const source = join(SITE, rel);
      const staged = join(stageDir, rel);
      if (!existsSync(staged)) {
        mismatches.push(rel + ': 暂存产物缺失');
        continue;
      }
      const a = readFileSync(source);
      const b = readFileSync(staged);
      if (rel === 'app.mjs') {
        const normalize = (buf) => buf.toString('utf8')
          .replace(/const BUILD = '[^']*';/, 'const BUILD = X;');
        if (normalize(a) !== normalize(b)) mismatches.push(rel + ': 与源码不一致');
      } else if (!a.equals(b)) {
        mismatches.push(rel + ': 与源码不一致');
      }
    }
    if (mismatches.length) {
      throw new Error('暂存产物与源码不一致：\n' + mismatches.slice(0, 20).join('\n'));
    }

    // 只在暂存副本里注入构建版本。
    const stagedApp = join(stageDir, 'app.mjs');
    const app = readFileSync(stagedApp, 'utf8');
    if (!/const BUILD = '[^']*';/.test(app)) {
      throw new Error('app.mjs 中找不到 BUILD 占位符');
    }
    writeFileSync(
      stagedApp,
      app.replace(/const BUILD = '[^']*';/, "const BUILD = '" + buildVersion + "';"),
      'utf8',
    );

    // 将三张样式表内联进暂存版 index.html，避免首屏布局偏移。
    const stagedIndex = join(stageDir, 'index.html');
    let indexHtml = readFileSync(stagedIndex, 'utf8');
    let inlinedCount = 0;
    indexHtml = indexHtml.replace(
      /<link rel="preload" href="\.\/styles\/([\w-]+)\.css" as="style"[^>]*>/g,
      (match, name) => {
        const cssPath = join(stageDir, 'styles', name + '.css');
        if (!existsSync(cssPath)) return match;
        let css = readFileSync(cssPath, 'utf8');
        css = css.replace(/url\((['"]?)\.\.\/assets\//g, 'url($1./assets/');
        inlinedCount += 1;
        return '<style data-inlined="' + name + '">\n' + css + '\n</style>';
      },
    );
    if (inlinedCount !== 3) {
      throw new Error('样式内联异常：只内联了 ' + inlinedCount + '/3 张');
    }
    writeFileSync(stagedIndex, indexHtml, 'utf8');

    // 发布产物中不得出现作者答案字段。
    const forbiddenFields = ['expected_solution', 'editorial_note', 'logic_recap_check'];
    const leaks = [];
    function scanJson(dir) {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) {
          scanJson(path);
          continue;
        }
        if (!entry.name.toLowerCase().endsWith('.json')) continue;
        const raw = readFileSync(path, 'utf8');
        for (const field of forbiddenFields) {
          if (raw.includes('"' + field + '"')) leaks.push(path + ' 含 ' + field);
        }
      }
    }
    scanJson(stageDir);
    if (leaks.length) throw new Error('发布包泄漏内部字段：\n' + leaks.join('\n'));

    if (!INCLUDE_TOOLS && existsSync(join(stageDir, 'tools'))) {
      throw new Error('发布包中出现了 site/tools/（作者工具不应公开）');
    }

    // 同卷重命名替换旧产物。旧目录若被占用，失败并保留原目录；
    // 绝不降级成逐文件覆盖，也不允许旧文件混入新发行包。
    const backupDir = outDir + '.previous-' + process.pid;
    if (existsSync(backupDir)) throw new Error('旧构建备份目录已存在，拒绝覆盖：' + backupDir);
    let movedOld = false;
    if (existsSync(outDir)) {
      if (!statSync(outDir).isDirectory()) throw new Error('输出路径已存在但不是目录：' + outDir);
      renameSync(outDir, backupDir);
      movedOld = true;
    }
    try {
      renameSync(stageDir, outDir);
      stageDir = null;
    } catch (error) {
      if (movedOld && existsSync(backupDir) && !existsSync(outDir)) {
        try {
          renameSync(backupDir, outDir);
          movedOld = false;
        } catch (restoreError) {
          console.error('严重：新产物安装失败，旧产物恢复也失败：' + restoreError.message);
        }
      }
      throw error;
    }
    if (movedOld) {
      try {
        rmSync(backupDir, { recursive: true, force: true });
      } catch (error) {
        console.warn('新产物已就位，但旧备份无法清理：' + backupDir + ' (' + error.message + ')');
      }
    }

    console.log('· 已内联 3 张样式表，index.html = '
      + (readFileSync(join(outDir, 'index.html'), 'utf8').length / 1024).toFixed(1) + ' KB');
    console.log('构建完成 · 版本 ' + buildVersion + ' · ' + RELEASED_IDS.length
      + ' 个白名单案件 · 输出 ' + outDir);
  } catch (error) {
    console.error('构建失败：' + (error && error.message ? error.message : String(error)));
    process.exitCode = 1;
  } finally {
    if (stageDir && existsSync(stageDir)) {
      try {
        rmSync(stageDir, { recursive: true, force: true });
      } catch (error) {
        console.error('暂存目录清理失败：' + stageDir + ' (' + error.message + ')');
      }
    }
  }
}

main();
