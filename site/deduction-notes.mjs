/**
 * Player-owned deduction notes. No solver reads these marks.
 * 0 = unmarked, 1 = possible, 2 = ruled out.
 * Structured storage is validated on every restoration.
 */
export const NOTE_UNKNOWN = 0;
export const NOTE_POSSIBLE = 1;
export const NOTE_EXCLUDED = 2;

export function blankNotes(n) {
  if (!Number.isInteger(n) || n < 1 || n > 8) return [];
  return Array.from({ length: n }, () => Array(n).fill(NOTE_UNKNOWN));
}

export function normalizeNotes(raw, n) {
  const fresh = blankNotes(n);
  if (!fresh.length || !Array.isArray(raw) || raw.length !== n) return fresh;
  if (!raw.every((row) => Array.isArray(row) && row.length === n
    && row.every((value) => Number.isInteger(value) && value >= 0 && value <= 2))) return fresh;
  return raw.map((row) => [...row]);
}

export function nextNote(value) {
  return value === NOTE_UNKNOWN ? NOTE_POSSIBLE
    : value === NOTE_POSSIBLE ? NOTE_EXCLUDED : NOTE_UNKNOWN;
}

export function noteCounts(notes) {
  let possible = 0;
  let excluded = 0;
  for (const row of notes) {
    for (const value of row) {
      if (value === NOTE_POSSIBLE) possible++;
      else if (value === NOTE_EXCLUDED) excluded++;
    }
  }
  return { possible, excluded };
}
