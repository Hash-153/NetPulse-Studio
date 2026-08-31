"""
NetPulse Simulator - Synthetic Network Traffic Generator
Generates realistic multi-protocol traffic streams (HTTP, DNS, Ping, DB Queries, VoIP).
"""

import random
import time
from typing import List, Optional

from server.core.packet import DissectedPacket
from server.core.protocol_ethernet import EthernetLayer, ETHERTYPE_IPV4, ETHERTYPE_ARP
from server.core.protocol_arp import ARPLayer, ARP_OP_REQUEST, ARP_OP_REPLY
from server.core.protocol_ipv4 import IPv4Layer, PROTO_ICMP, PROTO_TCP, PROTO_UDP
from server.core.protocol_icmp import ICMPLayer, ICMP_ECHO_REQUEST, ICMP_ECHO_REPLY
from server.core.protocol_tcp import TCPLayer, TCP_SYN, TCP_ACK, TCP_PSH
from server.core.protocol_udp import UDPLayer
from server.core.protocol_dns import DNSLayer, DNSQuestion, DNSResourceRecord, DNS_TYPE_A
from server.core.engine import PacketDissector


class TrafficGenerator:
    """
    Constructs realistic binary wire packets for network simulation and inspection.
    """

    @classmethod
    def create_icmp_ping(cls, src_ip: str = "10.10.1.101", dst_ip: str = "10.20.1.10",
                         src_mac: str = "00:1A:2B:05:00:01", dst_mac: str = "00:1A:2B:03:00:01",
                         seq: int = 1, ttl: int = 64) -> DissectedPacket:
        eth = EthernetLayer(dst_mac=dst_mac, src_mac=src_mac, ethertype=ETHERTYPE_IPV4)
        ip = IPv4Layer(src_ip=src_ip, dst_ip=dst_ip, protocol=PROTO_ICMP, ttl=ttl)
        icmp = ICMPLayer(icmp_type=ICMP_ECHO_REQUEST, code=0, identifier=0x4242, sequence=seq, data=b"NetPulsePingPayload1234567890")

        ip.payload = icmp.serialize()
        eth.payload = ip.serialize()
        raw_bytes = eth.serialize()

        return PacketDissector.dissect(raw_bytes)

    @classmethod
    def create_dns_query(cls, domain: str = "api.internal.corp",
                         src_ip: str = "10.10.1.101", dst_ip: str = "10.0.0.53",
                         src_mac: str = "00:1A:2B:05:00:01", dst_mac: str = "00:1A:2B:04:00:53") -> DissectedPacket:
        eth = EthernetLayer(dst_mac=dst_mac, src_mac=src_mac, ethertype=ETHERTYPE_IPV4)
        ip = IPv4Layer(src_ip=src_ip, dst_ip=dst_ip, protocol=PROTO_UDP, ttl=64)
        
        dns = DNSLayer(tx_id=random.randint(1000, 60000), is_response=False, recursion_desired=True)
        dns.questions.append(DNSQuestion(qname=domain, qtype=DNS_TYPE_A))
        
        udp = UDPLayer(src_port=random.randint(49152, 65535), dst_port=53)
        udp.payload = dns.serialize()
        
        ip.payload = udp.serialize(src_ip=src_ip, dst_ip=dst_ip)
        eth.payload = ip.serialize()
        raw_bytes = eth.serialize()

        return PacketDissector.dissect(raw_bytes)

    @classmethod
    def create_http_request(cls, path: str = "/api/v1/health",
                           src_ip: str = "10.10.1.101", dst_ip: str = "10.20.1.10",
                           src_mac: str = "00:1A:2B:05:00:01", dst_mac: str = "00:1A:2B:04:00:10") -> DissectedPacket:
        eth = EthernetLayer(dst_mac=dst_mac, src_mac=src_mac, ethertype=ETHERTYPE_IPV4)
        ip = IPv4Layer(src_ip=src_ip, dst_ip=dst_ip, protocol=PROTO_TCP, ttl=64)
        
        http_payload = f"GET {path} HTTP/1.1\r\nHost: {dst_ip}\r\nUser-Agent: NetPulse/2.0\r\nAccept: */*\r\n\r\n".encode("utf-8")
        tcp = TCPLayer(src_port=random.randint(40000, 60000), dst_port=80,
                       seq_num=random.randint(100000, 999999), ack_num=1,
                       flags=TCP_ACK | TCP_PSH)
        tcp.payload = http_payload
        
        ip.payload = tcp.serialize(src_ip=src_ip, dst_ip=dst_ip)
        eth.payload = ip.serialize()
        raw_bytes = eth.serialize()

        return PacketDissector.dissect(raw_bytes)

    @classmethod
    def create_arp_probe(cls, target_ip: str = "10.10.1.1",
                         sender_ip: str = "10.10.1.101",
                         sender_mac: str = "00:1A:2B:05:00:01") -> DissectedPacket:
        eth = EthernetLayer(dst_mac="ff:ff:ff:ff:ff:ff", src_mac=sender_mac, ethertype=ETHERTYPE_ARP)
        arp = ARPLayer(
            operation=ARP_OP_REQUEST,
            sender_mac=sender_mac,
            sender_ip=sender_ip,
            target_mac="00:00:00:00:00:00",
            target_ip=target_ip
        )
        eth.payload = arp.serialize()
        raw_bytes = eth.serialize()

        return PacketDissector.dissect(raw_bytes)

    @classmethod
    def create_random_sample_packet(cls) -> DissectedPacket:
        """Picks a random realistic protocol flow."""
        generators = [
            lambda: cls.create_icmp_ping(seq=random.randint(1, 100)),
            lambda: cls.create_dns_query(domain=random.choice(["corp.internal", "db.cluster", "auth.netpulse.local"])),
            lambda: cls.create_http_request(path=random.choice(["/", "/login", "/metrics", "/status"])),
            lambda: cls.create_arp_probe(target_ip=f"10.10.1.{random.randint(1, 20)}"),
        ]
        return random.choice(generators)()
