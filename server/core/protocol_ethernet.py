"""
NetPulse Core - Ethernet II & 802.1Q VLAN Protocol Parser
Handles MAC addresses, EtherType dispatching, and VLAN tags.
"""

import struct
from typing import Dict, Any, Tuple
from server.core.packet import ProtocolLayer, PacketBuffer, mac_bytes_to_str, mac_str_to_bytes

ETHERTYPE_IPV4 = 0x0800
ETHERTYPE_ARP  = 0x0806
ETHERTYPE_VLAN = 0x8100
ETHERTYPE_IPV6 = 0x86DD

ETHERTYPE_NAMES = {
    ETHERTYPE_IPV4: "IPv4",
    ETHERTYPE_ARP:  "ARP",
    ETHERTYPE_VLAN: "802.1Q VLAN",
    ETHERTYPE_IPV6: "IPv6",
}


class EthernetLayer(ProtocolLayer):
    """
    Ethernet II Frame Parser
    [Destination MAC: 6B] [Source MAC: 6B] [Optional 802.1Q Tag: 4B] [EtherType: 2B] [Payload]
    """

    name = "Ethernet II"
    layer_id = 2

    def __init__(self, dst_mac: str = "ff:ff:ff:ff:ff:ff", src_mac: str = "00:00:00:00:00:00",
                 ethertype: int = ETHERTYPE_IPV4, vlan_id: int = 0, vlan_pri: int = 0):
        super().__init__()
        self.dst_mac = dst_mac
        self.src_mac = src_mac
        self.ethertype = ethertype
        self.vlan_id = vlan_id
        self.vlan_pri = vlan_pri
        self._update_fields()

    def _update_fields(self):
        self.fields = {
            "Destination MAC": self.dst_mac,
            "Source MAC": self.src_mac,
            "EtherType": f"0x{self.ethertype:04x} ({ETHERTYPE_NAMES.get(self.ethertype, 'Unknown')})",
            "VLAN Tagged": self.vlan_id > 0,
        }
        if self.vlan_id > 0:
            self.fields["VLAN ID"] = self.vlan_id
            self.fields["VLAN Priority"] = self.vlan_pri

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "EthernetLayer":
        if buffer.remaining < 14:
            raise ValueError(f"Ethernet frame truncated: minimum 14 bytes required, got {buffer.remaining}")

        start_offset = buffer.offset
        dst_bytes = buffer.read_bytes(6)
        src_bytes = buffer.read_bytes(6)
        ethertype = buffer.read_uint16()

        vlan_id = 0
        vlan_pri = 0

        # Handle 802.1Q VLAN Tagging
        if ethertype == ETHERTYPE_VLAN:
            if buffer.remaining < 2:
                raise ValueError("Truncated 802.1Q VLAN tag")
            tci = buffer.read_uint16()
            vlan_pri = (tci >> 13) & 0x07
            vlan_id = tci & 0x0FFF
            ethertype = buffer.read_uint16()

        layer = cls(
            dst_mac=mac_bytes_to_str(dst_bytes),
            src_mac=mac_bytes_to_str(src_bytes),
            ethertype=ethertype,
            vlan_id=vlan_id,
            vlan_pri=vlan_pri
        )
        layer.raw_header = buffer.data[start_offset:buffer.offset]
        layer.payload = buffer.peek_bytes(buffer.remaining)
        return layer

    def serialize(self) -> bytes:
        dst = mac_str_to_bytes(self.dst_mac)
        src = mac_str_to_bytes(self.src_mac)
        if self.vlan_id > 0:
            tci = ((self.vlan_pri & 0x07) << 13) | (self.vlan_id & 0x0FFF)
            header = struct.pack("!6s6sHHH", dst, src, ETHERTYPE_VLAN, tci, self.ethertype)
        else:
            header = struct.pack("!6s6sH", dst, src, self.ethertype)
        self.raw_header = header
        return header + self.payload
