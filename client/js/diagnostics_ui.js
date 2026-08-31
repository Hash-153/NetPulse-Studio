/**
 * NetPulse - Diagnostics Workbench (Ping, Traceroute, Port Scanner)
 */

const DiagnosticsUI = {
  init() {
    this.populateNodeSelects();
    this.bindEvents();
  },

  async populateNodeSelects() {
    const srcSel = document.getElementById('diag-src-select');
    const dstSel = document.getElementById('diag-dst-select');
    if (!srcSel || !dstSel) return;

    try {
      const res = await fetch('/api/topology');
      const data = await res.json();

      srcSel.innerHTML = '';
      dstSel.innerHTML = '';

      data.nodes.forEach(n => {
        const o1 = document.createElement('option');
        o1.value = n.id;
        o1.textContent = `${n.name} (${n.ip})`;
        srcSel.appendChild(o1);

        const o2 = document.createElement('option');
        o2.value = n.id;
        o2.textContent = `${n.name} (${n.ip})`;
        dstSel.appendChild(o2);
      });

      if (data.nodes.length > 4) {
        srcSel.value = 'pc-eng1';
        dstSel.value = 'srv-web';
      }
    } catch (e) {
      console.error('Failed to load topology for diagnostics:', e);
    }
  },

  bindEvents() {
    const pingBtn = document.getElementById('btn-run-ping');
    if (pingBtn) {
      pingBtn.addEventListener('click', () => this.runPing());
    }

    const traceBtn = document.getElementById('btn-run-traceroute');
    if (traceBtn) {
      traceBtn.addEventListener('click', () => this.runTraceroute());
    }

    const portBtn = document.getElementById('btn-run-portscan');
    if (portBtn) {
      portBtn.addEventListener('click', () => this.runPortScan());
    }
  },

  async runPing() {
    const src = document.getElementById('diag-src-select').value;
    const dst = document.getElementById('diag-dst-select').value;
    const consoleBox = document.getElementById('diag-output-console');

    consoleBox.innerHTML = `PING ${dst} from ${src}: 64 data bytes...\n`;

    try {
      const res = await fetch(`/api/diagnostics/ping?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dst)}&count=4`);
      const data = await res.json();

      if (data.error) {
        consoleBox.innerHTML += `<span style="color: var(--accent-rose);">${data.error}</span>\n`;
        return;
      }

      let lines = `PING ${data.destination.name} (${data.destination.ip}) 64 bytes of data:\n`;
      data.probes.forEach(p => {
        if (p.status === 'SUCCESS') {
          lines += `64 bytes from ${data.destination.ip}: icmp_seq=${p.sequence} ttl=${p.ttl} time=${p.rtt_ms} ms\n`;
        } else {
          lines += `Request timeout for icmp_seq ${p.sequence} (${p.status})\n`;
        }
      });

      lines += `\n--- ${data.destination.name} ping statistics ---\n`;
      lines += `${data.packets_transmitted} packets transmitted, ${data.packets_received} received, ${data.packet_loss_percent}% packet loss\n`;
      if (data.rtt_avg_ms !== null) {
        lines += `rtt min/avg/max/mdev = ${data.rtt_min_ms}/${data.rtt_avg_ms}/${data.rtt_max_ms}/${data.rtt_mdev_ms} ms (Jitter: ${data.jitter_ms} ms)\n`;
      }

      consoleBox.innerText = lines;
    } catch (e) {
      consoleBox.innerText = `Ping failed: ${e.message}`;
    }
  },

  async runTraceroute() {
    const src = document.getElementById('diag-src-select').value;
    const dst = document.getElementById('diag-dst-select').value;
    const consoleBox = document.getElementById('diag-output-console');

    consoleBox.innerText = `traceroute to ${dst} (from ${src}), 30 hops max...\n`;

    try {
      const res = await fetch(`/api/diagnostics/traceroute?src=${encodeURIComponent(src)}&dst=${encodeURIComponent(dst)}`);
      const data = await res.json();

      if (data.error) {
        consoleBox.innerText = `Error: ${data.error}`;
        return;
      }

      let lines = `traceroute to ${data.destination.name} (${data.destination.ip}), 30 hops max:\n`;
      data.hops.forEach(h => {
        const samples = h.rtt_samples_ms.map(s => `${s} ms`).join('  ');
        lines += ` ${h.hop}  ${h.name} (${h.ip})  ${samples}\n`;
      });
      lines += `\nTrace complete. Total hops: ${data.total_hops}\n`;

      consoleBox.innerText = lines;
    } catch (e) {
      consoleBox.innerText = `Traceroute failed: ${e.message}`;
    }
  },

  async runPortScan() {
    const ip = document.getElementById('scan-target-ip').value;
    const type = document.getElementById('scan-node-type').value;
    const consoleBox = document.getElementById('scan-output-console');

    consoleBox.innerText = `Initiating SYN Stealth Scan against ${ip}...\n`;

    try {
      const res = await fetch(`/api/diagnostics/portscan?ip=${encodeURIComponent(ip)}&type=${encodeURIComponent(type)}`);
      const data = await res.json();

      let lines = `Nmap-compatible Scan report for ${data.target_ip} (${data.target_type.toUpperCase()})\n`;
      lines += `PORT     STATE  SERVICE     DESCRIPTION\n`;
      lines += `--------------------------------------------------------\n`;

      data.scan_results.forEach(r => {
        const portStr = `${r.port}/tcp`.padEnd(8, ' ');
        const stateStr = r.state.padEnd(6, ' ');
        const srvStr = r.service.padEnd(11, ' ');
        lines += `${portStr} ${stateStr} ${srvStr} ${r.description} (${r.latency_ms}ms)\n`;
      });

      lines += `\nScan summary: ${data.open_ports} open ports found out of ${data.ports_scanned} scanned.\n`;
      consoleBox.innerText = lines;
    } catch (e) {
      consoleBox.innerText = `Port scan failed: ${e.message}`;
    }
  }
};
