/**
 * NetPulse Application - Core Controller & Navigation
 */

const App = {
  activeTab: 'tab-topology',
  pollInterval: null,

  init() {
    this.bindNavigation();
    this.bindGlobalActions();
    this.startTelemetryPolling();

    // Initialize modules
    if (window.TopologyView) TopologyView.init();
    if (window.PacketInspector) PacketInspector.init();
    if (window.DiagnosticsUI) DiagnosticsUI.init();
    if (window.FirewallEditor) FirewallEditor.init();
    if (window.LiveMonitor) LiveMonitor.init();
  },

  bindNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        this.switchTab(tabId);
      });
    });
  },

  switchTab(tabId) {
    this.activeTab = tabId;

    document.querySelectorAll('.nav-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
    });

    document.querySelectorAll('.tab-pane').forEach(p => {
      p.classList.toggle('active', p.id === tabId);
    });

    if (tabId === 'tab-topology' && window.TopologyView) {
      TopologyView.render();
    }
  },

  bindGlobalActions() {
    const quickInjectBtn = document.getElementById('btn-quick-inject');
    if (quickInjectBtn) {
      quickInjectBtn.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/packets/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ protocol: 'random' })
          });
          const pkt = await res.json();
          if (window.PacketInspector) PacketInspector.fetchPackets();
        } catch (e) {
          console.error('Inject error:', e);
        }
      });
    }
  },

  startTelemetryPolling() {
    const fetchTelemetry = async () => {
      try {
        const res = await fetch('/api/telemetry');
        if (!res.ok) return;
        const data = await res.json();

        // Update metrics header
        if (data.summary) {
          const tpElem = document.getElementById('stat-throughput');
          const ppsElem = document.getElementById('stat-pps');
          if (tpElem) tpElem.textContent = `${data.summary.current_throughput_kbps} Kbps`;
          if (ppsElem) ppsElem.textContent = `${data.summary.current_pps} PPS`;
        }

        if (window.LiveMonitor) {
          LiveMonitor.update(data);
        }
      } catch (e) {
        // Silent catch during initial server boot
      }
    };

    fetchTelemetry();
    this.pollInterval = setInterval(fetchTelemetry, 1500);
  }
};

document.addEventListener('DOMContentLoaded', () => App.init());
