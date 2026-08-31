"""
NetPulse Core - Transmission Control Protocol (TCP) Parser
RFC 793 / RFC 3168 TCP header structure, flags, options, sequence space, and pseudo-header checksum.
"""

import struct
from typing import Dict, Any, List, Optional
from server.core.packet import ProtocolLayer, PacketBuffer, calculate_internet_checksum, ip_str_to_bytes

TCP_FIN = 0x01
TCP_SYN = 0x02
TCP_RST = 0x04
TCP_PSH = 0x08
TCP_ACK = 0x10
TCP_URG = 0x20
TCP_ECE = 0x40
TCP_CWR = 0x80


class TCPLayer(ProtocolLayer):
    """
    TCP Header Structure (RFC 793)
    [Source Port: 2B] [Destination Port: 2B]
    [Sequence Number: 4B]
    [Acknowledgment Number: 4B]
    [Data Offset: 4b | Reserved: 3b | Flags: 9b] (2B)
    [Window Size: 2B]
    [Checksum: 2B] [Urgent Pointer: 2B]
    [Options if Data Offset > 5]
    """

    name = "TCP"
    layer_id = 4

    def __init__(self, src_port: int = 80, dst_port: int = 80,
                 seq_num: int = 1000, ack_num: int = 0,
                 flags: int = TCP_SYN, window_size: int = 65535,
                 urg_ptr: int = 0):
        super().__init__()
        self.src_port = src_port
        self.dst_port = dst_port
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.data_offset = 5  # 5 * 4 = 20 bytes
        self.flags = flags
        self.window_size = window_size
        self.checksum = 0
        self.urg_ptr = urg_ptr
        self.options = b""
        self._update_fields()

    def _update_fields(self):
        flag_names = []
        if self.flags & TCP_CWR: flag_names.append("CWR")
        if self.flags & TCP_ECE: flag_names.append("ECE")
        if self.flags & TCP_URG: flag_names.append("URG")
        if self.flags & TCP_ACK: flag_names.append("ACK")
        if self.flags & TCP_PSH: flag_names.append("PSH")
        if self.flags & TCP_RST: flag_names.append("RST")
        if self.flags & TCP_SYN: flag_names.append("SYN")
        if self.flags & TCP_FIN: flag_names.append("FIN")
        flag_str = " | ".join(flag_names) if flag_names else "None"

        self.fields = {
            "Source Port": self.src_port,
            "Destination Port": self.dst_port,
            "Sequence Number": self.seq_num,
            "Acknowledgment Number": self.ack_num,
            "Header Length": f"{self.data_offset * 4} bytes ({self.data_offset})",
            "Flags": f"0x{self.flags:03x} ({flag_str})",
            "Window Size": self.window_size,
            "Checksum": f"0x{self.checksum:04x}",
            "Urgent Pointer": self.urg_ptr,
            "Payload Size": f"{len(self.payload)} bytes",
        }

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "TCPLayer":
        if buffer.remaining < 20:
            raise ValueError(f"TCP packet truncated: minimum 20 bytes required, got {buffer.remaining}")

        start_offset = buffer.offset
        src_port, dst_port, seq_num, ack_num, offset_flags, window, checksum, urg_ptr = struct.unpack(
            "!HHIIHHHH", buffer.read_bytes(20)
        )

        data_offset = (offset_flags >> 12) & 0x0F
        flags = offset_flags & 0x01FF

        if data_offset < 5:
            raise ValueError(f"Invalid TCP data offset: {data_offset}")

        header_len = data_offset * 4
        options = b""
        if data_offset > 5:
            opt_len = header_len - 20
            if buffer.remaining < opt_len:
                raise ValueError("Truncated TCP options")
            options = buffer.read_bytes(opt_len)

        layer = cls(
            src_port=src_port,
            dst_port=dst_port,
            seq_num=seq_num,
            ack_num=ack_num,
            flags=flags,
            window_size=window,
            urg_ptr=urg_ptr
        )
        layer.data_offset = data_offset
        layer.checksum = checksum
        layer.options = options
        layer.raw_header = buffer.data[start_offset:buffer.offset]
        layer.payload = buffer.read_bytes(buffer.remaining)
        layer._update_fields()
        return layer

    def compute_checksum(self, src_ip: str, dst_ip: str) -> int:
        """Computes TCP checksum including IPv4 pseudo-header (RFC 793)."""
        src_bytes = ip_str_to_bytes(src_ip)
        dst_bytes = ip_str_to_bytes(dst_ip)
        tcp_length = (self.data_offset * 4) + len(self.payload)

        pseudo_header = struct.pack("!4s4sBBH", src_bytes, dst_bytes, 0, 6, tcp_length)

        offset_flags = (self.data_offset << 12) | (self.flags & 0x01FF)
        tcp_header_no_csum = struct.pack(
            "!HHIIHHHH",
            self.src_port,
            self.dst_port,
            self.seq_num,
            self.ack_num,
            offset_flags,
            self.window_size,
            0,
            self.urg_ptr
        ) + self.options

        packet_for_csum = pseudo_header + tcp_header_no_csum + self.payload
        return calculate_internet_checksum(packet_for_csum)

    def serialize(self, src_ip: str = "127.0.0.1", dst_ip: str = "127.0.0.1") -> bytes:
        header_len = 20 + len(self.options)
        self.data_offset = header_len // 4
        self.checksum = self.compute_checksum(src_ip, dst_ip)

        offset_flags = (self.data_offset << 12) | (self.flags & 0x01FF)
        self.raw_header = struct.pack(
            "!HHIIHHHH",
            self.src_port,
            self.dst_port,
            self.seq_num,
            self.ack_num,
            offset_flags,
            self.window_size,
            self.checksum,
            self.urg_ptr
        ) + self.options

        self._update_fields()
        return self.raw_header + self.payload
