"""
NetPulse Diagnostics - Intrusion & Anomaly Detection System (IDS)
Heuristic security engine detecting port scans, SYN floods, and ARP spoofing attempts.
"""

import time
from typing import Dict, Any, List
from collections import defaultdict, deque
from server.core.packet import DissectedPacket
from server.core.protocol_ipv4 import IPv4Layer
from server.core.protocol_tcp import TCPLayer, TCP_SYN, TCP_ACK
from server.core.protocol_arp import ARPLayer, ARP_OP_REPLY


class SecurityAlert:
    def __init__(self, alert_type: str, severity: str, source_ip: str, target_ip: str,
                 description: str, timestamp: float):
        self.alert_type = alert_type
        self.severity = severity  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        self.source_ip = source_ip
        self.target_ip = target_ip
        self.description = description
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.alert_type,
            "severity": self.severity,
            "source_ip": self.source_ip,
            "target_ip": self.target_ip,
            "description": self.description,
            "timestamp": time.strftime("%H:%M:%S", time.localtime(self.timestamp)),
        }


class NetworkAnomalyDetector:
    """
    Stateful anomaly detection engine analyzing live packet streams.
    """

    def __init__(self):
        self.alerts: deque[SecurityAlert] = deque(maxlen=50)
        
        # Track TCP SYN packets per IP within 5s window
        self.syn_tracker: Dict[str, deque[float]] = defaultdict(deque)
        
        # Track targeted ports per IP within 5s window
        self.port_tracker: Dict[str, Dict[int, float]] = defaultdict(dict)

        # Track IP to MAC mappings for ARP spoof detection
        self.arp_bindings: Dict[str, str] = {}

    def inspect_packet(self, packet: DissectedPacket) -> List[SecurityAlert]:
        new_alerts = []
        now = time.time()

        # 1. ARP Spoofing / Poisoning Detection
        arp_layer = packet.get_layer("ARP")
        if arp_layer and isinstance(arp_layer, ARPLayer):
            if arp_layer.operation == ARP_OP_REPLY:
                ip = arp_layer.sender_ip
                mac = arp_layer.sender_mac
                if ip in self.arp_bindings and self.arp_bindings[ip] != mac:
                    alert = SecurityAlert(
                        alert_type="ARP_SPOOFING_DETECTED",
                        severity="CRITICAL",
                        source_ip=ip,
                        target_ip="BROADCAST",
                        description=f"IP {ip} MAC conflict! Previous: {self.arp_bindings[ip]}, New: {mac}",
                        timestamp=now
                    )
                    self.alerts.append(alert)
                    new_alerts.append(alert)
                self.arp_bindings[ip] = mac

        # 2. TCP SYN Flood & Port Scan Detection
        ip_layer: IPv4Layer = packet.get_layer("IPv4")  # type: ignore
        tcp_layer: TCPLayer = packet.get_layer("TCP")  # type: ignore

        if ip_layer and tcp_layer:
            src_ip = ip_layer.src_ip
            dst_ip = ip_layer.dst_ip

            if (tcp_layer.flags & TCP_SYN) and not (tcp_layer.flags & TCP_ACK):
                # Track SYN rate
                syn_times = self.syn_tracker[src_ip]
                syn_times.append(now)
                while syn_times and (now - syn_times[0] > 5.0):
                    syn_times.popleft()

                if len(syn_times) > 25:
                    alert = SecurityAlert(
                        alert_type="SYN_FLOOD_SUSPECTED",
                        severity="HIGH",
                        source_ip=src_ip,
                        target_ip=dst_ip,
                        description=f"High rate of unacknowledged SYN packets ({len(syn_times)} in 5s)",
                        timestamp=now
                    )
                    self.alerts.append(alert)
                    new_alerts.append(alert)

                # Track Port Scan (Multiple distinct destination ports)
                ports_map = self.port_tracker[src_ip]
                ports_map[tcp_layer.dst_port] = now
                
                # Prune old port touches
                expired = [p for p, ts in ports_map.items() if now - ts > 5.0]
                for p in expired:
                    del ports_map[p]

                if len(ports_map) > 8:
                    alert = SecurityAlert(
                        alert_type="PORT_SCAN_ACTIVITY",
                        severity="MEDIUM",
                        source_ip=src_ip,
                        target_ip=dst_ip,
                        description=f"Rapid scanning across {len(ports_map)} distinct destination ports",
                        timestamp=now
                    )
                    self.alerts.append(alert)
                    new_alerts.append(alert)

        return new_alerts

    def get_recent_alerts(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.alerts]
