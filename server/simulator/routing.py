"""
NetPulse Simulator - Shortest Path First (SPF) Routing Engine
Implements Dijkstra algorithm for dynamic route calculation, hop-by-hop forwarding, and metric weighting.
"""

import heapq
from typing import Dict, List, Optional, Tuple, Any
from server.simulator.topology import NetworkTopology, NetworkNode, NetworkLink


class RouteHop:
    def __init__(self, node: NetworkNode, link: Optional[NetworkLink], cumulative_delay: float):
        self.node = node
        self.link = link
        self.cumulative_delay = cumulative_delay

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node.node_id,
            "node_name": self.node.name,
            "node_ip": self.node.ip,
            "node_type": self.node.node_type,
            "link_id": self.link.link_id if self.link else None,
            "delay_ms": round(self.cumulative_delay, 2),
        }


class RoutingResult:
    def __init__(self, source_id: str, target_id: str, reachable: bool = False,
                 hops: Optional[List[RouteHop]] = None, total_latency: float = 0.0,
                 min_bandwidth: float = 0.0, total_hops: int = 0):
        self.source_id = source_id
        self.target_id = target_id
        self.reachable = reachable
        self.hops = hops or []
        self.total_latency = total_latency
        self.min_bandwidth = min_bandwidth
        self.total_hops = total_hops

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "reachable": self.reachable,
            "total_hops": self.total_hops,
            "total_latency_ms": round(self.total_latency, 2),
            "bottleneck_bandwidth_mbps": self.min_bandwidth,
            "path": [h.to_dict() for h in self.hops],
        }


class RoutingEngine:
    """
    Computes optimal paths across the network topology using Shortest Path First (SPF).
    Calculates cost based on link latency + inverted bandwidth weight.
    """

    @classmethod
    def compute_shortest_path(cls, topology: NetworkTopology, src_node_id: str,
                              dst_node_id: str) -> RoutingResult:
        if src_node_id not in topology.nodes or dst_node_id not in topology.nodes:
            return RoutingResult(src_node_id, dst_node_id, reachable=False)

        if src_node_id == dst_node_id:
            src_node = topology.nodes[src_node_id]
            return RoutingResult(
                src_node_id, dst_node_id, reachable=True,
                hops=[RouteHop(src_node, None, 0.0)], total_latency=0.0, min_bandwidth=10000.0, total_hops=1
            )

        # Dijkstra priority queue: (cost, current_node_id)
        pq: List[Tuple[float, str]] = []
        heapq.heappush(pq, (0.0, src_node_id))

        distances: Dict[str, float] = {src_node_id: 0.0}
        previous: Dict[str, Tuple[Optional[str], Optional[NetworkLink]]] = {src_node_id: (None, None)}

        while pq:
            current_cost, current_id = heapq.heappop(pq)

            if current_id == dst_node_id:
                break

            if current_cost > distances.get(current_id, float("inf")):
                continue

            for neighbor, link in topology.get_adjacent_nodes(current_id):
                # Cost metric: latency + 1000 / bandwidth
                link_cost = link.delay_ms + (100.0 / max(1.0, link.bandwidth_mbps))
                new_cost = current_cost + link_cost

                if new_cost < distances.get(neighbor.node_id, float("inf")):
                    distances[neighbor.node_id] = new_cost
                    previous[neighbor.node_id] = (current_id, link)
                    heapq.heappush(pq, (new_cost, neighbor.node_id))

        if dst_node_id not in previous or (previous[dst_node_id][0] is None and dst_node_id != src_node_id):
            return RoutingResult(src_node_id, dst_node_id, reachable=False)

        # Reconstruct path from destination to source
        path_nodes: List[NetworkNode] = []
        path_links: List[Optional[NetworkLink]] = []
        curr = dst_node_id

        while curr is not None:
            path_nodes.append(topology.nodes[curr])
            prev_id, connecting_link = previous[curr]
            if connecting_link:
                path_links.append(connecting_link)
            curr = prev_id

        path_nodes.reverse()
        path_links.reverse()
        path_links.append(None)  # Final hop has no outbound link

        # Compute cumulative stats
        hops: List[RouteHop] = []
        cum_delay = 0.0
        min_bw = float("inf")

        for idx, node in enumerate(path_nodes):
            connecting_link = path_links[idx]
            hops.append(RouteHop(node, connecting_link, cum_delay))
            if connecting_link:
                cum_delay += connecting_link.delay_ms
                min_bw = min(min_bw, connecting_link.bandwidth_mbps)

        if min_bw == float("inf"):
            min_bw = 1000.0

        return RoutingResult(
            source_id=src_node_id,
            target_id=dst_node_id,
            reachable=True,
            hops=hops,
            total_latency=cum_delay,
            min_bandwidth=min_bw,
            total_hops=len(hops)
        )
