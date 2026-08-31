"""
NetPulse Simulator - Network Topology Graph Model
Defines Nodes (Routers, Switches, Hosts, Gateways) and Links with bandwidth, latency, and packet loss.
"""

from typing import Dict, Any, List, Optional
import uuid


class NetworkNode:
    """
    Represents an entity in the network topology (Host, Switch, Router, Gateway, Server).
    """

    def __init__(self, node_id: str, name: str, node_type: str, ip: str, mac: str,
                 x: float = 0.0, y: float = 0.0):
        self.node_id = node_id
        self.name = name
        self.node_type = node_type  # 'host', 'router', 'switch', 'server', 'gateway'
        self.ip = ip
        self.mac = mac
        self.x = x
        self.y = y
        self.interfaces: List[Dict[str, Any]] = []
        self.arp_table: Dict[str, str] = {}  # IP -> MAC mapping
        self.routing_table: List[Dict[str, Any]] = []  # [{prefix, netmask, next_hop, interface, metric}]
        self.status: str = "online"  # 'online', 'degraded', 'offline'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.node_id,
            "name": self.name,
            "type": self.node_type,
            "ip": self.ip,
            "mac": self.mac,
            "x": self.x,
            "y": self.y,
            "status": self.status,
            "arp_entries": len(self.arp_table),
            "routes": len(self.routing_table),
        }


class NetworkLink:
    """
    Represents a full-duplex physical or virtual connection between two nodes.
    """

    def __init__(self, link_id: str, node_a_id: str, node_b_id: str,
                 bandwidth_mbps: float = 100.0, delay_ms: float = 2.0, loss_rate: float = 0.0):
        self.link_id = link_id
        self.node_a_id = node_a_id
        self.node_b_id = node_b_id
        self.bandwidth_mbps = bandwidth_mbps
        self.delay_ms = delay_ms
        self.loss_rate = loss_rate  # 0.0 to 1.0 (e.g. 0.01 = 1% loss)
        self.status: str = "active"  # 'active', 'congested', 'down'
        self.total_bytes_transmitted: int = 0
        self.total_packets_transmitted: int = 0
        self.total_packets_dropped: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.link_id,
            "source": self.node_a_id,
            "target": self.node_b_id,
            "bandwidth_mbps": self.bandwidth_mbps,
            "delay_ms": self.delay_ms,
            "loss_rate": self.loss_rate,
            "status": self.status,
            "bytes_tx": self.total_bytes_transmitted,
            "packets_tx": self.total_packets_transmitted,
            "packets_dropped": self.total_packets_dropped,
        }


class NetworkTopology:
    """
    Network Topology Manager containing all nodes and interconnecting links.
    """

    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.links: Dict[str, NetworkLink] = {}

    def add_node(self, node: NetworkNode) -> None:
        self.nodes[node.node_id] = node

    def add_link(self, link: NetworkLink) -> None:
        self.links[link.link_id] = link

    def get_node(self, node_id: str) -> Optional[NetworkNode]:
        return self.nodes.get(node_id)

    def get_node_by_ip(self, ip: str) -> Optional[NetworkNode]:
        for node in self.nodes.values():
            if node.ip == ip:
                return node
        return None

    def get_adjacent_nodes(self, node_id: str) -> List[tuple[NetworkNode, NetworkLink]]:
        """Returns list of (neighbor_node, connecting_link) for a given node."""
        neighbors = []
        for link in self.links.values():
            if link.status == "down":
                continue
            if link.node_a_id == node_id:
                other = self.nodes.get(link.node_b_id)
                if other and other.status != "offline":
                    neighbors.append((other, link))
            elif link.node_b_id == node_id:
                other = self.nodes.get(link.node_a_id)
                if other and other.status != "offline":
                    neighbors.append((other, link))
        return neighbors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "links": [l.to_dict() for l in self.links.values()],
        }

    @classmethod
    def create_enterprise_sample(cls) -> "NetworkTopology":
        """
        Creates a rich sample enterprise multi-tier topology:
        - Core Router (Backbone)
        - Distribution Switch (HQ) & Distribution Switch (Branch)
        - Web Server, Database Server, DNS/DHCP Gateway
        - Client Workstations
        """
        topo = cls()

        # Nodes
        gw = NetworkNode("gw-1", "Edge Gateway", "gateway", "198.51.100.1", "00:1A:2B:01:00:01", 400, 80)
        r1 = NetworkNode("r-core", "Core Router R1", "router", "10.0.0.1", "00:1A:2B:02:00:01", 400, 200)
        
        sw_corp = NetworkNode("sw-corp", "Corp Switch", "switch", "10.10.1.1", "00:1A:2B:03:00:01", 200, 320)
        sw_dmz = NetworkNode("sw-dmz", "DMZ Switch", "switch", "10.20.1.1", "00:1A:2B:03:00:02", 600, 320)

        srv_web = NetworkNode("srv-web", "Web App Server", "server", "10.20.1.10", "00:1A:2B:04:00:10", 520, 450)
        srv_db = NetworkNode("srv-db", "Database Server", "server", "10.20.1.20", "00:1A:2B:04:00:20", 680, 450)
        srv_dns = NetworkNode("srv-dns", "DNS Server", "server", "10.0.0.53", "00:1A:2B:04:00:53", 600, 150)

        pc1 = NetworkNode("pc-eng1", "Engineering PC", "host", "10.10.1.101", "00:1A:2B:05:00:01", 120, 450)
        pc2 = NetworkNode("pc-sales1", "Sales Laptop", "host", "10.10.1.102", "00:1A:2B:05:00:02", 280, 450)

        for n in [gw, r1, sw_corp, sw_dmz, srv_web, srv_db, srv_dns, pc1, pc2]:
            topo.add_node(n)

        # Links
        links = [
            NetworkLink("link-gw-r1", "gw-1", "r-core", bandwidth_mbps=1000, delay_ms=1.2),
            NetworkLink("link-r1-dns", "r-core", "srv-dns", bandwidth_mbps=1000, delay_ms=0.5),
            NetworkLink("link-r1-corp", "r-core", "sw-corp", bandwidth_mbps=1000, delay_ms=1.5),
            NetworkLink("link-r1-dmz", "r-core", "sw-dmz", bandwidth_mbps=1000, delay_ms=1.0),
            NetworkLink("link-corp-pc1", "sw-corp", "pc-eng1", bandwidth_mbps=100, delay_ms=0.8),
            NetworkLink("link-corp-pc2", "sw-corp", "pc-sales1", bandwidth_mbps=100, delay_ms=0.9),
            NetworkLink("link-dmz-web", "sw-dmz", "srv-web", bandwidth_mbps=1000, delay_ms=0.4),
            NetworkLink("link-dmz-db", "sw-dmz", "srv-db", bandwidth_mbps=1000, delay_ms=0.3),
        ]

        for l in links:
            topo.add_link(l)

        return topo
