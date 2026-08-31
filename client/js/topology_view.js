/**
 * NetPulse - Network Topology SVG Renderer & Interactive Graph
 */

const TopologyView = {
  svg: null,
  data: { nodes: [], links: [] },
  selectedNode: null,
  highlightedPath: [],

  async init() {
    this.svg = document.getElementById('topology-svg');
    this.bindEvents();
    await this.fetchTopology();
    this.populateSelectors();
    this.render();
  },

  bindEvents() {
    const traceBtn = document.getElementById('btn-execute-route');
    if (traceBtn) {
      traceBtn.addEventListener('click', () => this.traceRoute());
    }

    const resetBtn = document.getElementById('btn-refresh-topo');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        this.highlightedPath = [];
        this.render();
      });
    }
  },

  async fetchTopology() {
    try {
      const res = await fetch('/api/topology');
      if (res.ok) {
        this.data = await res.json();
        const statNodes = document.getElementById('stat-nodes');
        if (statNodes) statNodes.textContent = this.data.nodes.length;
      }
    } catch (e) {
      console.error('Failed to fetch topology:', e);
    }
  },

  populateSelectors() {
    const srcSel = document.getElementById('route-src-select');
    const dstSel = document.getElementById('route-dst-select');
    if (!srcSel || !dstSel) return;

    srcSel.innerHTML = '';
    dstSel.innerHTML = '';

    this.data.nodes.forEach(node => {
      const opt1 = document.createElement('option');
      opt1.value = node.id;
      opt1.textContent = `${node.name} (${node.ip})`;
      srcSel.appendChild(opt1);

      const opt2 = document.createElement('option');
      opt2.value = node.id;
      opt2.textContent = `${node.name} (${node.ip})`;
      dstSel.appendChild(opt2);
    });

    if (this.data.nodes.length > 4) {
      srcSel.value = 'pc-eng1';
      dstSel.value = 'srv-web';
    }
  },

  render() {
    if (!this.svg) return;
    this.svg.innerHTML = '';

    // Create defs for glow and arrow markers
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `
      <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="4" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    `;
    this.svg.appendChild(defs);

    const nodeMap = new Map();
    this.data.nodes.forEach(n => nodeMap.set(n.id, n));

    // Render Links
    this.data.links.forEach(link => {
      const src = nodeMap.get(link.source);
      const dst = nodeMap.get(link.target);
      if (!src || !dst) return;

      const isHighlighted = this.isLinkInPath(link.source, link.target);

      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', src.x);
      line.setAttribute('y1', src.y);
      line.setAttribute('x2', dst.x);
      line.setAttribute('y2', dst.y);
      line.setAttribute('class', `topo-link ${isHighlighted ? 'highlighted' : ''}`);
      this.svg.appendChild(line);
    });

    // Render Nodes
    this.data.nodes.forEach(node => {
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.setAttribute('class', `topo-node ${this.selectedNode === node.id ? 'selected' : ''}`);
      g.setAttribute('transform', `translate(${node.x}, ${node.y})`);

      // Card Box
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', -60);
      rect.setAttribute('y', -30);
      rect.setAttribute('width', 120);
      rect.setAttribute('height', 60);
      rect.setAttribute('class', 'topo-node-card');

      // Title & Subtitle
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      title.setAttribute('y', -5);
      title.setAttribute('class', 'topo-node-title');
      title.textContent = node.name;

      const sub = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      sub.setAttribute('y', 12);
      sub.setAttribute('class', 'topo-node-sub');
      sub.textContent = node.ip;

      g.appendChild(rect);
      g.appendChild(title);
      g.appendChild(sub);

      g.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectNode(node);
      });

      this.svg.appendChild(g);
    });
  },

  isLinkInPath(n1, n2) {
    if (this.highlightedPath.length < 2) return false;
    for (let i = 0; i < this.highlightedPath.length - 1; i++) {
      const a = this.highlightedPath[i];
      const b = this.highlightedPath[i + 1];
      if ((a === n1 && b === n2) || (a === n2 && b === n1)) {
        return true;
      }
    }
    return false;
  },

  selectNode(node) {
    this.selectedNode = node.id;
    this.render();

    const box = document.getElementById('node-inspector-details');
    if (box) {
      box.innerHTML = `
        <div style="font-weight: 700; color: #fff; margin-bottom: 0.5rem;">${node.name}</div>
        <div class="prop-row"><span class="prop-key">Node ID</span><span class="prop-val">${node.id}</span></div>
        <div class="prop-row"><span class="prop-key">Node Type</span><span class="prop-val">${node.type.toUpperCase()}</span></div>
        <div class="prop-row"><span class="prop-key">IPv4 Address</span><span class="prop-val">${node.ip}</span></div>
        <div class="prop-row"><span class="prop-key">MAC Address</span><span class="prop-val">${node.mac}</span></div>
        <div class="prop-row"><span class="prop-key">Status</span><span class="prop-val" style="color: var(--accent-emerald);">${node.status.toUpperCase()}</span></div>
      `;
    }
  },

  async traceRoute() {
    const src = document.getElementById('route-src-select').value;
    const dst = document.getElementById('route-dst-select').value;
    const outBox = document.getElementById('route-result-box');

    try {
      const res = await fetch(`/api/route?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dst)}`);
      const data = await res.json();

      if (data.reachable) {
        this.highlightedPath = data.path.map(h => h.node_id);
        this.render();

        if (outBox) {
          outBox.innerHTML = `
            <div style="color: var(--accent-cyan); font-weight: 600; margin-bottom: 4px;">Shortest Path Discovered:</div>
            <div>Total Hops: <strong>${data.total_hops}</strong> | Latency: <strong>${data.total_latency_ms} ms</strong></div>
            <div style="color: var(--text-dim); margin-top: 4px;">${data.path.map(p => p.node_name).join(' -> ')}</div>
          `;
        }
      } else {
        this.highlightedPath = [];
        this.render();
        if (outBox) outBox.innerHTML = `<span style="color: var(--accent-rose);">Destination Unreachable</span>`;
      }
    } catch (e) {
      console.error('Route trace failed:', e);
    }
  }
};
