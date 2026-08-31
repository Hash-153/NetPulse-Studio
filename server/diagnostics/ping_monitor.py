"""
NetPulse Diagnostics - Ping Latency & Jitter Monitor
Calculates Round-Trip Time (RTT), RFC 3550 Interarrival Jitter, and Packet Loss statistics.
"""

import math
import random
import time
from typing import Dict, Any, List, Optional
from server.simulator.topology import NetworkTopology
from server.simulator.routing import RoutingEngine


class PingProbeResult:
    def __init__(self, sequence: int, rtt_ms: Optional[float], ttl: int, status: str):
        self.sequence = sequence
        self.rtt_ms = rtt_ms
        self.ttl = ttl
        self.status = status  # 'SUCCESS', 'TIMEOUT', 'UNREACHABLE', 'DROPPED'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "rtt_ms": round(self.rtt_ms, 2) if self.rtt_ms is not None else None,
            "ttl": self.ttl,
            "status": self.status,
        }


class PingDiagnostics:
    """
    Executes a sequence of simulated or topology-backed ICMP Echo probes.
    """

    @classmethod
    def execute_ping(cls, topology: NetworkTopology, src_id: str, dst_id: str,
                     count: int = 4, packet_size_bytes: int = 64) -> Dict[str, Any]:
        src_node = topology.get_node(src_id) or topology.get_node_by_ip(src_id)
        dst_node = topology.get_node(dst_id) or topology.get_node_by_ip(dst_id)

        if not src_node:
            return {"error": f"Source node '{src_id}' not found in topology"}
        if not dst_node:
            return {"error": f"Destination node '{dst_id}' not found in topology"}

        # Calculate path via routing engine
        path_res = RoutingEngine.compute_shortest_path(topology, src_node.node_id, dst_node.node_id)
        
        probes: List[PingProbeResult] = []
        rtt_list: List[float] = []

        if not path_res.reachable:
            for i in range(1, count + 1):
                probes.append(PingProbeResult(sequence=i, rtt_ms=None, ttl=0, status="UNREACHABLE"))
            return {
                "source": src_node.to_dict(),
                "destination": dst_node.to_dict(),
                "packets_transmitted": count,
                "packets_received": 0,
                "packet_loss_percent": 100.0,
                "probes": [p.to_dict() for p in probes],
                "rtt_min_ms": None,
                "rtt_avg_ms": None,
                "rtt_max_ms": None,
                "rtt_mdev_ms": None,
                "jitter_ms": None,
            }

        base_latency = path_res.total_latency * 2.0  # RTT is round-trip

        for i in range(1, count + 1):
            # Simulate slight natural jitter variance (±10%)
            jitter_factor = random.uniform(0.92, 1.08)
            probe_rtt = max(0.2, base_latency * jitter_factor)
            
            # Check for simulated packet loss on links along the path
            is_lost = False
            for hop in path_res.hops:
                if hop.link and random.random() < hop.link.loss_rate:
                    is_lost = True
                    break

            if is_lost:
                probes.append(PingProbeResult(sequence=i, rtt_ms=None, ttl=64 - path_res.total_hops, status="DROPPED"))
            else:
                probes.append(PingProbeResult(sequence=i, rtt_ms=probe_rtt, ttl=64 - path_res.total_hops, status="SUCCESS"))
                rtt_list.append(probe_rtt)

        # Compute summary statistics
        transmitted = count
        received = len(rtt_list)
        loss_pct = round(((transmitted - received) / transmitted) * 100.0, 1)

        rtt_min = min(rtt_list) if rtt_list else None
        rtt_max = max(rtt_list) if rtt_list else None
        rtt_avg = (sum(rtt_list) / len(rtt_list)) if rtt_list else None

        # Standard deviation (mdev) & RFC 3550 Jitter calculation
        rtt_mdev = None
        jitter = None
        if len(rtt_list) > 1 and rtt_avg is not None:
            variance = sum((x - rtt_avg) ** 2 for x in rtt_list) / len(rtt_list)
            rtt_mdev = round(math.sqrt(variance), 2)

            # Jitter calculation: D(i,j) = |(R_j - S_j) - (R_i - S_i)|
            diffs = [abs(rtt_list[k] - rtt_list[k - 1]) for k in range(1, len(rtt_list))]
            jitter = round(sum(diffs) / len(diffs), 2)

        return {
            "source": src_node.to_dict(),
            "destination": dst_node.to_dict(),
            "packets_transmitted": transmitted,
            "packets_received": received,
            "packet_loss_percent": loss_pct,
            "probes": [p.to_dict() for p in probes],
            "rtt_min_ms": round(rtt_min, 2) if rtt_min is not None else None,
            "rtt_avg_ms": round(rtt_avg, 2) if rtt_avg is not None else None,
            "rtt_max_ms": round(rtt_max, 2) if rtt_max is not None else None,
            "rtt_mdev_ms": rtt_mdev,
            "jitter_ms": jitter,
        }
