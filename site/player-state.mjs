/**
 * 第零证物局 · 玩家会话纯函数。
 * 运行时的本地存档不可信：损坏内容、跨版本内容、手动编辑都必须安全降级。
 * 保证任何可恢复状态都是本案所有物件的一次完整排列。
 */
import { normalizeNotes } from './deduction-notes.mjs';

export const HISTORY_LIMIT = 50;

export function isExactPermutation(value, items) {
  if (!Array.isArray(value) || !Array.isArray(items) || value.length !== items.length) return false;
  const remaining = new Set(items);
  if (remaining.size !== items.length) return false;
  for (const item of value) {
    if (!remaining.delete(item)) return false;
  }
  return remaining.size === 0;
}

export function normalizeSavedSession(raw, items, hintCount) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)
      || !isExactPermutation(raw.order, items)) return null;
  const safeStack = (stack) => Array.isArray(stack)
    ? stack.filter((entry) => isExactPermutation(entry, items))
      .slice(-HISTORY_LIMIT).map((entry) => [...entry])
    : [];
  const hints = Number.isInteger(raw.hintIndex)
    ? Math.max(0, Math.min(hintCount, raw.hintIndex)) : 0;
  const attempts = Number.isSafeInteger(raw.attempts) && raw.attempts >= 0
    ? Math.min(raw.attempts, 9999) : 0;
  const at = Number.isSafeInteger(raw.at) && raw.at >= 0 ? raw.at : 0;
  return {
    order: [...raw.order],
    hintIndex: hints,
    history: safeStack(raw.history),
    redo: safeStack(raw.redo),
    attempts,
    at,
    notes: normalizeNotes(raw.notes, items.length),
  };
}

export function pushUndo(history, order) {
  return [...history, [...order]].slice(-HISTORY_LIMIT);
}
