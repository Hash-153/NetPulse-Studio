"""
NetPulse Core - Domain Name System (DNS) Protocol Parser
RFC 1035 DNS message parsing including Question, Answer, Nameserver, and Additional Resource Records.
"""

import struct
from typing import Dict, Any, List, Tuple
from server.core.packet import ProtocolLayer, PacketBuffer, ip_bytes_to_str, ip_str_to_bytes

DNS_TYPE_A     = 1
DNS_TYPE_NS    = 2
DNS_TYPE_CNAME = 5
DNS_TYPE_SOA   = 6
DNS_TYPE_PTR   = 12
DNS_TYPE_MX    = 15
DNS_TYPE_TXT   = 16
DNS_TYPE_AAAA  = 28

DNS_CLASS_IN = 1

RECORD_TYPE_NAMES = {
    DNS_TYPE_A: "A (IPv4)",
    DNS_TYPE_NS: "NS (Name Server)",
    DNS_TYPE_CNAME: "CNAME (Canonical Name)",
    DNS_TYPE_SOA: "SOA (Start of Authority)",
    DNS_TYPE_PTR: "PTR (Pointer)",
    DNS_TYPE_MX: "MX (Mail Exchange)",
    DNS_TYPE_TXT: "TXT (Text)",
    DNS_TYPE_AAAA: "AAAA (IPv6)",
}


def encode_dns_name(domain: str) -> bytes:
    """Encodes standard domain name into DNS wire format labels (e.g. 3www6google3com0)."""
    parts = domain.strip(".").split(".")
    raw = bytearray()
    for p in parts:
        if not p:
            continue
        p_bytes = p.encode("ascii")
        raw.append(len(p_bytes))
        raw.extend(p_bytes)
    raw.append(0)  # Null terminator label
    return bytes(raw)


def decode_dns_name(buffer: PacketBuffer, full_data: bytes) -> str:
    """Decodes DNS wire format name with support for standard RFC 1035 label compression pointers."""
    labels = []
    visited_offsets = set()
    initial_offset = buffer.offset
    jumped = False

    while True:
        if buffer.remaining < 1:
            break
        length = buffer.read_uint8()
        if length == 0:
            break

        # Check for pointer (top 2 bits set: 11000000 = 0xC0)
        if (length & 0xC0) == 0xC0:
            if buffer.remaining < 1:
                break
            second_byte = buffer.read_uint8()
            pointer = ((length & 0x3F) << 8) | second_byte
            if pointer in visited_offsets:
                break  # Prevent infinite loop on circular pointer
            visited_offsets.add(pointer)

            # Read remaining labels from pointer target
            ptr_buf = PacketBuffer(full_data)
            ptr_buf.seek(pointer)
            sub_name = decode_dns_name(ptr_buf, full_data)
            labels.append(sub_name)
            jumped = True
            break
        else:
            if buffer.remaining < length:
                break
            label = buffer.read_bytes(length).decode("latin-1", errors="replace")
            labels.append(label)

    return ".".join(l for l in labels if l)


class DNSQuestion:
    def __init__(self, qname: str, qtype: int = DNS_TYPE_A, qclass: int = DNS_CLASS_IN):
        self.qname = qname
        self.qtype = qtype
        self.qclass = qclass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.qname,
            "type": RECORD_TYPE_NAMES.get(self.qtype, f"TYPE{self.qtype}"),
            "class": "IN" if self.qclass == 1 else str(self.qclass),
        }


class DNSResourceRecord:
    def __init__(self, name: str, rtype: int, rclass: int, ttl: int, rdata: Any, rdata_str: str):
        self.name = name
        self.rtype = rtype
        self.rclass = rclass
        self.ttl = ttl
        self.rdata = rdata
        self.rdata_str = rdata_str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": RECORD_TYPE_NAMES.get(self.rtype, f"TYPE{self.rtype}"),
            "class": "IN" if self.rclass == 1 else str(self.rclass),
            "ttl": self.ttl,
            "data": self.rdata_str,
        }


class DNSLayer(ProtocolLayer):
    """
    DNS Message Structure (RFC 1035)
    [Transaction ID: 2B] [Flags: 2B]
    [Questions: 2B] [Answer RRs: 2B] [Authority RRs: 2B] [Additional RRs: 2B]
    [Questions Section...] [Answers Section...]
    """

    name = "DNS"
    layer_id = 7

    def __init__(self, tx_id: int = 0x1234, is_response: bool = False,
                 opcode: int = 0, authoritative: bool = False,
                 truncated: bool = False, recursion_desired: bool = True,
                 recursion_available: bool = False, rcode: int = 0):
        super().__init__()
        self.tx_id = tx_id
        self.is_response = is_response
        self.opcode = opcode
        self.authoritative = authoritative
        self.truncated = truncated
        self.recursion_desired = recursion_desired
        self.recursion_available = recursion_available
        self.rcode = rcode

        self.questions: List[DNSQuestion] = []
        self.answers: List[DNSResourceRecord] = []
        self.authorities: List[DNSResourceRecord] = []
        self.additionals: List[DNSResourceRecord] = []
        self._update_fields()

    def _update_fields(self):
        flags_str = []
        flags_str.append("Response" if self.is_response else "Query")
        if self.authoritative: flags_str.append("AA (Authoritative)")
        if self.truncated: flags_str.append("TC (Truncated)")
        if self.recursion_desired: flags_str.append("RD (Recursion Desired)")
        if self.recursion_available: flags_str.append("RA (Recursion Available)")

        self.fields = {
            "Transaction ID": f"0x{self.tx_id:04x}",
            "Flags": ", ".join(flags_str),
            "Questions Count": len(self.questions),
            "Answer RRs Count": len(self.answers),
            "Authority RRs Count": len(self.authorities),
            "Additional RRs Count": len(self.additionals),
            "Questions": [q.to_dict() for q in self.questions],
            "Answers": [a.to_dict() for a in self.answers],
        }

    @classmethod
    def parse(cls, buffer: PacketBuffer) -> "DNSLayer":
        if buffer.remaining < 12:
            raise ValueError(f"DNS message truncated: minimum 12 bytes required, got {buffer.remaining}")

        full_data = buffer.data
        start_offset = buffer.offset

        tx_id, flags, qdcount, ancount, nscount, arcount = struct.unpack("!HHHHHH", buffer.read_bytes(12))

        is_response = bool((flags >> 15) & 0x01)
        opcode = (flags >> 11) & 0x0F
        authoritative = bool((flags >> 10) & 0x01)
        truncated = bool((flags >> 9) & 0x01)
        recursion_desired = bool((flags >> 8) & 0x01)
        recursion_available = bool((flags >> 7) & 0x01)
        rcode = flags & 0x0F

        layer = cls(
            tx_id=tx_id,
            is_response=is_response,
            opcode=opcode,
            authoritative=authoritative,
            truncated=truncated,
            recursion_desired=recursion_desired,
            recursion_available=recursion_available,
            rcode=rcode
        )

        # Parse Questions
        for _ in range(qdcount):
            if buffer.remaining < 4:
                break
            qname = decode_dns_name(buffer, full_data)
            qtype = buffer.read_uint16()
            qclass = buffer.read_uint16()
            layer.questions.append(DNSQuestion(qname, qtype, qclass))

        # Parse Answers
        for _ in range(ancount):
            if buffer.remaining < 10:
                break
            rname = decode_dns_name(buffer, full_data)
            rtype = buffer.read_uint16()
            rclass = buffer.read_uint16()
            ttl = buffer.read_uint32()
            rdlength = buffer.read_uint16()

            if buffer.remaining < rdlength:
                break

            rdata_bytes = buffer.read_bytes(rdlength)
            rdata_str = ""

            if rtype == DNS_TYPE_A and rdlength == 4:
                rdata_str = ip_bytes_to_str(rdata_bytes)
            elif rtype == DNS_TYPE_CNAME or rtype == DNS_TYPE_PTR or rtype == DNS_TYPE_NS:
                sub_buf = PacketBuffer(full_data)
                sub_buf.seek(buffer.offset - rdlength)
                rdata_str = decode_dns_name(sub_buf, full_data)
            else:
                rdata_str = rdata_bytes.hex()

            layer.answers.append(DNSResourceRecord(rname, rtype, rclass, ttl, rdata_bytes, rdata_str))

        layer.raw_header = buffer.data[start_offset:buffer.offset]
        layer.payload = buffer.peek_bytes(buffer.remaining)
        layer._update_fields()
        return layer

    def serialize(self) -> bytes:
        flags = (int(self.is_response) << 15) | ((self.opcode & 0x0F) << 11) | \
                (int(self.authoritative) << 10) | (int(self.truncated) << 9) | \
                (int(self.recursion_desired) << 8) | (int(self.recursion_available) << 7) | \
                (self.rcode & 0x0F)

        header = struct.pack(
            "!HHHHHH",
            self.tx_id,
            flags,
            len(self.questions),
            len(self.answers),
            len(self.authorities),
            len(self.additionals)
        )

        body = bytearray(header)

        # Questions
        for q in self.questions:
            body.extend(encode_dns_name(q.qname))
            body.extend(struct.pack("!HH", q.qtype, q.qclass))

        # Answers
        for a in self.answers:
            body.extend(encode_dns_name(a.name))
            if a.rtype == DNS_TYPE_A:
                rdata = ip_str_to_bytes(a.rdata_str)
                body.extend(struct.pack("!HHIH4s", a.rtype, a.rclass, a.ttl, len(rdata), rdata))
            else:
                body.extend(struct.pack("!HHIH", a.rtype, a.rclass, a.ttl, len(a.rdata)))
                body.extend(a.rdata)

        self.raw_header = bytes(body)
        self._update_fields()
        return self.raw_header
