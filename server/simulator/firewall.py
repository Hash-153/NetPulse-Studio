"""
NetPulse Simulator - Access Control List (ACL) & Stateful Firewall Engine
Evaluates packet headers against customizable ordered security filtering rules.
"""

from typing import Dict, Any, List, Optional
from server.core.packet import DissectedPacket, ip_str_to_bytes
from server.core.protocol_ipv4 import IPv4Layer
from server.core.protocol_tcp import TCPLayer
from server.core.protocol_udp import UDPLayer


def ip_in_network(ip_str: str, cidr_str: str) -> bool:
    """Checks if an IPv4 address string matches a CIDR block (e.g. 10.0.0.0/24 or 'any')."""
    if cidr_str.lower() in ("any", "*", "0.0.0.0/0"):
        return True

    try:
        if "/" in cidr_str:
            net_ip, prefix_len_str = cidr_str.split("/")
            prefix_len = int(prefix_len_str)
        else:
            net_ip = cidr_str
            prefix_len = 32

        ip_raw = ip_str_to_bytes(ip_str)
        net_raw = ip_str_to_bytes(net_ip)

        ip_int = int.from_bytes(ip_raw, "big")
        net_int = int.from_bytes(net_raw, "big")

        mask = ((1 << 32) - 1) ^ ((1 << (32 - prefix_len)) - 1) if prefix_len < 32 else 0xFFFFFFFF
        return (ip_int & mask) == (net_int & mask)
    except Exception:
        return False


def port_in_range(port: int, range_str: str) -> bool:
    """Checks if a port matches a port or port range string (e.g. '80', '8000-8080', 'any')."""
    if str(range_str).lower() in ("any", "*", "0"):
        return True

    try:
        if "-" in str(range_str):
            start_p, end_p = map(int, str(range_str).split("-"))
            return start_p <= port <= end_p
        return int(range_str) == port
    except Exception:
        return False


class ACLRule:
    """
    Firewall Rule definition.
    Action: 'ALLOW' or 'DENY'
    Protocol: 'TCP', 'UDP', 'ICMP', 'ANY'
    """

    def __init__(self, rule_id: int, action: str, protocol: str,
                 src_ip: str = "any", dst_ip: str = "any",
                 src_port: str = "any", dst_port: str = "any",
                 description: str = ""):
        self.rule_id = rule_id
        self.action = action.upper()  # 'ALLOW' or 'DENY'
        self.protocol = protocol.upper()
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = src_port
        self.dst_port = dst_port
        self.description = description
        self.match_count = 0

    def matches(self, src_ip: str, dst_ip: str, proto_name: str, src_port: int, dst_port: int) -> bool:
        if self.protocol != "ANY" and self.protocol != proto_name.upper():
            return False
        if not ip_in_network(src_ip, self.src_ip):
            return False
        if not ip_in_network(dst_ip, self.dst_ip):
            return False
        if not port_in_range(src_port, self.src_port):
            return False
        if not port_in_range(dst_port, self.dst_port):
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.rule_id,
            "action": self.action,
            "protocol": self.protocol,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "description": self.description,
            "match_count": self.match_count,
        }


class FirewallEngine:
    """
    Ordered Rule-based Stateful Packet Filter.
    """

    def __init__(self, default_policy: str = "DENY"):
        self.default_policy = default_policy.upper()
        self.rules: List[ACLRule] = []
        self._init_default_rules()

    def _init_default_rules(self):
        # Default enterprise starter security rule set
        self.rules = [
            ACLRule(10, "ALLOW", "TCP", "any", "10.20.1.10", "any", "80", "Allow HTTP to Web App Server"),
            ACLRule(20, "ALLOW", "TCP", "any", "10.20.1.10", "any", "443", "Allow HTTPS to Web App Server"),
            ACLRule(30, "ALLOW", "UDP", "any", "10.0.0.53", "any", "53", "Allow DNS Queries"),
            ACLRule(40, "ALLOW", "TCP", "10.20.1.10", "10.20.1.20", "any", "5432", "Allow Web to DB PostgreSQL"),
            ACLRule(50, "DENY", "TCP", "any", "10.20.1.20", "any", "5432", "Block Direct External Access to DB"),
            ACLRule(60, "ALLOW", "ICMP", "10.10.0.0/16", "any", "any", "any", "Allow Internal ICMP Ping"),
            ACLRule(70, "ALLOW", "TCP", "10.10.1.0/24", "any", "any", "any", "Allow Corp LAN Outbound TCP"),
        ]

    def add_rule(self, rule: ACLRule) -> None:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.rule_id)

    def delete_rule(self, rule_id: int) -> bool:
        initial = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        return len(self.rules) < initial

    def evaluate_packet(self, packet: DissectedPacket) -> Dict[str, Any]:
        """Evaluates packet against ACL table and returns decision dictionary."""
        ip_layer: Optional[IPv4Layer] = packet.get_layer("IPv4")  # type: ignore
        if not ip_layer:
            return {"action": "ALLOW", "rule_id": None, "reason": "Non-IPv4 frame passed by default"}

        src_ip = ip_layer.src_ip
        dst_ip = ip_layer.dst_ip
        proto_name = "IP"
        src_port = 0
        dst_port = 0

        tcp_layer: Optional[TCPLayer] = packet.get_layer("TCP")  # type: ignore
        if tcp_layer:
            proto_name = "TCP"
            src_port = tcp_layer.src_port
            dst_port = tcp_layer.dst_port

        udp_layer: Optional[UDPLayer] = packet.get_layer("UDP")  # type: ignore
        if udp_layer:
            proto_name = "UDP"
            src_port = udp_layer.src_port
            dst_port = udp_layer.dst_port

        icmp_layer = packet.get_layer("ICMP")
        if icmp_layer:
            proto_name = "ICMP"

        for rule in self.rules:
            if rule.matches(src_ip, dst_ip, proto_name, src_port, dst_port):
                rule.match_count += 1
                return {
                    "action": rule.action,
                    "rule_id": rule.rule_id,
                    "rule_description": rule.description,
                    "reason": f"Matched Rule #{rule.rule_id} ({rule.action}): {rule.description}"
                }

        return {
            "action": self.default_policy,
            "rule_id": None,
            "reason": f"No rule matched, applied default policy ({self.default_policy})"
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_policy": self.default_policy,
            "rules": [r.to_dict() for r in self.rules],
        }
