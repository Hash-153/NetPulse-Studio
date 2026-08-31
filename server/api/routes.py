"""
NetPulse API - RESTful Routing and Endpoint Controllers
Handles topology queries, route computations, packet dissections, diagnostics, and firewall management.
"""

import json
from typing import Dict, Any, List, Optional
from collections import deque

from server.simulator.topology import NetworkTopology, NetworkNode, NetworkLink
from server.simulator.routing import RoutingEngine
from server.simulator.firewall import FirewallEngine, ACLRule
from server.simulator.traffic_gen import TrafficGenerator
from server.diagnostics.ping_monitor import PingDiagnostics
from server.diagnostics.traceroute import TracerouteDiagnostics
from server.diagnostics.port_scanner import PortScanner
from server.diagnostics.bandwidth_meter import BandwidthMeter
from server.diagnostics.anomaly_detector import NetworkAnomalyDetector
from server.core.engine import PacketDissector


class AppContext:
    """Global application state containing engines and history buffers."""
    def __init__(self):
        self.topology = NetworkTopology.create_enterprise_sample()
        self.firewall = FirewallEngine()
        self.bandwidth_meter = BandwidthMeter()
        self.anomaly_detector = NetworkAnomalyDetector()
        self.packet_history: deque[Dict[str, Any]] = deque(maxlen=100)
        self.is_traffic_running = True

        # Pre-populate with initial packets
        for _ in range(12):
            pkt = TrafficGenerator.create_random_sample_packet()
            self.packet_history.append(pkt.to_dict())
            self.bandwidth_meter.record_packet(len(pkt.raw_bytes))


# Singleton instance
ctx = AppContext()


class ApiRoutes:
    """REST API endpoint handlers."""

    @staticmethod
    def get_status() -> Dict[str, Any]:
        return {
            "status": "healthy",
            "version": "2.4.0",
            "nodes_count": len(ctx.topology.nodes),
            "links_count": len(ctx.topology.links),
            "firewall_rules_count": len(ctx.firewall.rules),
            "packets_captured": len(ctx.packet_history),
            "traffic_generator_active": ctx.is_traffic_running,
            "telemetry": ctx.bandwidth_meter.get_summary(),
        }

    @staticmethod
    def get_topology() -> Dict[str, Any]:
        return ctx.topology.to_dict()

    @staticmethod
    def add_node(data: Dict[str, Any]) -> Dict[str, Any]:
        node_id = data.get("id") or f"node-{len(ctx.topology.nodes) + 1}"
        name = data.get("name", "New Node")
        node_type = data.get("type", "host")
        ip = data.get("ip", f"10.10.1.{len(ctx.topology.nodes) + 10}")
        mac = data.get("mac", f"00:1A:2B:09:00:{len(ctx.topology.nodes):02x}")
        x = float(data.get("x", 300))
        y = float(data.get("y", 300))

        node = NetworkNode(node_id, name, node_type, ip, mac, x, y)
        ctx.topology.add_node(node)
        return {"success": True, "node": node.to_dict()}

    @staticmethod
    def add_link(data: Dict[str, Any]) -> Dict[str, Any]:
        link_id = data.get("id") or f"link-{len(ctx.topology.links) + 1}"
        src = data.get("source")
        dst = data.get("target")
        bw = float(data.get("bandwidth_mbps", 100))
        delay = float(data.get("delay_ms", 1.0))
        loss = float(data.get("loss_rate", 0.0))

        if not src or not dst or src not in ctx.topology.nodes or dst not in ctx.topology.nodes:
            return {"error": "Invalid source or target node ID"}

        link = NetworkLink(link_id, src, dst, bandwidth_mbps=bw, delay_ms=delay, loss_rate=loss)
        ctx.topology.add_link(link)
        return {"success": True, "link": link.to_dict()}

    @staticmethod
    def compute_route(src_id: str, dst_id: str) -> Dict[str, Any]:
        res = RoutingEngine.compute_shortest_path(ctx.topology, src_id, dst_id)
        return res.to_dict()

    @staticmethod
    def get_packets(limit: int = 50) -> List[Dict[str, Any]]:
        return list(ctx.packet_history)[-limit:]

    @staticmethod
    def generate_packet(proto: str) -> Dict[str, Any]:
        proto = proto.lower()
        if proto == "icmp":
            pkt = TrafficGenerator.create_icmp_ping()
        elif proto == "dns":
            pkt = TrafficGenerator.create_dns_query()
        elif proto == "http":
            pkt = TrafficGenerator.create_http_request()
        elif proto == "arp":
            pkt = TrafficGenerator.create_arp_probe()
        else:
            pkt = TrafficGenerator.create_random_sample_packet()

        # Evaluate through firewall
        fw_res = ctx.firewall.evaluate_packet(pkt)
        pkt_dict = pkt.to_dict()
        pkt_dict["firewall_eval"] = fw_res

        ctx.packet_history.append(pkt_dict)
        ctx.bandwidth_meter.record_packet(len(pkt.raw_bytes))
        ctx.anomaly_detector.inspect_packet(pkt)

        return pkt_dict

    @staticmethod
    def dissect_hex(raw_hex: str) -> Dict[str, Any]:
        try:
            clean_hex = "".join(raw_hex.split())
            raw_bytes = bytes.fromhex(clean_hex)
            pkt = PacketDissector.dissect(raw_bytes)
            fw_res = ctx.firewall.evaluate_packet(pkt)
            res = pkt.to_dict()
            res["firewall_eval"] = fw_res
            return res
        except Exception as e:
            return {"error": f"Invalid hex string: {str(e)}"}

    @staticmethod
    def run_ping(src_id: str, dst_id: str, count: int = 4) -> Dict[str, Any]:
        return PingDiagnostics.execute_ping(ctx.topology, src_id, dst_id, count=count)

    @staticmethod
    def run_traceroute(src_id: str, dst_id: str) -> Dict[str, Any]:
        return TracerouteDiagnostics.execute_traceroute(ctx.topology, src_id, dst_id)

    @staticmethod
    def run_portscan(ip: str, target_type: str = "server") -> Dict[str, Any]:
        return PortScanner.scan_target(ip, target_type=target_type)

    @staticmethod
    def get_firewall_rules() -> Dict[str, Any]:
        return ctx.firewall.to_dict()

    @staticmethod
    def add_firewall_rule(data: Dict[str, Any]) -> Dict[str, Any]:
        rule_id = int(data.get("id", len(ctx.firewall.rules) * 10 + 10))
        action = data.get("action", "ALLOW")
        proto = data.get("protocol", "TCP")
        src_ip = data.get("src_ip", "any")
        dst_ip = data.get("dst_ip", "any")
        src_p = data.get("src_port", "any")
        dst_p = data.get("dst_port", "any")
        desc = data.get("description", "Custom Rule")

        rule = ACLRule(rule_id, action, proto, src_ip, dst_ip, src_p, dst_p, desc)
        ctx.firewall.add_rule(rule)
        return {"success": True, "rules": ctx.firewall.to_dict()}

    @staticmethod
    def delete_firewall_rule(rule_id: int) -> Dict[str, Any]:
        deleted = ctx.firewall.delete_rule(rule_id)
        return {"success": deleted, "rules": ctx.firewall.to_dict()}

    @staticmethod
    def get_telemetry() -> Dict[str, Any]:
        sample = ctx.bandwidth_meter.tick()
        summary = ctx.bandwidth_meter.get_summary()
        timeseries = ctx.bandwidth_meter.get_timeseries()
        alerts = ctx.anomaly_detector.get_recent_alerts()
        return {
            "latest_sample": sample,
            "summary": summary,
            "timeseries": timeseries,
            "security_alerts": alerts,
        }
