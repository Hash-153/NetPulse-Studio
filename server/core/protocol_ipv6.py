"""
NetPulse Core - Internet Protocol Version 6 (IPv6) Parser
RFC 8200 IPv6 Fixed Header modeling with 128-bit addresses and Next Header chaining.
"""

import struct
from typing import Dict, Any
from server.core.packet import ProtocolLayer, PacketBuffer

def ipv6_bytes_to_str(raw: bytes) -> str:
    if len(raw) != 16:
        raise ValueError(f"IPv6 address must be 16 bytes, got {len(raw)}")
    words = [f"{(raw[i] << 8) + raw[i+1]:x}" for i in range(0, 16, 2)]
    return ":".join(words)

def ipv6_str_to_bytes(ip_str: str) -> bytes:
    # Basic standard full-expansion parser
    parts = ip_str.strip().split(":")
    if "" in parts:
        idx = parts.index("")
        parts.remove("")
        while len(parts) < 8:
            parts.insert(idx, "0")
    if len(parts) != 8:
        raise ValueError(f"Invalid IPv6 address format: {ip_str}")
    raw = bytearray()
    for p in parts:
        val = int(p if p else "0", 16)
        raw.extend(struct.pack("!H", val))
    return bytes(raw)


class IPv6Layer(ProtocolLayer):
    """
    IPv6 Header Structure (RFC 8200)
    [Version: 4b | Traffic Class: 8b | Flow Label: 20b] (4 bytes)
    [Payload Length: 2B] [Next Header: 1B] [Hop Limit: 1B]
    [Source IPv6: 16B] [Destination IPv6: 16B]
    """

    name = "IPv6"
    layer_id = 3

    def __init__(self, src_ip: str = "::1", dst_ip: str = "::1",
                 next_header: int = 6, hop_limit: int = 64,
                 traffic_class: int = 0, flow_label: int = 0):
        super().__init__()
        self.version = 6
        self.traffic_class = traffic_class
        self.flow_label = flow_label
        self.payload_length = 0
        self.next_header = next_header
        self.hop_limit = hop_limit
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self._update_fields()

    def _update_fields(self):
        self.fields = {
            "Version": self.version,
            "Traffic Class": f"0x{self.traffic_class:02x}",
            "Flow Label": f"0x{self.flow_label:05x}",
            "Payload Length": f"{self.payload_length} bytes",
            "Next Header": f"{self.next_header}",
            "Hop Limit": self.hop_limit,
            "Source IPv6": self.src_ip,
            "Destination IPv6": self.dst_ip,
        }

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "IPv6Layer":
        if buffer.remaining < 40:
            raise ValueError(f"IPv6 packet truncated: minimum 40 bytes required, got {buffer.remaining}")

        start_offset = buffer.offset
        w1 = buffer.read_uint32()
        version = (w1 >> 28) & 0x0F
        traffic_class = (w1 >> 20) & 0xFF
        flow_label = w1 & 0xFFFFF

        if version != 6:
            raise ValueError(f"Invalid IPv6 version: {version}")

        payload_length = buffer.read_uint16()
        next_header = buffer.read_uint8()
        hop_limit = buffer.read_uint8()

        src_raw = buffer.read_bytes(16)
        dst_raw = buffer.read_bytes(16)

        layer = cls(
            src_ip=ipv6_bytes_to_str(src_raw),
            dst_ip=ipv6_bytes_to_str(dst_raw),
            next_header=next_header,
            hop_limit=hop_limit,
            traffic_class=traffic_class,
            flow_label=flow_label
        )
        layer.payload_length = payload_length
        layer.raw_header = buffer.data[start_offset:buffer.offset]
        layer.payload = buffer.read_bytes(min(payload_length, buffer.remaining))
        layer._update_fields()
        return layer

    def serialize(self) -> bytes:
        self.payload_length = len(self.payload)
        w1 = (self.version << 28) | ((self.traffic_class & 0xFF) << 20) | (self.flow_label & 0xFFFFF)
        header = struct.pack(
            "!IHBB16s16s",
            w1,
            self.payload_length,
            self.next_header,
            self.hop_limit,
            ipv6_str_to_bytes(self.src_ip),
            ipv6_str_to_bytes(self.dst_ip)
        )
        self.raw_header = header
        self._update_fields()
        return header + self.payload
