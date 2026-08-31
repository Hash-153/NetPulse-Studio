"""
NetPulse Diagnostics - Bandwidth Utilization & Telemetry Aggregator
Tracks live throughput, packet transfer rates, and rolling timeseries metrics.
"""

import time
from typing import Dict, Any, List
from collections import deque


class BandwidthMeter:
    """
    Maintains sliding window telemetry of network traffic throughput (Kbps, PPS).
    """

    def __init__(self, history_seconds: int = 60):
        self.history_seconds = history_seconds
        self.samples = deque(maxlen=history_seconds)
        self.total_bytes = 0
        self.total_packets = 0
        self.last_ts = time.time()
        self.current_window_bytes = 0
        self.current_window_packets = 0

    def record_packet(self, packet_size_bytes: int) -> None:
        self.total_bytes += packet_size_bytes
        self.total_packets += 1
        self.current_window_bytes += packet_size_bytes
        self.current_window_packets += 1

    def tick(self) -> Dict[str, Any]:
        """Called every second to record the sliding window throughput."""
        now = time.time()
        dt = max(0.1, now - self.last_ts)
        self.last_ts = now

        rate_bps = (self.current_window_bytes * 8) / dt
        rate_kbps = rate_bps / 1000.0
        pps = self.current_window_packets / dt

        sample = {
            "timestamp": int(now),
            "throughput_kbps": round(rate_kbps, 2),
            "packets_per_sec": round(pps, 1),
            "bytes_in_second": self.current_window_bytes,
        }
        self.samples.append(sample)

        self.current_window_bytes = 0
        self.current_window_packets = 0

        return sample

    def get_timeseries(self) -> List[Dict[str, Any]]:
        return list(self.samples)

    def get_summary(self) -> Dict[str, Any]:
        latest_kbps = self.samples[-1]["throughput_kbps"] if self.samples else 0.0
        latest_pps = self.samples[-1]["packets_per_sec"] if self.samples else 0.0
        return {
            "total_megabytes": round(self.total_bytes / (1024 * 1024), 2),
            "total_packets": self.total_packets,
            "current_throughput_kbps": latest_kbps,
            "current_pps": latest_pps,
            "history_points": len(self.samples),
        }
