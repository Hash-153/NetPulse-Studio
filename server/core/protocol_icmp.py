"""
NetPulse Core - Internet Control Message Protocol (ICMP) Parser
RFC 792 ICMPv4 modeling for Echo Request, Echo Reply, Destination Unreachable, and Time Exceeded.
"""

import struct
from typing import Dict, Any
from server.core.packet import ProtocolLayer, PacketBuffer, calculate_internet_checksum

ICMP_ECHO_REPLY        = 0
ICMP_DEST_UNREACHABLE  = 3
ICMP_ECHO_REQUEST      = 8
ICMP_TIME_EXCEEDED     = 11

ICMP_TYPE_NAMES = {
    ICMP_ECHO_REPLY:       "Echo Reply (0)",
    ICMP_DEST_UNREACHABLE: "Destination Unreachable (3)",
    ICMP_ECHO_REQUEST:     "Echo Request (8)",
    ICMP_TIME_EXCEEDED:    "Time Exceeded (TTL expired) (11)",
}


class ICMPLayer(ProtocolLayer):
    """
    ICMPv4 Packet Structure
    [Type: 1B] [Code: 1B] [Checksum: 2B]
    [Identifier: 2B] [Sequence Number: 2B] [Payload Data]
    """

    name = "ICMP"
    layer_id = 3

    def __init__(self, icmp_type: int = ICMP_ECHO_REQUEST, code: int = 0,
                 identifier: int = 1, sequence: int = 1, data: bytes = b""):
        super().__init__()
        self.icmp_type = icmp_type
        self.code = code
        self.checksum = 0
        self.identifier = identifier
        self.sequence = sequence
        self.payload = data
        self._update_fields()

    def _update_fields(self):
        type_str = ICMP_TYPE_NAMES.get(self.icmp_type, f"Type {self.icmp_type}")
        self.fields = {
            "Type": type_str,
            "Code": self.code,
            "Checksum": f"0x{self.checksum:04x}",
            "Identifier": f"0x{self.identifier:04x} ({self.identifier})",
            "Sequence Number": f"0x{self.sequence:04x} ({self.sequence})",
            "Payload Size": f"{len(self.payload)} bytes",
        }

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "ICMPLayer":
        if buffer.remaining < 8:
            raise ValueError(f"ICMP packet truncated: minimum 8 bytes required, got {buffer.remaining}")

        start_offset = buffer.offset
        icmp_type, code, checksum, identifier, sequence = struct.unpack("!BBHHH", buffer.read_bytes(8))

        layer = cls(
            icmp_type=icmp_type,
            code=code,
            identifier=identifier,
            sequence=sequence
        )
        layer.checksum = checksum
        layer.raw_header = buffer.data[start_offset:buffer.offset]
        layer.payload = buffer.read_bytes(buffer.remaining)

        # Verify Checksum
        full_packet = layer.raw_header + layer.payload
        calc_csum = calculate_internet_checksum(full_packet)
        if calc_csum != 0 and calc_csum != 0xFFFF:
            layer.validation_errors.append(f"ICMP checksum mismatch: got 0x{checksum:04x}")

        layer._update_fields()
        return layer

    def serialize(self) -> bytes:
        # Zero checksum header
        raw_no_csum = struct.pack(
            "!BBHHH",
            self.icmp_type,
            self.code,
            0,
            self.identifier,
            self.sequence
        ) + self.payload

        self.checksum = calculate_internet_checksum(raw_no_csum)
        self.raw_header = struct.pack(
            "!BBHHH",
            self.icmp_type,
            self.code,
            self.checksum,
            self.identifier,
            self.sequence
        )
        self._update_fields()
        return self.raw_header + self.payload
