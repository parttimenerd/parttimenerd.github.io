/**
 * jvm-tools-core.js — shared logic for the JVM Tools decision tree and search.
 *
 * Keep this file in sync with:
 *   SapMachineIOPage/src/lib/jvm-tools-core.js
 *
 * This module is framework-agnostic: no React, no Alpine, no DOM access.
 * Rendering is handled per-site; this file owns only pure logic.
 */

'use strict';

// ─── Decision tree navigation ─────────────────────────────────────────────────

/**
 * Returns a new state after navigating to a child node.
 * @param {{ cur: string, hist: Array<{id:string,label:string}> }} state
 * @param {string} nextId  — key of the target node
 * @param {string} label   — option label shown in breadcrumb
 */
export function go(state, nextId, label) {
  return { cur: nextId, hist: [...state.hist, { id: state.cur, label }] };
}

/**
 * Returns a new state after going back one step.
 */
export function back(state) {
  if (!state.hist.length) return state;
  const prev = state.hist[state.hist.length - 1];
  return { cur: prev.id, hist: state.hist.slice(0, -1) };
}

/**
 * Returns a new state after jumping to a breadcrumb at index idx.
 */
export function goTo(state, idx) {
  return { cur: state.hist[idx].id, hist: state.hist.slice(0, idx) };
}

/**
 * Returns the initial/reset state.
 */
export function reset() {
  return { cur: 'start', hist: [] };
}

// ─── Visibility persistence ───────────────────────────────────────────────────

const PF_KEY = 'pf-hidden';

export function pfHide() {
  try { localStorage.setItem(PF_KEY, '1'); } catch {}
}

export function pfShow() {
  try { localStorage.removeItem(PF_KEY); } catch {}
}

export function pfIsHidden() {
  try { return localStorage.getItem(PF_KEY) === '1'; } catch { return false; }
}

// ─── Tool search ──────────────────────────────────────────────────────────────

/**
 * Returns true if tool matches query (case-insensitive substring).
 * Searches: id, tagline, tagline_short, when_to_use[], features[].
 *
 * @param {object} tool  — a tool entry from jvm-tools.json
 * @param {string} query — the search string (empty → always true)
 */
export function matchesTool(tool, query) {
  if (!query) return true;
  const hay = [
    tool.id || '',
    tool.tagline || '',
    tool.tagline_short || '',
    ...(tool.when_to_use || []),
    ...(tool.features || []),
  ].join(' ').toLowerCase();
  return hay.includes(query.toLowerCase());
}

// ─── Build-time validation ────────────────────────────────────────────────────

const MAX_OPTIONS = 6;

/**
 * Validates a merged decision tree object.
 * Throws with a descriptive message if any question node exceeds MAX_OPTIONS.
 *
 * @param {object} tree — the merged tree (key → node)
 */
export function validateTree(tree) {
  const violations = [];
  for (const [key, node] of Object.entries(tree)) {
    if (node.type === 'question' && Array.isArray(node.options) && node.options.length > MAX_OPTIONS) {
      const labels = node.options.map(o => `'${o.label}'`).join(', ');
      violations.push(`  Node '${key}' has ${node.options.length} options (max ${MAX_OPTIONS}): ${labels}`);
    }
  }
  if (violations.length > 0) {
    throw new Error(
      `[jvm-tools] Decision tree validation failed — question nodes exceed ${MAX_OPTIONS} options:\n${violations.join('\n')}`
    );
  }
}
