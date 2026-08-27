export function treeEditor() {
  return {
    // ── State ──────────────────────────────────────────────────────────────
    nodes: {},
    nodeOrder: [],
    selected: null,
    errors: [],
    copied: false,
    _deleteConfirm: null,
    _deleteTimer: null,

    svgNodes: [],
    svgEdges: [],
    svgWidth: 800,
    svgHeight: 500,

    _dragIdx: null,

    // ── Init ───────────────────────────────────────────────────────────────
    init() {
      const raw = JSON.parse(document.getElementById('pf-tree-data')?.textContent || '{}');
      this.nodes = JSON.parse(JSON.stringify(raw));
      this.nodeOrder = Object.keys(this.nodes);
      this.layoutDiagram();
    },

    // ── Diagram layout (BFS top-down) ──────────────────────────────────────
    layoutDiagram() {
      const NODE_W = 160, NODE_H = 50, H_GAP = 40, V_GAP = 30, PAD = 20;

      const levels = {};
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

      const byDepth = {};
      for (const [id, depth] of Object.entries(levels)) {
        (byDepth[depth] = byDepth[depth] || []).push(id);
      }

      const orphans = this.nodeOrder.filter(id => !(id in levels));

      const positions = {};
      const maxDepth = Object.keys(byDepth).length
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

      const orphanCol = maxDepth + 1;
      orphans.forEach((id, row) => {
        positions[id] = {
          x: PAD + orphanCol * (NODE_W + H_GAP),
          y: PAD + row * (NODE_H + V_GAP),
        };
      });

      this.svgNodes = this.nodeOrder.map(id => {
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

    // ── Tool mutations ─────────────────────────────────────────────────────
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
            if (!opt.next?.trim()) errs.push(`Option "${opt.label || '#' + (i + 1)}" in "${id}" has no target (set the → dropdown)`);
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
            if (!grp.tools?.length) errs.push(`Related group "${grp.label || '#' + (i + 1)}" in "${id}" has no tools`);
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
      if (/[:#'"&*?|>{}\[\]!]/.test(str) || /^\s|\s$/.test(str)) {
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
