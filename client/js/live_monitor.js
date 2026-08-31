/**
 * NetPulse - Real-Time Canvas Telemetry Chart & IDS Security Alert Stream
 */

window.LiveMonitor = {
  canvas: null,
  ctx: null,
  history: [],

  init() {
    this.canvas = document.getElementById('throughput-chart');
    if (this.canvas) {
      this.ctx = this.canvas.getContext('2d');
    }
  },

  update(telemetryData) {
    if (telemetryData.timeseries) {
      this.history = telemetryData.timeseries;
      this.renderChart();
    }

    if (telemetryData.security_alerts) {
      this.renderAlerts(telemetryData.security_alerts);
    }
  },

  renderChart() {
    if (!this.ctx || !this.canvas) return;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, w, h);

    // Draw Grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.lineWidth = 1;
    for (let y = 30; y < h; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    if (this.history.length < 2) return;

    const values = this.history.map(s => s.throughput_kbps);
    const maxVal = Math.max(10, ...values) * 1.25;
    const stepX = w / (this.history.length - 1);

    // Fill Gradient
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(0, 212, 255, 0.35)');
    grad.addColorStop(1, 'rgba(0, 212, 255, 0.0)');

    ctx.beginPath();
    ctx.moveTo(0, h);

    for (let i = 0; i < this.history.length; i++) {
      const x = i * stepX;
      const y = h - (this.history[i].throughput_kbps / maxVal) * (h - 40);
      ctx.lineTo(x, y);
    }

    ctx.lineTo((this.history.length - 1) * stepX, h);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Draw Stroke Line
    ctx.beginPath();
    for (let i = 0; i < this.history.length; i++) {
      const x = i * stepX;
      const y = h - (this.history[i].throughput_kbps / maxVal) * (h - 40);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = '#00d4ff';
    ctx.lineWidth = 2.5;
    ctx.stroke();
  },

  renderAlerts(alerts) {
    const container = document.getElementById('ids-alerts-container');
    if (!container) return;

    if (!alerts || alerts.length === 0) {
      container.innerHTML = `<p style="color: var(--text-dim); font-size: 0.85rem;">No active security anomalies detected.</p>`;
      return;
    }

    container.innerHTML = '';
    alerts.slice(-6).reverse().forEach(a => {
      const card = document.createElement('div');
      card.style.background = 'rgba(10, 14, 23, 0.6)';
      card.style.border = '1px solid rgba(244, 63, 94, 0.3)';
      card.style.borderRadius = '8px';
      card.style.padding = '0.65rem 0.85rem';
      card.style.fontSize = '0.8rem';

      const sevColor = a.severity === 'CRITICAL' ? 'var(--accent-rose)' : 'var(--accent-amber)';

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
          <strong style="color: ${sevColor};">${a.type}</strong>
          <span style="color: var(--text-dim); font-family: var(--font-mono);">${a.timestamp}</span>
        </div>
        <div style="color: var(--text-muted);">${a.description}</div>
      `;

      container.appendChild(card);
    });
  }
};
