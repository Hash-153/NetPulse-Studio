"""
NetPulse Test Suite - Diagnostics & Telemetry
Validates Ping, Traceroute, Port Scanning, and Bandwidth meter metrics.
"""

import unittest
from server.simulator.topology import NetworkTopology
from server.diagnostics.ping_monitor import PingDiagnostics
from server.diagnostics.traceroute import TracerouteDiagnostics
from server.diagnostics.port_scanner import PortScanner
from server.diagnostics.bandwidth_meter import BandwidthMeter
from server.diagnostics.anomaly_detector import NetworkAnomalyDetector
from server.simulator.traffic_gen import TrafficGenerator


class TestDiagnostics(unittest.TestCase):

    def setUp(self):
        self.topology = NetworkTopology.create_enterprise_sample()

    def test_ping_execution(self):
        res = PingDiagnostics.execute_ping(self.topology, "pc-eng1", "srv-web", count=4)
        self.assertEqual(res["packets_transmitted"], 4)
        self.assertGreater(res["packets_received"], 0)
        self.assertIsNotNone(res["rtt_avg_ms"])
        self.assertGreater(res["rtt_avg_ms"], 0)

    def test_traceroute_execution(self):
        res = TracerouteDiagnostics.execute_traceroute(self.topology, "pc-eng1", "srv-web")
        self.assertTrue(res["target_reached"])
        self.assertGreater(res["total_hops"], 2)

    def test_port_scanner(self):
        res = PortScanner.scan_target("10.20.1.10", target_type="server")
        self.assertEqual(res["target_ip"], "10.20.1.10")
        self.assertGreater(res["open_ports"], 0)
        # Port 80 should be open on web server
        p80 = next((p for p in res["scan_results"] if p["port"] == 80), None)
        self.assertIsNotNone(p80)
        self.assertEqual(p80["state"], "OPEN")

    def test_bandwidth_meter(self):
        bm = BandwidthMeter(history_seconds=10)
        bm.record_packet(1500)
        bm.record_packet(1500)
        sample = bm.tick()
        self.assertEqual(sample["bytes_in_second"], 3000)
        self.assertGreater(sample["throughput_kbps"], 0)


if __name__ == "__main__":
    unittest.main()
