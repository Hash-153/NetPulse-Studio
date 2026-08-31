"""
NetPulse Core - Packet Data Structures and Binary Utilities
Provides raw packet representations, byte parsing helpers, and hex dump formatting.
Written from first principles with zero external dependencies.
"""

import struct
from typing import Dict, Any, List, Optional, Tuple


class PacketBuffer:
    """
    Reader and writer buffer for binary network packet parsing.
    Encapsulates offset tracking and safe unpacked reads.
    """

    def __init__(self, data: bytes):
        self._data = bytes(data)
        self._offset = 0

    @property
    def data(self) -> bytes:
        return self._data

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def remaining(self) -> int:
        return max(0, len(self._data) - self._offset)

    def seek(self, offset: int) -> None:
        if offset < 0 or offset > len(self._data):
            raise ValueError(f"Invalid seek offset: {offset} (buffer length: {len(self._data)})")
        self._offset = offset

    def read_bytes(self, length: int) -> bytes:
        if self._offset + length > len(self._data):
            raise ValueError(f"Buffer underflow: requested {length} bytes, {self.remaining} available")
        chunk = self._data[self._offset : self._offset + length]
        self._offset += length
        return chunk

    def read_uint8(self) -> int:
        (val,) = struct.unpack("!B", self.read_bytes(1))
        return val

    def read_uint16(self) -> int:
        (val,) = struct.unpack("!H", self.read_bytes(2))
        return val

    def read_uint32(self) -> int:
        (val,) = struct.unpack("!I", self.read_bytes(4))
        return val

    def read_uint64(self) -> int:
        (val,) = struct.unpack("!Q", self.read_bytes(8))
        return val

    def peek_bytes(self, length: int) -> bytes:
        if self._offset + length > len(self._data):
            return self._data[self._offset :]
        return self._data[self._offset : self._offset + length]


class ProtocolLayer:
    """
    Abstract base class for all protocol layers (Ethernet, IP, TCP, UDP, etc.)
    """

    name: str = "GENERIC"
    layer_id: int = 0  # 2 = DataLink, 3 = Network, 4 = Transport, 7 = Application

    def __init__(self):
        self.fields: Dict[str, Any] = {}
        self.payload: bytes = b""
        self.raw_header: bytes = b""
        self.validation_errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert layer to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "layer_id": self.layer_id,
            "fields": self.fields,
            "header_len": len(self.raw_header),
            "payload_len": len(self.payload),
            "errors": self.validation_errors,
        }

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "ProtocolLayer":
        raise NotImplementedError("Subclasses must implement parse()")

    def serialize(self) -> bytes:
        raise NotImplementedError("Subclasses must implement serialize()")


class DissectedPacket:
    """
    Represents a full multi-layer network packet analyzed by the dissector.
    """

    def __init__(self, raw_bytes: bytes, timestamp: float = 0.0):
        self.raw_bytes = raw_bytes
        self.timestamp = timestamp
        self.layers: List[ProtocolLayer] = []
        self.summary: str = ""
        self.is_valid: bool = True
        self.error_message: Optional[str] = None

    def add_layer(self, layer: ProtocolLayer) -> None:
        self.layers.append(layer)

    def get_layer(self, name: str) -> Optional[ProtocolLayer]:
        for layer in self.layers:
            if layer.name.upper() == name.upper():
                return layer
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "length": len(self.raw_bytes),
            "summary": self.summary,
            "is_valid": self.is_valid,
            "error": self.error_message,
            "layers": [l.to_dict() for l in self.layers],
            "hex_dump": format_hex_dump(self.raw_bytes),
        }


def format_hex_dump(data: bytes, bytes_per_line: int = 16) -> List[Dict[str, Any]]:
    """
    Produces a standard Wireshark / hexdump format with offset, hex bytes, and ASCII representation.
    """
    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i : i + bytes_per_line]
        hex_parts = [f"{b:02x}" for b in chunk]
        hex_str = " ".join(hex_parts)

        # ASCII representation (printable characters or dot)
        ascii_parts = [chr(b) if 32 <= b <= 126 else "." for b in chunk]
        ascii_str = "".join(ascii_parts)

        lines.append({
            "offset": f"{i:04x}",
            "hex": hex_str,
            "ascii": ascii_str,
            "raw_offset": i,
        })
    return lines


def calculate_internet_checksum(data: bytes) -> int:
    """
    Standard RFC 1071 16-bit one's complement Internet Checksum algorithm.
    Used by IPv4, ICMP, TCP, and UDP.
    """
    if len(data) % 2 == 1:
        data = data + b"\x00"

    total = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        total += word

    while (total >> 16) > 0:
        total = (total & 0xFFFF) + (total >> 16)

    return (~total) & 0xFFFF


def mac_bytes_to_str(mac: bytes) -> str:
    """Formats 6-byte MAC address to standard colon-separated hex format."""
    return ":".join(f"{b:02x}" for b in mac)


def mac_str_to_bytes(mac_str: str) -> bytes:
    """Parses colon or hyphen-separated MAC string to 6 bytes."""
    clean = mac_str.replace(":", "").replace("-", "").strip()
    if len(clean) != 12:
        raise ValueError(f"Invalid MAC address string: {mac_str}")
    return bytes.fromhex(clean)


def ip_bytes_to_str(ip: bytes) -> str:
    """Formats 4-byte IPv4 address into dotted-quad notation."""
    if len(ip) != 4:
        raise ValueError(f"IPv4 address must be 4 bytes, got {len(ip)}")
    return ".".join(str(b) for b in ip)


def ip_str_to_bytes(ip_str: str) -> bytes:
    """Parses dotted-quad IPv4 string into 4 bytes."""
    octets = [int(p) for p in ip_str.strip().split(".")]
    if len(octets) != 4 or any(o < 0 or o > 255 for o in octets):
        raise ValueError(f"Invalid IPv4 address format: {ip_str}")
    return bytes(octets)
