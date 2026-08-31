"""
NetPulse Core - Dynamic Host Configuration Protocol (DHCP) Parser
RFC 2131 DHCP / BOOTP packet parsing including Magic Cookie, Message Types, and standard Options.
"""

import struct
from typing import Dict, Any, List
from server.core.packet import ProtocolLayer, PacketBuffer, mac_bytes_to_str, ip_bytes_to_str

DHCP_MAGIC_COOKIE = 0x63825363

DHCP_DISCOVER = 1
DHCP_OFFER    = 2
DHCP_REQUEST  = 3
DHCP_DECLINE  = 4
DHCP_ACK      = 5
DHCP_NAK      = 6
DHCP_RELEASE  = 7
DHCP_INFORM   = 8

DHCP_MSG_TYPES = {
    DHCP_DISCOVER: "DHCP Discover (1)",
    DHCP_OFFER:    "DHCP Offer (2)",
    DHCP_REQUEST:  "DHCP Request (3)",
    DHCP_DECLINE:  "DHCP Decline (4)",
    DHCP_ACK:      "DHCP ACK (5)",
    DHCP_NAK:      "DHCP NAK (6)",
    DHCP_RELEASE:  "DHCP Release (7)",
    DHCP_INFORM:   "DHCP Inform (8)",
}


class DHCPOption:
    def __init__(self, code: int, name: str, value: str):
        self.code = code
        self.name = name
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "name": self.name, "value": self.value}


class DHCPLayer(ProtocolLayer):
    """
    DHCP / BOOTP Message Structure (RFC 2131)
    [op: 1B] [htype: 1B] [hlen: 1B] [hops: 1B] [xid: 4B]
    [secs: 2B] [flags: 2B] [ciaddr: 4B] [yiaddr: 4B] [siaddr: 4B] [giaddr: 4B]
    [chaddr: 16B] [sname: 64B] [file: 128B] [magic cookie: 4B] [options...]
    """

    name = "DHCP"
    layer_id = 7

    def __init__(self, op: int = 1, xid: int = 0x3903F326, client_mac: str = "00:00:00:00:00:00",
                 msg_type: int = DHCP_DISCOVER):
        super().__init__()
        self.op = op          # 1 = BOOTREQUEST, 2 = BOOTREPLY
        self.htype = 1       # 1 = Ethernet
        self.hlen = 6
        self.hops = 0
        self.xid = xid
        self.secs = 0
        self.flags = 0x0000
        self.ciaddr = "0.0.0.0"
        self.yiaddr = "0.0.0.0"
        self.siaddr = "0.0.0.0"
        self.giaddr = "0.0.0.0"
        self.chaddr = client_mac
        self.msg_type = msg_type
        self.options: List[DHCPOption] = []
        self._update_fields()

    def _update_fields(self):
        op_str = "BOOTREQUEST (1)" if self.op == 1 else "BOOTREPLY (2)"
        msg_str = DHCP_MSG_TYPES.get(self.msg_type, f"Type {self.msg_type}")
        self.fields = {
            "Message Opcode": op_str,
            "Hardware Type": f"Ethernet ({self.htype})",
            "Transaction ID (XID)": f"0x{self.xid:08x}",
            "Message Type": msg_str,
            "Client IP (ciaddr)": self.ciaddr,
            "Your (Client) IP (yiaddr)": self.yiaddr,
            "Next Server IP (siaddr)": self.siaddr,
            "Relay Agent IP (giaddr)": self.giaddr,
            "Client MAC (chaddr)": self.chaddr,
            "Options": [opt.to_dict() for opt in self.options],
        }

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "DHCPLayer":
        if buffer.remaining < 240:
            raise ValueError(f"DHCP packet truncated: minimum 240 bytes required, got {buffer.remaining}")

        start_offset = buffer.offset
        op, htype, hlen, hops, xid, secs, flags = struct.unpack("!BBBBIHH", buffer.read_bytes(12))
        ciaddr = ip_bytes_to_str(buffer.read_bytes(4))
        yiaddr = ip_bytes_to_str(buffer.read_bytes(4))
        siaddr = ip_bytes_to_str(buffer.read_bytes(4))
        giaddr = ip_bytes_to_str(buffer.read_bytes(4))

        chaddr_raw = buffer.read_bytes(16)
        client_mac = mac_bytes_to_str(chaddr_raw[:6])

        _sname = buffer.read_bytes(64)
        _file = buffer.read_bytes(128)

        cookie = buffer.read_uint32()
        msg_type = DHCP_DISCOVER
        options = []

        if cookie == DHCP_MAGIC_COOKIE:
            while buffer.remaining > 0:
                code = buffer.read_uint8()
                if code == 0:  # Pad
                    continue
                if code == 255:  # End Option
                    break
                if buffer.remaining < 1:
                    break
                length = buffer.read_uint8()
                if buffer.remaining < length:
                    break
                val_bytes = buffer.read_bytes(length)

                if code == 53 and length >= 1:  # DHCP Message Type
                    msg_type = val_bytes[0]
                    options.append(DHCPOption(53, "DHCP Message Type", DHCP_MSG_TYPES.get(msg_type, str(msg_type))))
                elif code == 1 and length == 4:  # Subnet Mask
                    options.append(DHCPOption(1, "Subnet Mask", ip_bytes_to_str(val_bytes)))
                elif code == 3 and length >= 4:  # Router / Gateway
                    options.append(DHCPOption(3, "Router", ip_bytes_to_str(val_bytes[:4])))
                elif code == 6 and length >= 4:  # Domain Name Server
                    options.append(DHCPOption(6, "DNS Server", ip_bytes_to_str(val_bytes[:4])))
                elif code == 51 and length == 4:  # IP Address Lease Time
                    lease_secs = struct.unpack("!I", val_bytes)[0]
                    options.append(DHCPOption(51, "Lease Time", f"{lease_secs}s ({lease_secs // 3600} hours)"))
                elif code == 12:  # Hostname
                    options.append(DHCPOption(12, "Hostname", val_bytes.decode("ascii", errors="replace")))
                else:
                    options.append(DHCPOption(code, f"Option {code}", val_bytes.hex()))

        layer = cls(op=op, xid=xid, client_mac=client_mac, msg_type=msg_type)
        layer.ciaddr = ciaddr
        layer.yiaddr = yiaddr
        layer.siaddr = siaddr
        layer.giaddr = giaddr
        layer.options = options
        layer.raw_header = buffer.data[start_offset:buffer.offset]
        layer.payload = buffer.peek_bytes(buffer.remaining)
        layer._update_fields()
        return layer
