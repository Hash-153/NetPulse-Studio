"""
NetPulse Diagnostics - Traceroute Path & Hop Inspector
Simulates incremental TTL probing to discover intermediate routers and per-hop latencies.
"""

from typing import Dict, Any, List, Optional
import random
from server.simulator.topology import NetworkTopology
from server.simulator.routing import RoutingEngine


class TracerouteHop:
    def __init__(self, ttl: int, node_name: str, node_ip: str, node_type: str,
                 rtt_ms_list: List[float]):
        self.ttl = ttl
        self.node_name = node_name
        self.node_ip = node_ip
        self.node_type = node_type
        self.rtt_ms_list = rtt_ms_list

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hop": self.ttl,
            "name": self.node_name,
            "ip": self.node_ip,
            "type": self.node_type,
            "rtt_samples_ms": [round(r, 2) for r in self.rtt_ms_list],
            "rtt_avg_ms": round(sum(self.rtt_ms_list) / len(self.rtt_ms_list), 2) if self.rtt_ms_list else None,
        }


class TracerouteDiagnostics:
    """
    Simulates hop-by-hop traceroute execution across the network graph.
    """

    @classmethod
    def execute_traceroute(cls, topology: NetworkTopology, src_id: str, dst_id: str,
                           max_hops: int = 30, probes_per_hop: int = 3) -> Dict[str, Any]:
        src_node = topology.get_node(src_id) or topology.get_node_by_ip(src_id)
        dst_node = topology.get_node(dst_id) or topology.get_node_by_ip(dst_id)

        if not src_node:
            return {"error": f"Source node '{src_id}' not found in topology"}
        if not dst_node:
            return {"error": f"Destination node '{dst_id}' not found in topology"}

        path_res = RoutingEngine.compute_shortest_path(topology, src_node.node_id, dst_node.node_id)
        
        if not path_res.reachable:
            return {
                "source": src_node.to_dict(),
                "destination": dst_node.to_dict(),
                "target_reached": False,
                "total_hops": 0,
                "hops": [],
                "error": "Destination host unreachable: No route to host",
            }

        hops_output: List[TracerouteHop] = []

        # Iterate through path hops
        for idx, route_hop in enumerate(path_res.hops):
            ttl = idx + 1
            if ttl > max_hops:
                break

            base_rtt = route_hop.cumulative_delay * 2.0
            rtts = []
            for _ in range(probes_per_hop):
                jitter = random.uniform(0.95, 1.05)
                rtts.append(max(0.1, base_rtt * jitter))

            hop_entry = TracerouteHop(
                ttl=ttl,
                node_name=route_hop.node.name,
                node_ip=route_hop.node.ip,
                node_type=route_hop.node.node_type,
                rtt_ms_list=rtts
            )
            hops_output.append(hop_entry)

        return {
            "source": src_node.to_dict(),
            "destination": dst_node.to_dict(),
            "target_reached": True,
            "total_hops": len(hops_output),
            "hops": [h.to_dict() for h in hops_output],
        }
