"""
NetPulse Core - Address Resolution Protocol (ARP) Parser
RFC 826 ARP Request and Reply packet modeling.
"""

import struct
from typing import Dict, Any
from server.core.packet import (
    ProtocolLayer, PacketBuffer, mac_bytes_to_str, mac_str_to_bytes,
    ip_bytes_to_str, ip_str_to_bytes
)

ARP_OP_REQUEST = 1
ARP_OP_REPLY   = 2

OPCODE_NAMES = {
    ARP_OP_REQUEST: "Request (1)",
    ARP_OP_REPLY:   "Reply (2)",
}


class ARPLayer(ProtocolLayer):
    """
    ARP Packet Structure
    [HTYPE: 2B] [PTYPE: 2B] [HLEN: 1B] [PLEN: 1B] [OPER: 2B]
    [SHA: 6B] [SPA: 4B] [THA: 6B] [TPA: 4B]
    """

    name = "ARP"
    layer_id = 2

    def __init__(self, operation: int = ARP_OP_REQUEST,
                 sender_mac: str = "00:00:00:00:00:00", sender_ip: str = "0.0.0.0",
                 target_mac: str = "00:00:00:00:00:00", target_ip: str = "0.0.0.0"):
        super().__init__()
        self.htype = 1      # Ethernet (10Mb)
        self.ptype = 0x0800 # IPv4
        self.hlen = 6
        self.plen = 4
        self.operation = operation
        self.sender_mac = sender_mac
        self.sender_ip = sender_ip
        self.target_mac = target_mac
        self.target_ip = target_ip
        self._update_fields()

    def _update_fields(self):
        op_name = OPCODE_NAMES.get(self.operation, f"Unknown ({self.operation})")
        self.fields = {
            "Hardware Type": f"Ethernet ({self.htype})",
            "Protocol Type": f"IPv4 (0x{self.ptype:04x})",
            "Hardware Size": self.hlen,
            "Protocol Size": self.plen,
            "Opcode": op_name,
            "Sender MAC Address": self.sender_mac,
            "Sender IP Address": self.sender_ip,
            "Target MAC Address": self.target_mac,
            "Target IP Address": self.target_ip,
        }

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "ARPLayer":
        if buffer.remaining < 28:
            raise ValueError(f"ARP packet truncated: minimum 28 bytes required, got {buffer.remaining}")

        start_offset = buffer.offset
        htype, ptype, hlen, plen, oper = struct.unpack("!HHBBH", buffer.read_bytes(8))
        sha_raw = buffer.read_bytes(hlen)
        spa_raw = buffer.read_bytes(plen)
        tha_raw = buffer.read_bytes(hlen)
        tpa_raw = buffer.read_bytes(plen)

        layer = cls(
            operation=oper,
            sender_mac=mac_bytes_to_str(sha_raw),
            sender_ip=ip_bytes_to_str(spa_raw),
            target_mac=mac_bytes_to_str(tha_raw),
            target_ip=ip_bytes_to_str(tpa_raw)
        )
        layer.htype = htype
        layer.ptype = ptype
        layer.hlen = hlen
        layer.plen = plen
        layer.raw_header = buffer.data[start_offset:buffer.offset]
        layer.payload = buffer.peek_bytes(buffer.remaining)
        return layer

    def serialize(self) -> bytes:
        header = struct.pack(
            "!HHBBH6s4s6s4s",
            self.htype,
            self.ptype,
            self.hlen,
            self.plen,
            self.operation,
            mac_str_to_bytes(self.sender_mac),
            ip_str_to_bytes(self.sender_ip),
            mac_str_to_bytes(self.target_mac),
            ip_str_to_bytes(self.target_ip),
        )
        self.raw_header = header
        return header + self.payload
