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
