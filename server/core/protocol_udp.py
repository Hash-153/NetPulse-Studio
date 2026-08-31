"""
NetPulse Core - User Datagram Protocol (UDP) Parser
RFC 768 UDP datagram modeling with length calculation and checksum support.
"""

import struct
from typing import Dict, Any
from server.core.packet import ProtocolLayer, PacketBuffer, calculate_internet_checksum, ip_str_to_bytes


class UDPLayer(ProtocolLayer):
    """
    UDP Datagram Structure (RFC 768)
    [Source Port: 2B] [Destination Port: 2B]
    [Length: 2B] [Checksum: 2B] [Payload Data]
    """

    name = "UDP"
    layer_id = 4

    def __init__(self, src_port: int = 53, dst_port: int = 53, data: bytes = b""):
        super().__init__()
        self.src_port = src_port
        self.dst_port = dst_port
        self.length = 8 + len(data)
        self.checksum = 0
        self.payload = data
        self._update_fields()

    def _update_fields(self):
        self.fields = {
            "Source Port": self.src_port,
            "Destination Port": self.dst_port,
            "Length": f"{self.length} bytes",
            "Checksum": f"0x{self.checksum:04x}",
            "Payload Size": f"{len(self.payload)} bytes",
        }

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "UDPLayer":
        if buffer.remaining < 8:
            raise ValueError(f"UDP packet truncated: minimum 8 bytes required, got {buffer.remaining}")

        start_offset = buffer.offset
        src_port, dst_port, length, checksum = struct.unpack("!HHHH", buffer.read_bytes(8))

        layer = cls(src_port=src_port, dst_port=dst_port)
        layer.length = length
        layer.checksum = checksum
        layer.raw_header = buffer.data[start_offset:buffer.offset]

        payload_len = max(0, length - 8)
        layer.payload = buffer.read_bytes(min(payload_len, buffer.remaining))
        layer._update_fields()
        return layer

    def compute_checksum(self, src_ip: str, dst_ip: str) -> int:
        src_bytes = ip_str_to_bytes(src_ip)
        dst_bytes = ip_str_to_bytes(dst_ip)
        pseudo_header = struct.pack("!4s4sBBH", src_bytes, dst_bytes, 0, 17, self.length)
        udp_header_no_csum = struct.pack("!HHHH", self.src_port, self.dst_port, self.length, 0)
        packet_for_csum = pseudo_header + udp_header_no_csum + self.payload
        csum = calculate_internet_checksum(packet_for_csum)
        return 0xFFFF if csum == 0 else csum

    def serialize(self, src_ip: str = "127.0.0.1", dst_ip: str = "127.0.0.1") -> bytes:
        self.length = 8 + len(self.payload)
        self.checksum = self.compute_checksum(src_ip, dst_ip)
        self.raw_header = struct.pack("!HHHH", self.src_port, self.dst_port, self.length, self.checksum)
        self._update_fields()
        return self.raw_header + self.payload
