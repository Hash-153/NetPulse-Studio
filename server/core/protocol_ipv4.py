"""
NetPulse Core - Internet Protocol Version 4 (IPv4) Parser
Handles IPv4 header structure, fragmentation flags, TTL, protocol dispatch, and RFC 791 checksum.
"""

import struct
from typing import Dict, Any, List
from server.core.packet import (
    ProtocolLayer, PacketBuffer, calculate_internet_checksum,
    ip_bytes_to_str, ip_str_to_bytes
)

PROTO_ICMP = 1
PROTO_TCP  = 6
PROTO_UDP  = 17

PROTOCOL_NAMES = {
    PROTO_ICMP: "ICMP (1)",
    PROTO_TCP:  "TCP (6)",
    PROTO_UDP:  "UDP (17)",
}


class IPv4Layer(ProtocolLayer):
    """
    IPv4 Header Parser (RFC 791)
    [Ver(4b)+IHL(4b)] [DSCP(6b)+ECN(2b)] [Total Length: 2B]
    [Identification: 2B] [Flags(3b)+FragOffset(13b)]
    [TTL: 1B] [Protocol: 1B] [Header Checksum: 2B]
    [Source IP: 4B] [Destination IP: 4B] [Options if IHL > 5]
    """

    name = "IPv4"
    layer_id = 3

    def __init__(self, src_ip: str = "127.0.0.1", dst_ip: str = "127.0.0.1",
                 protocol: int = PROTO_TCP, ttl: int = 64, identification: int = 54321,
                 dscp: int = 0, ecn: int = 0, flags: int = 0x02, frag_offset: int = 0):
        super().__init__()
        self.version = 4
        self.ihl = 5  # 5 32-bit words = 20 bytes
        self.dscp = dscp
        self.ecn = ecn
        self.total_length = 20
        self.identification = identification
        self.flags = flags  # 0x02 = DF (Don't Fragment)
        self.frag_offset = frag_offset
        self.ttl = ttl
        self.protocol = protocol
        self.checksum = 0
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.options = b""
        self._update_fields()

    def _update_fields(self):
        flag_str = []
        if self.flags & 0x04:
            flag_str.append("Reserved")
        if self.flags & 0x02:
            flag_str.append("DF (Don't Fragment)")
        if self.flags & 0x01:
            flag_str.append("MF (More Fragments)")
        flag_repr = ", ".join(flag_str) if flag_str else "None"

        proto_name = PROTOCOL_NAMES.get(self.protocol, f"Unknown ({self.protocol})")

        self.fields = {
            "Version": self.version,
            "Header Length (IHL)": f"{self.ihl * 4} bytes ({self.ihl})",
            "Differentiated Services (DSCP)": f"0x{self.dscp:02x}",
            "Explicit Congestion Notification (ECN)": f"0x{self.ecn:02x}",
            "Total Length": self.total_length,
            "Identification": f"0x{self.identification:04x} ({self.identification})",
            "Flags": f"0x{self.flags:02x} ({flag_repr})",
            "Fragment Offset": self.frag_offset,
            "Time to Live (TTL)": self.ttl,
            "Protocol": proto_name,
            "Header Checksum": f"0x{self.checksum:04x}",
            "Source IP Address": self.src_ip,
            "Destination IP Address": self.dst_ip,
        }

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "IPv4Layer":
        if buffer.remaining < 20:
            raise ValueError(f"IPv4 packet truncated: minimum 20 bytes required, got {buffer.remaining}")

        start_offset = buffer.offset
        v_ihl = buffer.read_uint8()
        version = (v_ihl >> 4) & 0x0F
        ihl = v_ihl & 0x0F

        if version != 4:
            raise ValueError(f"Invalid IPv4 version: {version}")
        if ihl < 5:
            raise ValueError(f"Invalid IPv4 IHL: {ihl} (minimum 5 words)")

        header_len = ihl * 4
        if buffer.remaining + 1 < header_len:
            raise ValueError(f"IPv4 options truncated: expected {header_len} bytes")

        tos = buffer.read_uint8()
        dscp = (tos >> 2) & 0x3F
        ecn = tos & 0x03

        total_length = buffer.read_uint16()
        identification = buffer.read_uint16()
        flags_frag = buffer.read_uint16()
        flags = (flags_frag >> 13) & 0x07
        frag_offset = flags_frag & 0x1FFF

        ttl = buffer.read_uint8()
        protocol = buffer.read_uint8()
        checksum = buffer.read_uint16()

        src_raw = buffer.read_bytes(4)
        dst_raw = buffer.read_bytes(4)

        options = b""
        if ihl > 5:
            options = buffer.read_bytes(header_len - 20)

        layer = cls(
            src_ip=ip_bytes_to_str(src_raw),
            dst_ip=ip_bytes_to_str(dst_raw),
            protocol=protocol,
            ttl=ttl,
            identification=identification,
            dscp=dscp,
            ecn=ecn,
            flags=flags,
            frag_offset=frag_offset
        )
        layer.ihl = ihl
        layer.total_length = total_length
        layer.checksum = checksum
        layer.options = options
        layer.raw_header = buffer.data[start_offset:buffer.offset]

        # Verify Header Checksum
        calculated_csum = calculate_internet_checksum(layer.raw_header)
        if calculated_csum != 0 and calculated_csum != 0xFFFF:
            layer.validation_errors.append(f"Checksum mismatch: received 0x{checksum:04x}")

        payload_len = max(0, total_length - header_len)
        layer.payload = buffer.read_bytes(min(payload_len, buffer.remaining))
        layer._update_fields()
        return layer

    def serialize(self) -> bytes:
        v_ihl = (self.version << 4) | (self.ihl & 0x0F)
        tos = ((self.dscp & 0x3F) << 2) | (self.ecn & 0x03)
        flags_frag = ((self.flags & 0x07) << 13) | (self.frag_offset & 0x1FFF)
        
        # Calculate total length
        header_len = 20 + len(self.options)
        self.ihl = header_len // 4
        self.total_length = header_len + len(self.payload)

        # Build zero-checksum header for calculation
        header_no_csum = struct.pack(
            "!BBHHHBBH4s4s",
            v_ihl,
            tos,
            self.total_length,
            self.identification,
            flags_frag,
            self.ttl,
            self.protocol,
            0,
            ip_str_to_bytes(self.src_ip),
            ip_str_to_bytes(self.dst_ip)
        ) + self.options

        self.checksum = calculate_internet_checksum(header_no_csum)

        self.raw_header = struct.pack(
            "!BBHHHBBH4s4s",
            v_ihl,
            tos,
            self.total_length,
            self.identification,
            flags_frag,
            self.ttl,
            self.protocol,
            self.checksum,
            ip_str_to_bytes(self.src_ip),
            ip_str_to_bytes(self.dst_ip)
        ) + self.options

        self._update_fields()
        return self.raw_header + self.payload
