/**
 * NetPulse - Network Topology SVG Renderer & Interactive Graph Engine
 */

window.TopologyView = {
  svg: null,
  data: { nodes: [], links: [] },
  selectedNode: null,
  highlightedPath: [],
  isDragging: false,
  dragNode: null,
  dragOffset: { x: 0, y: 0 },

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

    const computeBtn = document.getElementById('btn-route-path');
    if (computeBtn) {
      computeBtn.addEventListener('click', () => this.traceRoute());
    }

    const resetBtn = document.getElementById('btn-refresh-topo');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        this.highlightedPath = [];
        this.fetchTopology().then(() => {
          this.populateSelectors();
          this.render();
        });
      });
    }

    if (this.svg) {
      this.svg.addEventListener('mousemove', (e) => this.handleMouseMove(e));
      this.svg.addEventListener('mouseup', () => this.handleMouseUp());
      this.svg.addEventListener('mouseleave', () => this.handleMouseUp());
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
    if (!srcSel || !dstSel || !this.data.nodes.length) return;

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

    // Create defs for filters and markers
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `
      <filter id="glow-cyan" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="5" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
      <linearGradient id="link-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#00d4ff" />
        <stop offset="100%" stop-color="#3b82f6" />
      </linearGradient>
    `;
    this.svg.appendChild(defs);

    const nodeMap = new Map();
    this.data.nodes.forEach(n => nodeMap.set(n.id, n));

    // Render Links
    const linksGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    linksGroup.setAttribute('id', 'topo-links-group');
    this.svg.appendChild(linksGroup);

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
      if (isHighlighted) {
        line.setAttribute('style', 'stroke: #00d4ff; stroke-width: 4px; filter: url(#glow-cyan);');
      } else {
        line.setAttribute('style', 'stroke: rgba(255, 255, 255, 0.2); stroke-width: 2px;');
      }
      linksGroup.appendChild(line);

      // Link speed/latency label
      const midX = (src.x + dst.x) / 2;
      const midY = (src.y + dst.y) / 2;
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', midX);
      text.setAttribute('y', midY - 6);
      text.setAttribute('fill', 'rgba(255, 255, 255, 0.4)');
      text.setAttribute('font-size', '9px');
      text.setAttribute('font-family', 'monospace');
      text.setAttribute('text-anchor', 'middle');
      text.textContent = `${link.bandwidth_mbps}M | ${link.delay_ms}ms`;
      linksGroup.appendChild(text);
    });

    // Render Nodes
    const nodesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    nodesGroup.setAttribute('id', 'topo-nodes-group');
    this.svg.appendChild(nodesGroup);

    this.data.nodes.forEach(node => {
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.setAttribute('class', `topo-node ${this.selectedNode === node.id ? 'selected' : ''}`);
      g.setAttribute('transform', `translate(${node.x}, ${node.y})`);
      g.setAttribute('data-node-id', node.id);

      const colorMap = {
        'gateway': '#f59e0b',
        'router': '#00d4ff',
        'switch': '#3b82f6',
        'server': '#8b5cf6',
        'host': '#10b981',
      };
      const themeColor = colorMap[node.type] || '#3b82f6';
      const isSelected = (this.selectedNode === node.id);

      // Card Background Box
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', -65);
      rect.setAttribute('y', -32);
      rect.setAttribute('width', 130);
      rect.setAttribute('height', 64);
      rect.setAttribute('rx', 10);
      rect.setAttribute('ry', 10);
      rect.setAttribute('fill', '#111927');
      rect.setAttribute('stroke', isSelected ? '#00d4ff' : themeColor);
      rect.setAttribute('stroke-width', isSelected ? '2.5' : '1.5');
      if (isSelected) {
        rect.setAttribute('filter', 'url(#glow-cyan)');
      }

      // Top color indicator bar
      const topBar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      topBar.setAttribute('x', -65);
      topBar.setAttribute('y', -32);
      topBar.setAttribute('width', 130);
      topBar.setAttribute('height', 4);
      topBar.setAttribute('rx', 2);
      topBar.setAttribute('fill', themeColor);

      // Type Badge
      const typeTag = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      typeTag.setAttribute('x', 0);
      typeTag.setAttribute('y', -14);
      typeTag.setAttribute('fill', themeColor);
      typeTag.setAttribute('font-size', '8.5px');
      typeTag.setAttribute('font-weight', '700');
      typeTag.setAttribute('letter-spacing', '0.05em');
      typeTag.setAttribute('text-anchor', 'middle');
      typeTag.textContent = node.type.toUpperCase();

      // Title
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      title.setAttribute('x', 0);
      title.setAttribute('y', 3);
      title.setAttribute('fill', '#ffffff');
      title.setAttribute('font-size', '11px');
      title.setAttribute('font-weight', '600');
      title.setAttribute('text-anchor', 'middle');
      title.textContent = node.name;

      // IP Subtitle
      const sub = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      sub.setAttribute('x', 0);
      sub.setAttribute('y', 19);
      sub.setAttribute('fill', '#9ca3af');
      sub.setAttribute('font-size', '9.5px');
      sub.setAttribute('font-family', 'monospace');
      sub.setAttribute('text-anchor', 'middle');
      sub.textContent = node.ip;

      g.appendChild(rect);
      g.appendChild(topBar);
      g.appendChild(typeTag);
      g.appendChild(title);
      g.appendChild(sub);

      // Mouse drag and selection handlers
      g.addEventListener('mousedown', (e) => {
        this.handleMouseDown(e, node);
      });

      g.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectNode(node);
      });

      nodesGroup.appendChild(g);
    });
  },

  handleMouseDown(e, node) {
    this.isDragging = true;
    this.dragNode = node;
    const pt = this.getSVGCoords(e);
    this.dragOffset = { x: pt.x - node.x, y: pt.y - node.y };
  },

  handleMouseMove(e) {
    if (!this.isDragging || !this.dragNode) return;
    const pt = this.getSVGCoords(e);
    this.dragNode.x = Math.max(70, Math.min(730, pt.x - this.dragOffset.x));
    this.dragNode.y = Math.max(40, Math.min(500, pt.y - this.dragOffset.y));
    this.render();
  },

  handleMouseUp() {
    this.isDragging = false;
    this.dragNode = null;
  },

  getSVGCoords(e) {
    const rect = this.svg.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 800;
    const y = ((e.clientY - rect.top) / rect.height) * 550;
    return { x, y };
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
        <div style="font-weight: 700; color: #fff; font-size: 1rem; margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between;">
          <span>${node.name}</span>
          <span style="font-size: 0.75rem; background: rgba(0, 212, 255, 0.15); color: #00d4ff; padding: 2px 6px; border-radius: 4px;">${node.type.toUpperCase()}</span>
        </div>
        <div class="prop-row"><span class="prop-key">Node ID</span><span class="prop-val">${node.id}</span></div>
        <div class="prop-row"><span class="prop-key">IPv4 Address</span><span class="prop-val" style="color: #00d4ff;">${node.ip}</span></div>
        <div class="prop-row"><span class="prop-key">MAC Address</span><span class="prop-val">${node.mac}</span></div>
        <div class="prop-row"><span class="prop-key">Status</span><span class="prop-val" style="color: #10b981;">● ONLINE</span></div>
      `;
    }
  },

  async traceRoute() {
    const srcElem = document.getElementById('route-src-select');
    const dstElem = document.getElementById('route-dst-select');
    const src = srcElem ? srcElem.value : 'pc-eng1';
    const dst = dstElem ? dstElem.value : 'srv-web';
    const outBox = document.getElementById('route-result-box');

    try {
      const res = await fetch(`/api/route?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dst)}`);
      const data = await res.json();

      if (data.reachable) {
        this.highlightedPath = data.path.map(h => h.node_id);
        this.render();

        if (outBox) {
          outBox.innerHTML = `
            <div style="background: rgba(0, 212, 255, 0.08); border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 6px; padding: 8px;">
              <div style="color: #00d4ff; font-weight: 700; margin-bottom: 4px;">✓ Shortest Route Found:</div>
              <div style="color: #f3f4f6;">Hops: <strong>${data.total_hops}</strong> | Latency: <strong>${data.total_latency_ms} ms</strong> | Bandwidth: <strong>${data.bottleneck_bandwidth_mbps} Mbps</strong></div>
              <div style="color: #9ca3af; font-family: monospace; font-size: 0.75rem; margin-top: 4px;">${data.path.map(p => p.node_name).join(' ➔ ')}</div>
            </div>
          `;
        }
      } else {
        this.highlightedPath = [];
        this.render();
        if (outBox) {
          outBox.innerHTML = `<div style="color: #f43f5e; font-weight: 600; padding: 6px;">✕ Destination Unreachable: No route between selected nodes.</div>`;
        }
      }
    } catch (e) {
      console.error('Route trace failed:', e);
    }
  }
};
