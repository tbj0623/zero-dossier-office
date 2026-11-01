/**
 * V7 local-only backup format. No network or solver calls.
 * Every imported field is allowlisted and every restored session is normalized.
 */
import { normalizeSavedSession } from './player-state.mjs';

export const VAULT_FORMAT = 'zero-dossier-local-backup';
export const VAULT_VERSION = 1;
export const VAULT_LIMIT_BYTES = 256 * 1024;

const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const record = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

export function normalizeProgress(value) {
  if (value == null) return null;
  if (!record(value)) throw new Error('invalid progress');
  if (Object.keys(value).some((field) => !['solved','usedHints','times','at'].includes(field)))
    throw new Error('unknown progress field');
  const out = {};
  if (own(value, 'solved')) {
    if (typeof value.solved !== 'boolean') throw new Error('invalid solved flag');
    out.solved = value.solved;
  }
  if (own(value, 'usedHints')) {
    if (typeof value.usedHints !== 'boolean') throw new Error('invalid hints flag');
    out.usedHints = value.usedHints;
  }
  if (own(value, 'times')) {
    if (!Number.isSafeInteger(value.times) || value.times < 0 || value.times > 10000)
      throw new Error('invalid completion count');
    out.times = value.times;
  }
  if (own(value, 'at')) {
    if (typeof value.at !== 'string' || value.at.length > 40
        || !Number.isFinite(Date.parse(value.at))) throw new Error('invalid completion date');
    out.at = value.at;
  }
  if (!Object.keys(out).length) throw new Error('empty progress');
  return out;
}

function canonicalSession(value, spec) {
  if (value == null) return null;
  const valid = normalizeSavedSession(value, spec.items, spec.hintCount);
  if (!valid) throw new Error('invalid saved case');
  return valid;
}

function validateCases(cases, specs) {
  if (!record(cases)) throw new Error('invalid cases');
  const output = {};
  const keys = Object.keys(cases);
  if (keys.length > Object.keys(specs).length) throw new Error('too many cases');
  for (const id of keys) {
    if (!own(specs, id)) throw new Error('unknown case');
    const entry = cases[id];
    if (!record(entry)) throw new Error('invalid case entry');
    if (Object.keys(entry).some((field) => field !== 'progress' && field !== 'session'))
      throw new Error('unknown case field');
    const normalized = {};
    if (own(entry, 'progress')) {
      const p = normalizeProgress(entry.progress);
      if (p) normalized.progress = p;
    }
    if (own(entry, 'session')) {
      const session = canonicalSession(entry.session, specs[id]);
      if (session) normalized.session = session;
    }
    if (!Object.keys(normalized).length) throw new Error('empty case entry');
    output[id] = normalized;
  }
  return output;
}

export function buildBackup(cases, specs, date = new Date().toISOString()) {
  const valid = validateCases(cases, specs);
  return {
    format: VAULT_FORMAT, version: VAULT_VERSION, exportedAt: date,
    cases: valid,
  };
}

export function parseBackup(text, specs) {
  if (typeof text !== 'string' || !text.length
      || new TextEncoder().encode(text).length > VAULT_LIMIT_BYTES)
    throw new Error('invalid backup size');
  let raw;
  try { raw = JSON.parse(text); } catch { throw new Error('not JSON'); }
  if (!record(raw) || raw.format !== VAULT_FORMAT || raw.version !== VAULT_VERSION
    || !record(raw.cases) || Object.keys(raw).some(
      (k) => !['format','version','exportedAt','cases'].includes(k)))
    throw new Error('invalid backup format');
  if (typeof raw.exportedAt !== 'string' || !Number.isFinite(Date.parse(raw.exportedAt)))
    throw new Error('invalid export date');
  return validateCases(raw.cases, specs);
}
