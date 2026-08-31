"""
NetPulse Core - Packet Dissector & Protocol Inspection Engine
Analyzes raw byte streams and constructs multi-layer protocol trees (L2 to L7).
"""

import time
from typing import Optional, List, Dict, Any

from server.core.packet import PacketBuffer, DissectedPacket
from server.core.protocol_ethernet import (
    EthernetLayer, ETHERTYPE_IPV4, ETHERTYPE_IPV6, ETHERTYPE_ARP
)
from server.core.protocol_arp import ARPLayer
from server.core.protocol_ipv4 import IPv4Layer, PROTO_ICMP, PROTO_TCP, PROTO_UDP
from server.core.protocol_ipv6 import IPv6Layer
from server.core.protocol_icmp import ICMPLayer
from server.core.protocol_tcp import TCPLayer
from server.core.protocol_udp import UDPLayer
from server.core.protocol_dns import DNSLayer
from server.core.protocol_dhcp import DHCPLayer


class PacketDissector:
    """
    State-of-the-art native network packet dissector.
    Recursively descends through protocol encapsulations.
    """

    @classmethod
    def dissect(cls, raw_data: bytes, timestamp: Optional[float] = None) -> DissectedPacket:
        if timestamp is None:
            timestamp = time.time()

        packet = DissectedPacket(raw_bytes=raw_data, timestamp=timestamp)
        buffer = PacketBuffer(raw_data)

        if len(raw_data) < 14:
            packet.is_valid = False
            packet.error_message = "Packet too small (< 14 bytes) for Ethernet frame"
            packet.summary = f"Malformed Frame ({len(raw_data)} bytes)"
            return packet

        try:
            # Layer 2: Ethernet
            eth = EthernetLayer.parse(buffer)
            packet.add_layer(eth)

            # Layer 3: Network Layer Dispatch
            if eth.ethertype == ETHERTYPE_ARP:
                arp = ARPLayer.parse(buffer)
                packet.add_layer(arp)
                packet.summary = f"ARP: Who has {arp.target_ip}? Tell {arp.sender_ip}" if arp.operation == 1 else f"ARP: {arp.sender_ip} is at {arp.sender_mac}"
                return packet

            elif eth.ethertype == ETHERTYPE_IPV4:
                ip = IPv4Layer.parse(buffer)
                packet.add_layer(ip)
                cls._dissect_ipv4_payload(ip, buffer, packet)

            elif eth.ethertype == ETHERTYPE_IPV6:
                ip6 = IPv6Layer.parse(buffer)
                packet.add_layer(ip6)
                cls._dissect_ipv6_payload(ip6, buffer, packet)

            else:
                packet.summary = f"Ethernet II: EtherType 0x{eth.ethertype:04x} ({len(raw_data)} bytes)"

        except Exception as e:
            packet.is_valid = False
            packet.error_message = f"Dissection exception: {str(e)}"
            if not packet.summary:
                packet.summary = f"Malformed Packet ({str(e)})"

        return packet

    @classmethod
    def _dissect_ipv4_payload(cls, ip: IPv4Layer, buffer: PacketBuffer, packet: DissectedPacket):
        payload_buf = PacketBuffer(ip.payload)

        if ip.protocol == PROTO_ICMP:
            icmp = ICMPLayer.parse(payload_buf)
            packet.add_layer(icmp)
            packet.summary = f"ICMP: {icmp.fields.get('Type', 'Echo')} ({ip.src_ip} -> {ip.dst_ip})"

        elif ip.protocol == PROTO_TCP:
            tcp = TCPLayer.parse(payload_buf)
            packet.add_layer(tcp)
            flags_short = tcp.fields.get("Flags", "").split("(")[-1].replace(")", "")
            packet.summary = f"TCP: {ip.src_ip}:{tcp.src_port} -> {ip.dst_ip}:{tcp.dst_port} [{flags_short}] Seq={tcp.seq_num} Len={len(tcp.payload)}"
            cls._dissect_l7_application(tcp.src_port, tcp.dst_port, tcp.payload, packet)

        elif ip.protocol == PROTO_UDP:
            udp = UDPLayer.parse(payload_buf)
            packet.add_layer(udp)
            packet.summary = f"UDP: {ip.src_ip}:{udp.src_port} -> {ip.dst_ip}:{udp.dst_port} Len={udp.length}"
            cls._dissect_l7_application(udp.src_port, udp.dst_port, udp.payload, packet)

        else:
            packet.summary = f"IPv4: {ip.src_ip} -> {ip.dst_ip} (Proto {ip.protocol})"

    @classmethod
    def _dissect_ipv6_payload(cls, ip6: IPv6Layer, buffer: PacketBuffer, packet: DissectedPacket):
        payload_buf = PacketBuffer(ip6.payload)

        if ip6.next_header == PROTO_TCP:
            tcp = TCPLayer.parse(payload_buf)
            packet.add_layer(tcp)
            packet.summary = f"TCP/IPv6: {ip6.src_ip}:{tcp.src_port} -> {ip6.dst_ip}:{tcp.dst_port}"
            cls._dissect_l7_application(tcp.src_port, tcp.dst_port, tcp.payload, packet)
        elif ip6.next_header == PROTO_UDP:
            udp = UDPLayer.parse(payload_buf)
            packet.add_layer(udp)
            packet.summary = f"UDP/IPv6: {ip6.src_ip}:{udp.src_port} -> {ip6.dst_ip}:{udp.dst_port}"
            cls._dissect_l7_application(udp.src_port, udp.dst_port, udp.payload, packet)
        else:
            packet.summary = f"IPv6: {ip6.src_ip} -> {ip6.dst_ip} (NextHeader {ip6.next_header})"

    @classmethod
    def _dissect_l7_application(cls, src_port: int, dst_port: int, app_payload: bytes, packet: DissectedPacket):
        if not app_payload:
            return

        app_buf = PacketBuffer(app_payload)

        # DNS Inspection (Port 53)
        if src_port == 53 or dst_port == 53:
            try:
                dns = DNSLayer.parse(app_buf)
                packet.add_layer(dns)
                if dns.questions:
                    q = dns.questions[0]
                    packet.summary = f"DNS: {'Response' if dns.is_response else 'Query'} {q.qname} ({q.to_dict()['type']})"
            except Exception:
                pass

        # DHCP Inspection (Port 67 or 68)
        elif src_port in (67, 68) or dst_port in (67, 68):
            try:
                dhcp = DHCPLayer.parse(app_buf)
                packet.add_layer(dhcp)
                packet.summary = f"DHCP: {dhcp.fields.get('Message Type', 'BOOTP')} (XID 0x{dhcp.xid:08x})"
            except Exception:
                pass
