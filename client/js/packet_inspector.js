/**
 * NetPulse - Packet Sniffer & Wireshark-Style Deep Packet Inspector
 */

const PacketInspector = {
  packets: [],
  selectedPacketIndex: null,

  init() {
    this.bindButtons();
    this.fetchPackets();
    setInterval(() => this.fetchPackets(), 2000);
  },

  bindButtons() {
    const map = [
      { id: 'btn-inject-icmp', proto: 'icmp' },
      { id: 'btn-inject-dns', proto: 'dns' },
      { id: 'btn-inject-http', proto: 'http' },
      { id: 'btn-inject-arp', proto: 'arp' }
    ];

    map.forEach(item => {
      const btn = document.getElementById(item.id);
      if (btn) {
        btn.addEventListener('click', async () => {
          await fetch('/api/packets/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ protocol: item.proto })
          });
          this.fetchPackets();
        });
      }
    });
  },

  async fetchPackets() {
    try {
      const res = await fetch('/api/packets?limit=30');
      if (res.ok) {
        this.packets = await res.json();
        this.renderTable();
        
        // Auto-select latest if none selected
        if (this.selectedPacketIndex === null && this.packets.length > 0) {
          this.selectPacket(this.packets.length - 1);
        }
      }
    } catch (e) {
      console.error('Fetch packets failed:', e);
    }
  },

  renderTable() {
    const tbody = document.getElementById('packet-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';
    this.packets.forEach((pkt, idx) => {
      const tr = document.createElement('tr');
      tr.className = `packet-row ${this.selectedPacketIndex === idx ? 'selected' : ''}`;

      const fwAction = pkt.firewall_eval ? pkt.firewall_eval.action : 'ALLOW';
      const fwBadgeClass = fwAction === 'ALLOW' ? 'badge-udp' : 'badge-arp';

      const timeStr = new Date(pkt.timestamp * 1000).toLocaleTimeString();

      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td>${timeStr}</td>
        <td>${pkt.length} B</td>
        <td style="max-width: 320px; overflow: hidden; text-overflow: ellipsis;">${pkt.summary}</td>
        <td><span class="badge-tag ${fwBadgeClass}">${fwAction}</span></td>
      `;

      tr.addEventListener('click', () => this.selectPacket(idx));
      tbody.appendChild(tr);
    });
  },

  selectPacket(idx) {
    this.selectedPacketIndex = idx;
    this.renderTable();

    const pkt = this.packets[idx];
    if (!pkt) return;

    this.renderProtocolTree(pkt);
    this.renderHexDump(pkt);
  },

  renderProtocolTree(pkt) {
    const container = document.getElementById('protocol-tree-content');
    if (!container) return;

    container.innerHTML = '';

    pkt.layers.forEach((layer) => {
      const node = document.createElement('div');
      node.className = 'layer-node';

      const header = document.createElement('div');
      header.className = 'layer-header';
      header.innerHTML = `
        <span><strong>${layer.name}</strong> (Layer ${layer.layer_id})</span>
        <span style="font-size: 0.75rem; color: var(--text-dim);">${layer.header_len} bytes</span>
      `;

      const body = document.createElement('div');
      body.className = 'layer-body';

      for (const [key, val] of Object.entries(layer.fields)) {
        if (typeof val === 'object') continue;
        const line = document.createElement('div');
        line.className = 'field-line';
        line.innerHTML = `
          <span class="field-name">${key}</span>
          <span class="field-value">${val}</span>
        `;
        body.appendChild(line);
      }

      header.addEventListener('click', () => {
        body.style.display = body.style.display === 'none' ? 'block' : 'none';
      });

      node.appendChild(header);
      node.appendChild(body);
      container.appendChild(node);
    });
  },

  renderHexDump(pkt) {
    const container = document.getElementById('hex-dump-content');
    if (!container) return;

    container.innerHTML = '';
    if (!pkt.hex_dump || pkt.hex_dump.length === 0) {
      container.innerHTML = '<span style="color: var(--text-dim);">Empty payload</span>';
      return;
    }

    pkt.hex_dump.forEach(line => {
      const div = document.createElement('div');
      div.className = 'hex-line';
      div.innerHTML = `
        <span class="hex-offset">${line.offset}</span>
        <span class="hex-bytes">${line.hex}</span>
        <span class="hex-ascii">${line.ascii}</span>
      `;
      container.appendChild(div);
    });
  }
};
