# Tree Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a visual in-browser editor for the `problem-finder.yaml` decision tree to the `/jvm-tools/` page, with SVG diagram, structured edit forms, validation, and YAML clipboard export.

**Architecture:** Hugo embeds the tree as JSON at build time; an Alpine component (`treeEditor()`) reads it on mount, manages all state reactively, renders an SVG flow diagram, and handles YAML serialization + validation. No new npm dependencies. Export is clipboard-only (static site).

**Tech Stack:** Hugo Go templates, Alpine.js v3, Tailwind CSS v3 (existing classes only), plain SVG

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `themes/projects-theme/assets/js/tree-editor.js` | **Create** | `treeEditor()` factory: state, init, diagram layout, edit mutations, validation, YAML serialization |
| `themes/projects-theme/assets/js/main.js` | **Modify** (2 lines) | Import `treeEditor` and expose on `window` before `Alpine.start()` |
| `themes/projects-theme/layouts/partials/problem-finder-editor.html` | **Create** | Hugo partial: embed tree JSON + tool IDs JSON, render editor shell HTML |
| `themes/projects-theme/layouts/collection/list.html` | **Modify** (2 lines) | Include `problem-finder-editor.html` after the widget include |

---

## Task 1: Register `treeEditor` in main.js

**Files:**
- Modify: `themes/projects-theme/assets/js/main.js:1` (add import at top, add registration before `Alpine.start()`)
- Create: `themes/projects-theme/assets/js/tree-editor.js` (skeleton only — full implementation in Task 2)

- [ ] **Step 1: Create the skeleton JS file**

Create `/Users/i560383_1/code/experiments/parttimenerd.github.io/themes/projects-theme/assets/js/tree-editor.js` with:

```js
export function treeEditor() {
  return {
    nodes: {},
    nodeOrder: [],
    selected: null,
    errors: [],
    copied: false,
    svgNodes: [],
    svgEdges: [],
    svgWidth: 800,
    svgHeight: 500,

    init() {
      const raw = JSON.parse(document.getElementById('pf-tree-data')?.textContent || '{}');
      this.nodes = raw;
      this.nodeOrder = Object.keys(raw);
      this.layoutDiagram();
    },

    layoutDiagram() {
      this.svgNodes = [];
      this.svgEdges = [];
    },
  };
}
```

- [ ] **Step 2: Import and register in main.js**

Open `themes/projects-theme/assets/js/main.js`. Add one import at the very top and one registration line just before `Alpine.start()`:

```js
import Alpine from 'alpinejs';
import focus from '@alpinejs/focus';
import { treeEditor } from './tree-editor.js';   // ← add this line
import hljs from 'highlight.js/lib/core';
// ... rest of imports unchanged ...

Alpine.plugin(focus);
window.Alpine = Alpine;
window.treeEditor = treeEditor;                   // ← add this line
Alpine.start();
```

- [ ] **Step 3: Verify Hugo builds cleanly**

```bash
hugo --source /Users/i560383_1/code/experiments/parttimenerd.github.io --quiet 2>&1
```

Expected: no output (clean build).

- [ ] **Step 4: Commit**

```bash
git -C /Users/i560383_1/code/experiments/parttimenerd.github.io \
  add themes/projects-theme/assets/js/tree-editor.js \
      themes/projects-theme/assets/js/main.js
git -C /Users/i560383_1/code/experiments/parttimenerd.github.io \
  commit -m "feat: register treeEditor Alpine component skeleton"
```

---

## Task 2: Implement `treeEditor()` — init, diagram layout, add/delete nodes

**Files:**
- Modify: `themes/projects-theme/assets/js/tree-editor.js` (full implementation)

This task implements the core Alpine component. It's large but all in one file. Write it completely — no placeholders.

- [ ] **Step 1: Replace tree-editor.js with the full implementation**

Replace the entire contents of `themes/projects-theme/assets/js/tree-editor.js` with:

```js
export function treeEditor() {
  return {
    // ── State ──────────────────────────────────────────────────────────────
    nodes: {},
    nodeOrder: [],
    selected: null,
    errors: [],
    copied: false,
    _deleteConfirm: null,   // id of node awaiting delete confirmation
    _deleteTimer: null,

    svgNodes: [],
    svgEdges: [],
    svgWidth: 800,
    svgHeight: 500,

    // drag state for option reordering
    _dragIdx: null,

    // ── Init ───────────────────────────────────────────────────────────────
    init() {
      const raw = JSON.parse(document.getElementById('pf-tree-data')?.textContent || '{}');
      // Deep-clone so we can mutate freely
      this.nodes = JSON.parse(JSON.stringify(raw));
      this.nodeOrder = Object.keys(this.nodes);
      this.layoutDiagram();
    },

    // ── Diagram layout (BFS top-down) ──────────────────────────────────────
    layoutDiagram() {
      const NODE_W = 160, NODE_H = 50, H_GAP = 40, V_GAP = 30, PAD = 20;

      // BFS from 'start'
      const levels = {};   // id → depth
      const queue = ['start'];
      const visited = new Set();
      levels['start'] = 0;
      while (queue.length) {
        const id = queue.shift();
        if (visited.has(id)) continue;
        visited.add(id);
        const node = this.nodes[id];
        if (!node) continue;
        const depth = levels[id];
        if (node.type === 'question') {
          for (const opt of (node.options || [])) {
            if (opt.next && !(opt.next in levels)) {
              levels[opt.next] = depth + 1;
              queue.push(opt.next);
            }
          }
        }
      }

      // Group by depth
      const byDepth = {};
      for (const [id, depth] of Object.entries(levels)) {
        (byDepth[depth] = byDepth[depth] || []).push(id);
      }

      // Orphans (not reachable from 'start')
      const orphans = this.nodeOrder.filter(id => !(id in levels));

      // Assign x (column = depth * (NODE_W + H_GAP))
      // Assign y (row within depth = index * (NODE_H + V_GAP))
      const positions = {};
      const maxDepth = byDepth && Object.keys(byDepth).length
        ? Math.max(...Object.keys(byDepth).map(Number))
        : 0;

      for (const [depth, ids] of Object.entries(byDepth)) {
        const col = Number(depth);
        ids.forEach((id, row) => {
          positions[id] = {
            x: PAD + col * (NODE_W + H_GAP),
            y: PAD + row * (NODE_H + V_GAP),
          };
        });
      }

      // Orphans in an extra column to the right
      const orphanCol = maxDepth + 1;
      orphans.forEach((id, row) => {
        positions[id] = {
          x: PAD + orphanCol * (NODE_W + H_GAP),
          y: PAD + row * (NODE_H + V_GAP),
        };
      });

      // Build svgNodes
      this.svgNodes = this.nodeOrder
        .filter(id => id in positions)
        .concat(orphans.filter(id => !(id in positions)))
        .map(id => {
          const node = this.nodes[id];
          const pos = positions[id] || { x: PAD, y: PAD };
          const label = node
            ? (node.type === 'question' ? node.text : node.headline) || id
            : id;
          return {
            id,
            x: pos.x,
            y: pos.y,
            w: NODE_W,
            h: NODE_H,
            type: node?.type || 'question',
            label: label.length > 22 ? label.slice(0, 21) + '…' : label,
          };
        });

      // Build svgEdges
      this.svgEdges = [];
      for (const id of this.nodeOrder) {
        const node = this.nodes[id];
        if (node?.type !== 'question') continue;
        const src = positions[id];
        if (!src) continue;
        for (const opt of (node.options || [])) {
          if (!opt.next || !positions[opt.next]) continue;
          const dst = positions[opt.next];
          const edgeLabel = opt.label
            ? (opt.label.length > 18 ? opt.label.slice(0, 17) + '…' : opt.label)
            : '';
          this.svgEdges.push({
            x1: src.x + NODE_W / 2,
            y1: src.y + NODE_H,
            x2: dst.x + NODE_W / 2,
            y2: dst.y,
            label: edgeLabel,
          });
        }
      }

      // Compute canvas size
      let maxX = 0, maxY = 0;
      for (const n of this.svgNodes) {
        maxX = Math.max(maxX, n.x + NODE_W + PAD);
        maxY = Math.max(maxY, n.y + NODE_H + PAD);
      }
      this.svgWidth = Math.max(maxX, 400);
      this.svgHeight = Math.max(maxY, 300);
    },

    selectNode(id) {
      this.selected = id;
    },

    // ── Add nodes ──────────────────────────────────────────────────────────
    _uniqueId(prefix) {
      let n = 1;
      while (this.nodes[`${prefix}${n}`]) n++;
      return `${prefix}${n}`;
    },

    addQuestion() {
      const id = this._uniqueId('q-new-');
      this.nodes[id] = { type: 'question', text: '', options: [] };
      this.nodeOrder.push(id);
      this.selected = id;
      this.layoutDiagram();
    },

    addResult() {
      const id = this._uniqueId('r-new-');
      this.nodes[id] = { type: 'result', headline: '', tools: [] };
      this.nodeOrder.push(id);
      this.selected = id;
      this.layoutDiagram();
    },

    // ── Delete node ────────────────────────────────────────────────────────
    requestDelete(id) {
      if (this._deleteConfirm === id) {
        // Second click — confirm
        clearTimeout(this._deleteTimer);
        this._deleteConfirm = null;
        this._doDelete(id);
      } else {
        this._deleteConfirm = id;
        this._deleteTimer = setTimeout(() => {
          this._deleteConfirm = null;
        }, 2000);
      }
    },

    _doDelete(id) {
      // Remove dangling next references
      for (const nid of this.nodeOrder) {
        const n = this.nodes[nid];
        if (n?.type === 'question') {
          n.options = (n.options || []).filter(o => o.next !== id);
        }
      }
      delete this.nodes[id];
      this.nodeOrder = this.nodeOrder.filter(i => i !== id);
      if (this.selected === id) this.selected = null;
      this.layoutDiagram();
    },

    // ── Option mutations ───────────────────────────────────────────────────
    addOption(nodeId) {
      this.nodes[nodeId].options = [
        ...(this.nodes[nodeId].options || []),
        { label: '', next: '' },
      ];
      this.layoutDiagram();
    },

    removeOption(nodeId, idx) {
      this.nodes[nodeId].options.splice(idx, 1);
      this.layoutDiagram();
    },

    // drag-and-drop option reorder
    dragStart(idx) {
      this._dragIdx = idx;
    },

    dragOver(e) {
      e.preventDefault();
    },

    dropOption(nodeId, targetIdx) {
      if (this._dragIdx === null || this._dragIdx === targetIdx) return;
      const opts = this.nodes[nodeId].options;
      const moved = opts.splice(this._dragIdx, 1)[0];
      opts.splice(targetIdx, 0, moved);
      this._dragIdx = null;
      this.layoutDiagram();
    },

    // ── Tool mutations (primary tools, followon tools, related group tools) ─
    addTool(toolList) {
      toolList.push({ id: '', section: 'jvm-tools', note: '' });
    },

    removeTool(toolList, idx) {
      toolList.splice(idx, 1);
    },

    // ── Follow-on toggle ───────────────────────────────────────────────────
    toggleFollowon(nodeId) {
      const node = this.nodes[nodeId];
      if (node.followon) {
        delete node.followon;
      } else {
        node.followon = { heading: '', tools: [] };
      }
    },

    // ── Related groups ─────────────────────────────────────────────────────
    addRelatedGroup(nodeId) {
      const node = this.nodes[nodeId];
      node.related = [...(node.related || []), { label: '', tools: [] }];
    },

    removeRelatedGroup(nodeId, idx) {
      this.nodes[nodeId].related.splice(idx, 1);
    },

    // ── Validation ─────────────────────────────────────────────────────────
    validate() {
      const errs = [];
      const ids = new Set(this.nodeOrder);

      if (!this.nodes['start']) {
        errs.push("Missing required 'start' node");
      }

      for (const id of this.nodeOrder) {
        const node = this.nodes[id];
        if (!node) continue;

        if (node.type === 'question') {
          if (!node.text?.trim()) errs.push(`Question "${id}" has no text`);
          if (!node.options?.length) errs.push(`Question "${id}" has no options`);
          (node.options || []).forEach((opt, i) => {
            if (!opt.label?.trim()) errs.push(`Option #${i + 1} in "${id}" has an empty label`);
            if (!opt.next?.trim()) errs.push(`Option "${opt.label || '#' + (i+1)}" in "${id}" has no target (set the → dropdown)`);
            else if (!ids.has(opt.next)) errs.push(`Option "${opt.label}" in node "${id}" points to "${opt.next}" which doesn't exist`);
          });
        }

        if (node.type === 'result') {
          if (!node.headline?.trim()) errs.push(`Result "${id}" has no headline`);
          if (!node.tools?.length) errs.push(`Result "${id}" has no tools`);
          (node.tools || []).forEach((t, i) => {
            if (!t.id?.trim()) errs.push(`Tool #${i + 1} in result "${id}" has no ID`);
          });
          if (node.followon) {
            if (!node.followon.heading?.trim()) errs.push(`Follow-on in "${id}" has no heading`);
            if (!node.followon.tools?.length) errs.push(`Follow-on in "${id}" has no tools`);
          }
          (node.related || []).forEach((grp, i) => {
            if (!grp.label?.trim()) errs.push(`Related group #${i + 1} in "${id}" has no label`);
            if (!grp.tools?.length) errs.push(`Related group "${grp.label || '#' + (i+1)}" in "${id}" has no tools`);
          });
        }
      }

      this.errors = errs;
      return errs.length === 0;
    },

    // ── YAML serialization ─────────────────────────────────────────────────
    yamlStr(s) {
      if (s === null || s === undefined) return "''";
      const str = String(s);
      if (!str) return "''";
      // Quote if contains YAML-special chars or leading/trailing whitespace
      if (/[:#'"&*?|>{}\[\]!]/.test(str) || /^\s|\s$/.test(str)) {
        // Use double quotes; escape internal double quotes and backslashes
        return '"' + str.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
      }
      return str;
    },

    serializeYaml() {
      const lines = [
        '# Decision tree for the "Have a problem?" widget on /jvm-tools/',
        '# Each key is a node ID. Two types: question (shows options) and result (shows tools).',
        '# To add a tool: add a result node and wire an option in the relevant question to it.',
        '# Start node is always "start".',
        '# Optional result fields: followon (next steps), related (alternative paths).',
        '# Tools may specify section: experiments|femto to link outside jvm-tools.',
        '',
      ];

      const questions = this.nodeOrder.filter(id => this.nodes[id]?.type === 'question');
      const results   = this.nodeOrder.filter(id => this.nodes[id]?.type === 'result');

      // Ensure start is first
      const qOrdered = ['start', ...questions.filter(id => id !== 'start')];

      for (const id of qOrdered) {
        const node = this.nodes[id];
        if (!node) continue;
        lines.push(`${id}:`);
        lines.push(`  type: question`);
        lines.push(`  text: ${this.yamlStr(node.text)}`);
        lines.push(`  options:`);
        for (const opt of (node.options || [])) {
          lines.push(`    - label: ${this.yamlStr(opt.label)}`);
          lines.push(`      next: ${opt.next || "''"}`);
        }
        lines.push('');
      }

      if (results.length) {
        lines.push('# ── Result nodes ──────────────────────────────────────────────────────────────────');
        lines.push('');
        for (const id of results) {
          const node = this.nodes[id];
          if (!node) continue;
          lines.push(`${id}:`);
          lines.push(`  type: result`);
          lines.push(`  headline: ${this.yamlStr(node.headline)}`);
          lines.push(`  tools:`);
          for (const t of (node.tools || [])) {
            lines.push(`    - id: ${t.id || "''"}`);
            if (t.section && t.section !== 'jvm-tools') lines.push(`      section: ${t.section}`);
            if (t.note?.trim()) lines.push(`      note: ${this.yamlStr(t.note)}`);
          }
          if (node.followon) {
            lines.push(`  followon:`);
            lines.push(`    heading: ${this.yamlStr(node.followon.heading)}`);
            lines.push(`    tools:`);
            for (const t of (node.followon.tools || [])) {
              lines.push(`      - id: ${t.id || "''"}`);
              if (t.section && t.section !== 'jvm-tools') lines.push(`        section: ${t.section}`);
              if (t.note?.trim()) lines.push(`        note: ${this.yamlStr(t.note)}`);
            }
          }
          if (node.related?.length) {
            lines.push(`  related:`);
            for (const grp of node.related) {
              lines.push(`    - label: ${this.yamlStr(grp.label)}`);
              lines.push(`      tools:`);
              for (const t of (grp.tools || [])) {
                lines.push(`        - id: ${t.id || "''"}`);
                if (t.section && t.section !== 'jvm-tools') lines.push(`          section: ${t.section}`);
                if (t.note?.trim()) lines.push(`          note: ${this.yamlStr(t.note)}`);
              }
            }
          }
          lines.push('');
        }
      }

      return lines.join('\n');
    },

    // ── Copy YAML to clipboard ─────────────────────────────────────────────
    copyYaml() {
      if (!this.validate()) return;
      const yaml = this.serializeYaml();
      navigator.clipboard.writeText(yaml).then(() => {
        this.copied = true;
        setTimeout(() => { this.copied = false; }, 2000);
      });
    },
  };
}
```

- [ ] **Step 2: Verify the JS module imports cleanly (Hugo esbuild)**

```bash
hugo --source /Users/i560383_1/code/experiments/parttimenerd.github.io --quiet 2>&1
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git -C /Users/i560383_1/code/experiments/parttimenerd.github.io \
  add themes/projects-theme/assets/js/tree-editor.js
git -C /Users/i560383_1/code/experiments/parttimenerd.github.io \
  commit -m "feat: implement treeEditor Alpine component (state, diagram, mutations, validation, YAML export)"
```

---

## Task 3: Create the Hugo partial (`problem-finder-editor.html`)

**Files:**
- Create: `themes/projects-theme/layouts/partials/problem-finder-editor.html`

This partial renders the editor shell HTML. All Alpine bindings call methods defined in `treeEditor()`. Hugo embeds the data as JSON; Alpine reads it on `x-init`.

- [ ] **Step 1: Create the partial**

Create `/Users/i560383_1/code/experiments/parttimenerd.github.io/themes/projects-theme/layouts/partials/problem-finder-editor.html` with:

```html
{{/* ─────────────────────────────────────────────────────────────────────────
     problem-finder-editor.html
     Visual editor for the decision tree. Edit in-browser, export YAML,
     paste into data/jvm-tools/problem-finder.yaml and rebuild.
     ───────────────────────────────────────────────────────────────────────── */}}

{{ $tree    := index site.Data "jvm-tools" "problem-finder" }}
{{ $toolIds := slice }}
{{ range site.Data.jvm_tools.static    }}{{ $toolIds = $toolIds | append .id }}{{ end }}
{{ range site.Data.femto.static        }}{{ $toolIds = $toolIds | append .id }}{{ end }}
{{ range site.Data.experiments.static  }}{{ $toolIds = $toolIds | append .id }}{{ end }}

{{/* Embed data as JSON for the Alpine component to read on init */}}
<script type="application/json" id="pf-tree-data">{{ $tree | jsonify }}</script>
<datalist id="pf-tool-ids">
  {{ range $toolIds }}<option value="{{ . }}">{{ end }}
</datalist>

<div
  x-data="treeEditor()"
  x-init="init()"
  class="mt-16 border-t-2 border-dashed border-gray-200 pt-8 pb-16"
>

  {{/* ── Header ─────────────────────────────────────────────────────────── */}}
  <div class="mb-2">
    <h2 class="font-['Vollkorn'] text-xl font-bold text-gray-900">Tree Editor</h2>
    <p class="text-xs text-gray-400 mt-0.5">Edit below, then Copy YAML and paste into <code class="font-mono">data/jvm-tools/problem-finder.yaml</code> and rebuild.</p>
  </div>

  {{/* ── Toolbar ─────────────────────────────────────────────────────────── */}}
  <div class="flex flex-wrap items-center gap-2 mb-4">
    <button @click="addQuestion()"
      class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
      + New question
    </button>
    <button @click="addResult()"
      class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
      + New result
    </button>
    <div class="ml-auto flex items-center gap-2">
      <template x-if="errors.length > 0">
        <span class="text-xs text-red-600" x-text="errors.length + ' error(s) — fix before copying'"></span>
      </template>
      <button @click="copyYaml()"
        :class="copied ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'"
        class="px-4 py-1.5 text-sm text-white rounded-lg transition-colors">
        <span x-text="copied ? 'Copied! ✓' : 'Copy YAML ▸'"></span>
      </button>
    </div>
  </div>

  {{/* ── Validation errors ───────────────────────────────────────────────── */}}
  <template x-if="errors.length > 0">
    <div class="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
      <p class="font-semibold mb-1">Fix these errors before exporting:</p>
      <ul class="list-disc list-inside space-y-0.5">
        <template x-for="err in errors" :key="err">
          <li x-text="err"></li>
        </template>
      </ul>
    </div>
  </template>

  {{/* ── Split: diagram + edit panel ────────────────────────────────────── */}}
  <div class="grid grid-cols-1 md:grid-cols-2 gap-0 border border-gray-200 rounded-xl overflow-hidden">

    {{/* ── Diagram panel ─────────────────────────────────────────────────── */}}
    <div class="bg-gray-50 p-4 overflow-auto min-h-[500px] border-b md:border-b-0 md:border-r border-gray-200">
      <p class="text-xs font-bold text-gray-400 uppercase tracking-wide mb-3">Diagram — click a node to edit</p>
      <svg
        :width="svgWidth"
        :height="svgHeight"
        class="block"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#9ca3af"/>
          </marker>
        </defs>

        {{/* Edges */}}
        <template x-for="edge in svgEdges" :key="edge.x1 + ',' + edge.y1 + ',' + edge.x2 + ',' + edge.y2">
          <g>
            <line
              :x1="edge.x1" :y1="edge.y1"
              :x2="edge.x2" :y2="edge.y2"
              stroke="#9ca3af" stroke-width="1.5"
              marker-end="url(#arrow)"
            />
            <text
              :x="(edge.x1 + edge.x2) / 2 + 4"
              :y="(edge.y1 + edge.y2) / 2"
              fill="#6b7280" font-size="10"
              x-text="edge.label"
            ></text>
          </g>
        </template>

        {{/* Nodes */}}
        <template x-for="n in svgNodes" :key="n.id">
          <g @click="selectNode(n.id)" class="cursor-pointer">
            <rect
              :x="n.x" :y="n.y" :width="n.w" :height="n.h"
              rx="6" fill="white"
              :stroke="n.type === 'question' ? '#3b82f6' : '#22c55e'"
              :stroke-width="selected === n.id ? 3 : 1.5"
            />
            <text
              :x="n.x + n.w / 2"
              :y="n.y + 16"
              text-anchor="middle"
              font-size="11" font-weight="600"
              :fill="n.type === 'question' ? '#1d4ed8' : '#15803d'"
              x-text="n.id"
            ></text>
            <text
              :x="n.x + n.w / 2"
              :y="n.y + 32"
              text-anchor="middle"
              font-size="10" fill="#6b7280"
              x-text="n.label"
            ></text>
          </g>
        </template>
      </svg>
    </div>

    {{/* ── Edit panel ────────────────────────────────────────────────────── */}}
    <div class="bg-white p-5 overflow-y-auto min-h-[500px]">
      <template x-if="!selected">
        <p class="text-sm text-gray-400 italic mt-4">Click a node in the diagram to edit it.</p>
      </template>

      <template x-if="selected && nodes[selected]">
        <div>
          {{/* Node header */}}
          <div class="flex items-center gap-3 mb-4">
            <span class="font-mono text-sm font-bold text-gray-800" x-text="selected"></span>
            <span
              x-text="nodes[selected].type"
              :class="nodes[selected].type === 'question' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'"
              class="text-xs font-semibold px-2 py-0.5 rounded-full"
            ></span>
            <button
              @click="requestDelete(selected)"
              :class="_deleteConfirm === selected ? 'text-red-600 font-semibold' : 'text-red-400 hover:text-red-600'"
              class="ml-auto text-xs transition-colors"
              x-text="_deleteConfirm === selected ? 'Sure?' : 'Delete node'"
            ></button>
          </div>

          {{/* ── Question fields ──────────────────────────────────────── */}}
          <template x-if="nodes[selected].type === 'question'">
            <div>
              <label class="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1 block">Question text</label>
              <textarea rows="2"
                x-model="nodes[selected].text"
                @input="layoutDiagram()"
                class="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400 mb-4 resize-none"
              ></textarea>

              <label class="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2 block">Options</label>
              <ul class="space-y-2 mb-2">
                <template x-for="(opt, idx) in nodes[selected].options" :key="idx">
                  <li
                    class="flex items-center gap-2 p-2 bg-gray-50 rounded border border-gray-100"
                    draggable="true"
                    @dragstart="dragStart(idx)"
                    @dragover="dragOver($event)"
                    @drop="dropOption(selected, idx)"
                  >
                    <span class="cursor-grab text-gray-300 select-none text-base">≡</span>
                    <input type="text"
                      x-model="opt.label"
                      placeholder="Option label"
                      class="flex-1 border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400"
                    />
                    <span class="text-gray-400 text-xs shrink-0">→</span>
                    <select
                      x-model="opt.next"
                      @change="layoutDiagram()"
                      class="border border-gray-200 rounded px-1 py-1 text-sm focus:outline-none focus:border-blue-400"
                    >
                      <option value="">— choose —</option>
                      <template x-for="nid in nodeOrder" :key="nid">
                        <option :value="nid" :selected="opt.next === nid" x-text="nid"></option>
                      </template>
                    </select>
                    <button @click="removeOption(selected, idx)"
                      class="text-xs text-red-400 hover:text-red-600 shrink-0">✕</button>
                  </li>
                </template>
              </ul>
              <button @click="addOption(selected)"
                class="text-xs text-blue-600 hover:underline">+ add option</button>
            </div>
          </template>

          {{/* ── Result fields ────────────────────────────────────────── */}}
          <template x-if="nodes[selected].type === 'result'">
            <div>
              <label class="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1 block">Headline</label>
              <textarea rows="2"
                x-model="nodes[selected].headline"
                @input="layoutDiagram()"
                class="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400 mb-4 resize-none"
              ></textarea>

              {{/* Primary tools */}}
              <label class="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2 block">Tools</label>
              <div class="space-y-2 mb-2">
                <template x-for="(tool, idx) in nodes[selected].tools" :key="idx">
                  <div class="bg-gray-50 rounded border border-gray-100 p-2 space-y-1">
                    <div class="flex items-center gap-2">
                      <label class="text-xs text-gray-500 w-8 shrink-0">ID</label>
                      <input type="text" list="pf-tool-ids"
                        x-model="tool.id"
                        placeholder="tool-id"
                        class="flex-1 border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400"
                      />
                      <label class="text-xs text-gray-500 shrink-0">Section</label>
                      <select x-model="tool.section"
                        class="border border-gray-200 rounded px-1 py-1 text-sm focus:outline-none focus:border-blue-400">
                        <option value="jvm-tools">jvm-tools</option>
                        <option value="femto">femto</option>
                        <option value="experiments">experiments</option>
                      </select>
                      <button @click="removeTool(nodes[selected].tools, idx)"
                        class="text-xs text-red-400 hover:text-red-600 shrink-0">✕</button>
                    </div>
                    <div class="flex items-center gap-2">
                      <label class="text-xs text-gray-500 w-8 shrink-0">Note</label>
                      <input type="text"
                        x-model="tool.note"
                        placeholder="optional one-line note"
                        class="flex-1 border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400"
                      />
                    </div>
                  </div>
                </template>
              </div>
              <button @click="addTool(nodes[selected].tools)"
                class="text-xs text-blue-600 hover:underline mb-5">+ add tool</button>

              {{/* Follow-on */}}
              <div class="border-t border-gray-100 pt-4 mt-2 mb-4">
                <label class="flex items-center gap-2 cursor-pointer mb-3">
                  <input type="checkbox"
                    :checked="!!nodes[selected].followon"
                    @change="toggleFollowon(selected)"
                    class="rounded"
                  />
                  <span class="text-xs font-bold text-gray-500 uppercase tracking-wide">Follow-on callout</span>
                </label>
                <template x-if="nodes[selected].followon">
                  <div class="pl-4 border-l-2 border-blue-100 space-y-2">
                    <input type="text"
                      x-model="nodes[selected].followon.heading"
                      placeholder="Follow-on heading"
                      class="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400"
                    />
                    <div class="space-y-2">
                      <template x-for="(tool, idx) in nodes[selected].followon.tools" :key="idx">
                        <div class="bg-blue-50 rounded border border-blue-100 p-2 space-y-1">
                          <div class="flex items-center gap-2">
                            <label class="text-xs text-gray-500 w-8 shrink-0">ID</label>
                            <input type="text" list="pf-tool-ids"
                              x-model="tool.id"
                              placeholder="tool-id"
                              class="flex-1 border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400"
                            />
                            <label class="text-xs text-gray-500 shrink-0">Section</label>
                            <select x-model="tool.section"
                              class="border border-gray-200 rounded px-1 py-1 text-sm focus:outline-none focus:border-blue-400">
                              <option value="jvm-tools">jvm-tools</option>
                              <option value="femto">femto</option>
                              <option value="experiments">experiments</option>
                            </select>
                            <button @click="removeTool(nodes[selected].followon.tools, idx)"
                              class="text-xs text-red-400 hover:text-red-600 shrink-0">✕</button>
                          </div>
                          <div class="flex items-center gap-2">
                            <label class="text-xs text-gray-500 w-8 shrink-0">Note</label>
                            <input type="text"
                              x-model="tool.note"
                              placeholder="optional note"
                              class="flex-1 border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400"
                            />
                          </div>
                        </div>
                      </template>
                    </div>
                    <button @click="addTool(nodes[selected].followon.tools)"
                      class="text-xs text-blue-600 hover:underline">+ add follow-on tool</button>
                  </div>
                </template>
              </div>

              {{/* Related groups */}}
              <div class="border-t border-gray-100 pt-4">
                <p class="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">Related callouts</p>
                <template x-for="(grp, gIdx) in (nodes[selected].related || [])" :key="gIdx">
                  <div class="bg-amber-50 border border-amber-100 rounded-lg p-3 mb-3">
                    <div class="flex items-center gap-2 mb-2">
                      <input type="text"
                        x-model="grp.label"
                        placeholder="Related group label"
                        class="flex-1 border border-amber-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-amber-400"
                      />
                      <button @click="removeRelatedGroup(selected, gIdx)"
                        class="text-xs text-red-400 hover:text-red-600 shrink-0">✕ remove</button>
                    </div>
                    <div class="space-y-2 mb-2">
                      <template x-for="(tool, tIdx) in grp.tools" :key="tIdx">
                        <div class="bg-white rounded border border-amber-100 p-2 space-y-1">
                          <div class="flex items-center gap-2">
                            <label class="text-xs text-gray-500 w-8 shrink-0">ID</label>
                            <input type="text" list="pf-tool-ids"
                              x-model="tool.id"
                              placeholder="tool-id"
                              class="flex-1 border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400"
                            />
                            <label class="text-xs text-gray-500 shrink-0">Section</label>
                            <select x-model="tool.section"
                              class="border border-gray-200 rounded px-1 py-1 text-sm focus:outline-none focus:border-blue-400">
                              <option value="jvm-tools">jvm-tools</option>
                              <option value="femto">femto</option>
                              <option value="experiments">experiments</option>
                            </select>
                            <button @click="removeTool(grp.tools, tIdx)"
                              class="text-xs text-red-400 hover:text-red-600 shrink-0">✕</button>
                          </div>
                          <div class="flex items-center gap-2">
                            <label class="text-xs text-gray-500 w-8 shrink-0">Note</label>
                            <input type="text"
                              x-model="tool.note"
                              placeholder="optional note"
                              class="flex-1 border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-400"
                            />
                          </div>
                        </div>
                      </template>
                    </div>
                    <button @click="addTool(grp.tools)"
                      class="text-xs text-blue-600 hover:underline">+ add tool</button>
                  </div>
                </template>
                <button @click="addRelatedGroup(selected)"
                  class="text-xs text-blue-600 hover:underline">+ add related group</button>
              </div>

            </div>
          </template>
        </div>
      </template>
    </div>{{/* end edit panel */}}

  </div>{{/* end split grid */}}

</div>{{/* end x-data */}}
```

- [ ] **Step 2: Verify Hugo builds cleanly**

```bash
hugo --source /Users/i560383_1/code/experiments/parttimenerd.github.io --quiet 2>&1
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git -C /Users/i560383_1/code/experiments/parttimenerd.github.io \
  add themes/projects-theme/layouts/partials/problem-finder-editor.html
git -C /Users/i560383_1/code/experiments/parttimenerd.github.io \
  commit -m "feat: add problem-finder-editor Hugo partial"
```

---

## Task 4: Wire the editor into `list.html`

**Files:**
- Modify: `themes/projects-theme/layouts/collection/list.html:35-36`

Currently lines 34-36 read:
```html
  {{/* Problem finder decision tree — jvm-tools only */}}
  {{ if eq .Section "jvm-tools" }}{{ partial "problem-finder.html" . }}{{ end }}

  {{/* Sticky anchor nav */}}
```

- [ ] **Step 1: Insert the editor include**

Open `themes/projects-theme/layouts/collection/list.html` and add two lines immediately after the existing widget include:

```html
  {{/* Problem finder decision tree — jvm-tools only */}}
  {{ if eq .Section "jvm-tools" }}{{ partial "problem-finder.html" . }}{{ end }}

  {{/* Problem finder editor — jvm-tools only */}}
  {{ if eq .Section "jvm-tools" }}{{ partial "problem-finder-editor.html" . }}{{ end }}

  {{/* Sticky anchor nav */}}
```

- [ ] **Step 2: Verify Hugo builds cleanly**

```bash
hugo --source /Users/i560383_1/code/experiments/parttimenerd.github.io --quiet 2>&1
```

Expected: no output.

- [ ] **Step 3: Check editor appears in built HTML**

```bash
grep -c "treeEditor\|pf-tree-data\|Tree Editor" \
  /tmp/hugo-preview/jvm-tools/index.html 2>/dev/null || \
hugo --source /Users/i560383_1/code/experiments/parttimenerd.github.io \
  --destination /tmp/hugo-preview --quiet 2>&1 && \
grep -c "treeEditor\|pf-tree-data\|Tree Editor" \
  /tmp/hugo-preview/jvm-tools/index.html
```

Expected: a number ≥ 3 (treeEditor registration, pf-tree-data script, "Tree Editor" heading).

- [ ] **Step 4: Check editor is NOT on femto/experiments pages**

```bash
grep "treeEditor\|pf-tree-data" \
  /tmp/hugo-preview/femto/index.html \
  /tmp/hugo-preview/experiments/index.html 2>/dev/null \
  && echo "FAIL: editor leaked to other pages" \
  || echo "OK: editor not present on other pages"
```

Expected: `OK: editor not present on other pages`

- [ ] **Step 5: Commit**

```bash
git -C /Users/i560383_1/code/experiments/parttimenerd.github.io \
  add themes/projects-theme/layouts/collection/list.html
git -C /Users/i560383_1/code/experiments/parttimenerd.github.io \
  commit -m "feat: include tree editor on jvm-tools page"
```

---

## Task 5: Manual verification in the browser

**Files:** none (verification only)

- [ ] **Step 1: Start dev server**

```bash
hugo serve --source /Users/i560383_1/code/experiments/parttimenerd.github.io \
  --disableFastRender --port 1313
```

Navigate to `http://localhost:1313/jvm-tools/`. Scroll past the decision tree widget. The editor should appear below a dashed separator line.

- [ ] **Step 2: Verify diagram renders**

The SVG diagram should show boxes for all 24 nodes (7 questions + 17 results). Question nodes have blue borders, result nodes have green borders. `start` is visible in the top-left area.

- [ ] **Step 3: Click a question node to edit**

Click `start` in the diagram. The right panel should show:
- ID: `start` (read-only)
- Type badge: `question` (blue)
- Text textarea pre-filled: "What problem are you trying to solve?"
- 6 option rows, each showing label text and a `→` dropdown

- [ ] **Step 4: Click a result node to edit**

Click `r-jstall` in the diagram. The right panel should show:
- ID: `r-jstall` (read-only)
- Headline pre-filled
- Tools list with 1 entry (jstall, with note)
- Follow-on checkbox checked (shows heading + condensed-data + jfr-query)
- Related section with 1 group

- [ ] **Step 5: Test Copy YAML with clean tree**

Click "Copy YAML ▸". No errors should appear. Paste into a text editor and verify:
- Starts with the comment block
- `start:` is first
- Questions come before results
- `r-jfr-visual` has a `followon:` block
- `r-execjar` has a `related:` block with femtojar with `section: femto`
- YAML is parseable: `python3 -c "import yaml; yaml.safe_load(open('/dev/stdin'))"` with the pasted content

- [ ] **Step 6: Test validation errors**

Click `start` in diagram. Delete the text in the "Question text" field. Click "Copy YAML ▸". Should see red error panel: `Question "start" has no text`. Restore the text. Click again — error clears, YAML copies.

- [ ] **Step 7: Test add + delete question node**

Click "+ New question". A node `q-new-1` appears in the diagram (right column if unreachable). Right panel shows empty text field and no options. Click "+ add option" — an option row appears. Delete the node: click "Delete node", wait for "Sure?", click again. Node disappears from diagram.

- [ ] **Step 8: Test option reorder**

Click `start` in diagram. Drag the second option ("My JVM crashed…") above the first ("My app is slow…") using the ≡ handle. Verify the order changes in the list.

- [ ] **Step 9: Test that femto/experiments pages are unaffected**

Navigate to `http://localhost:1313/femto/` — no editor should appear. Same for `http://localhost:1313/experiments/`.

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Hugo embeds tree as JSON (`pf-tree-data` script tag) | Task 3 |
| Hugo embeds tool IDs as `<datalist>` | Task 3 |
| `treeEditor()` registered on `window` | Task 1 |
| State: `nodes`, `nodeOrder`, `selected`, `errors`, `copied`, `svgNodes`, `svgEdges` | Task 2 |
| `init()` reads JSON, populates state, calls `layoutDiagram()` | Task 2 |
| BFS diagram layout from `start` | Task 2 |
| Orphan nodes in right column | Task 2 |
| Question nodes: blue border; result nodes: green border | Task 3 (SVG) |
| Selected node: thicker stroke | Task 3 (SVG) |
| Edge labels truncated to 18 chars | Task 2 |
| Node labels truncated to 22 chars | Task 2 |
| Click node → selects, populates edit panel | Task 3 |
| Add question / add result with unique ID | Task 2 |
| Delete with two-click confirmation | Task 2 |
| Delete cleans up dangling `next` refs | Task 2 |
| Option drag-and-drop reorder | Task 2 + 3 |
| Question: text field, options list, add/remove option, `→` dropdown | Task 3 |
| Result: headline, tools (id/section/note), follow-on toggle, related groups | Task 3 |
| Tool ID `<datalist>` autocomplete | Task 3 |
| All 13 validation rules | Task 2 |
| Validation blocks export | Task 2 |
| Errors shown in red panel | Task 3 |
| YAML serializer: comment header, start first, questions then results | Task 2 |
| YAML serializer: quoting rules | Task 2 |
| Copy to clipboard + "Copied!" feedback | Task 2 + 3 |
| Editor only on jvm-tools page | Task 4 |
| Mobile stacked layout | Task 3 (grid-cols-1 md:grid-cols-2) |

**Placeholder scan:** None found. All code is complete in every step.

**Type consistency:**
- `addTool(toolList)` called with `nodes[selected].tools`, `nodes[selected].followon.tools`, `grp.tools` — all are arrays, consistent.
- `removeTool(toolList, idx)` same pattern.
- `dropOption(nodeId, targetIdx)` matches `dragStart(idx)` — both use array indices.
- `layoutDiagram()` called explicitly after every mutation — consistent throughout.
- `_deleteConfirm` and `_deleteTimer` used in `requestDelete()` and displayed in the template — consistent.
