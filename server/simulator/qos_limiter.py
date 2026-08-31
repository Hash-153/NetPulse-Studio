"""
NetPulse Simulator - Quality of Service (QoS) & Token Bucket Shaper
Models traffic policing and rate limiting algorithms (Token Bucket & Leaky Bucket).
"""

import time
from typing import Dict, Any


class TokenBucketShaper:
    """
    Token Bucket Rate Limiter (RFC 2697 / RFC 2698 modeling).
    - rate_bytes_per_sec: Continuous token replenishment rate.
    - burst_capacity_bytes: Maximum token accumulation depth.
    """

    def __init__(self, rate_bytes_per_sec: float, burst_capacity_bytes: float):
        self.rate = rate_bytes_per_sec
        self.capacity = burst_capacity_bytes
        self.tokens = burst_capacity_bytes
        self.last_update = time.time()
        self.total_conform_bytes = 0
        self.total_dropped_bytes = 0
        self.total_packets = 0

    def replenish(self) -> None:
        now = time.time()
        delta = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + (delta * self.rate))

    def consume(self, packet_size_bytes: int) -> bool:
        """
        Attempts to transmit a packet.
        Returns True if packet conforms to QoS envelope; False if dropped/exceeded.
        """
        self.replenish()
        self.total_packets += 1
        if self.tokens >= packet_size_bytes:
            self.tokens -= packet_size_bytes
            self.total_conform_bytes += packet_size_bytes
            return True
        else:
            self.total_dropped_bytes += packet_size_bytes
            return False

    def to_dict(self) -> Dict[str, Any]:
        self.replenish()
        return {
            "rate_kbps": round((self.rate * 8) / 1000, 2),
            "burst_capacity_kb": round(self.capacity / 1024, 2),
            "available_tokens_kb": round(self.tokens / 1024, 2),
            "conforming_bytes": self.total_conform_bytes,
            "dropped_bytes": self.total_dropped_bytes,
            "total_packets": self.total_packets,
        }
