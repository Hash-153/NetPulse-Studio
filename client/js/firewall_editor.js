/**
 * NetPulse - Firewall & ACL Rule Editor
 */

window.FirewallEditor = {
  rules: [],

  init() {
    this.fetchRules();
    this.bindEvents();
  },

  bindEvents() {
    const addBtn = document.getElementById('btn-open-add-rule');
    if (addBtn) {
      addBtn.addEventListener('click', () => this.promptAddRule());
    }
  },

  async fetchRules() {
    try {
      const res = await fetch('/api/firewall');
      if (res.ok) {
        const data = await res.json();
        this.rules = data.rules || [];
        const statElem = document.getElementById('stat-rules');
        if (statElem) statElem.textContent = this.rules.length;
        this.renderTable();
      }
    } catch (e) {
      console.error('Failed to fetch firewall rules:', e);
    }
  },

  renderTable() {
    const tbody = document.getElementById('firewall-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';
    this.rules.forEach(r => {
      const tr = document.createElement('tr');

      const actionBadge = r.action === 'ALLOW' ? 'badge-udp' : 'badge-arp';
      const protoBadge = `badge-${r.protocol.toLowerCase()}`;

      tr.innerHTML = `
        <td>#${r.id}</td>
        <td><span class="badge-tag ${actionBadge}">${r.action}</span></td>
        <td><span class="badge-tag ${protoBadge}">${r.protocol}</span></td>
        <td>${r.src_ip}</td>
        <td>${r.dst_ip}</td>
        <td>${r.dst_port}</td>
        <td>${r.description}</td>
        <td style="color: var(--accent-cyan); font-weight: 700;">${r.match_count}</td>
        <td>
          <button class="btn btn-danger" style="padding: 2px 8px; font-size: 0.75rem;" onclick="window.FirewallEditor.deleteRule(${r.id})">Delete</button>
        </td>
      `;

      tbody.appendChild(tr);
    });
  },

  async promptAddRule() {
    const action = prompt("Action (ALLOW or DENY):", "DENY");
    if (!action) return;

    const protocol = prompt("Protocol (TCP, UDP, ICMP, ANY):", "TCP");
    if (!protocol) return;

    const dstIp = prompt("Destination IP or CIDR (e.g. 10.20.1.10 or any):", "10.20.1.20");
    if (!dstIp) return;

    const dstPort = prompt("Destination Port (e.g. 80, 5432, any):", "5432");
    if (!dstPort) return;

    const desc = prompt("Rule Description:", "Custom Security Policy");

    try {
      const res = await fetch('/api/firewall/rule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: action.toUpperCase(),
          protocol: protocol.toUpperCase(),
          src_ip: "any",
          dst_ip: dstIp,
          src_port: "any",
          dst_port: dstPort,
          description: desc || "Custom Policy"
        })
      });

      if (res.ok) {
        this.fetchRules();
      }
    } catch (e) {
      alert("Failed to add rule: " + e.message);
    }
  },

  async deleteRule(ruleId) {
    if (!confirm(`Delete Firewall Rule #${ruleId}?`)) return;
    try {
      const res = await fetch(`/api/firewall/rule?id=${ruleId}`, { method: 'DELETE' });
      if (res.ok) {
        this.fetchRules();
      }
    } catch (e) {
      alert("Failed to delete rule: " + e.message);
    }
  }
};
