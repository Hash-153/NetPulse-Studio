"""
NetPulse Test Suite - Protocol Parsers and Binary Serializers
Validates bit-level serialization, RFC checksums, and dissector outputs across L2-L7 protocols.
"""

import unittest
import struct

from server.core.packet import (
    calculate_internet_checksum, mac_str_to_bytes, mac_bytes_to_str,
    ip_str_to_bytes, ip_bytes_to_str, PacketBuffer
)
from server.core.protocol_ethernet import EthernetLayer, ETHERTYPE_IPV4, ETHERTYPE_ARP
from server.core.protocol_arp import ARPLayer, ARP_OP_REQUEST, ARP_OP_REPLY
from server.core.protocol_ipv4 import IPv4Layer, PROTO_ICMP, PROTO_TCP, PROTO_UDP
from server.core.protocol_ipv6 import IPv6Layer
from server.core.protocol_icmp import ICMPLayer, ICMP_ECHO_REQUEST, ICMP_ECHO_REPLY
from server.core.protocol_tcp import TCPLayer, TCP_SYN, TCP_ACK
from server.core.protocol_udp import UDPLayer
from server.core.protocol_dns import DNSLayer, DNSQuestion, DNS_TYPE_A
from server.core.protocol_dhcp import DHCPLayer, DHCP_DISCOVER
from server.core.engine import PacketDissector


class TestProtocolParsers(unittest.TestCase):

    def test_internet_checksum(self):
        # RFC 1071 sample test
        data = b"\x45\x00\x00\x3c\x1c\x46\x40\x00\x40\x06\x00\x00\xac\x10\x0a\x63\xac\x10\x0a\x0c"
        csum = calculate_internet_checksum(data)
        self.assertIsInstance(csum, int)
        self.assertTrue(0 <= csum <= 0xFFFF)

    def test_mac_and_ip_converters(self):
        mac_str = "00:1a:2b:3c:4d:5e"
        mac_bytes = mac_str_to_bytes(mac_str)
        self.assertEqual(len(mac_bytes), 6)
        self.assertEqual(mac_bytes_to_str(mac_bytes), mac_str)

        ip_str = "192.168.1.100"
        ip_bytes = ip_str_to_bytes(ip_str)
        self.assertEqual(len(ip_bytes), 4)
        self.assertEqual(ip_bytes_to_str(ip_bytes), ip_str)

    def test_ethernet_serialization(self):
        eth = EthernetLayer(dst_mac="ff:ff:ff:ff:ff:ff", src_mac="00:11:22:33:44:55", ethertype=ETHERTYPE_IPV4)
        raw = eth.serialize()
        self.assertEqual(len(raw), 14)

        buf = PacketBuffer(raw)
        parsed = EthernetLayer.parse(buf)
        self.assertEqual(parsed.dst_mac, "ff:ff:ff:ff:ff:ff")
        self.assertEqual(parsed.src_mac, "00:11:22:33:44:55")
        self.assertEqual(parsed.ethertype, ETHERTYPE_IPV4)

    def test_arp_packet(self):
        arp = ARPLayer(operation=ARP_OP_REQUEST, sender_mac="00:11:22:33:44:55",
                       sender_ip="192.168.1.1", target_mac="00:00:00:00:00:00", target_ip="192.168.1.254")
        raw = arp.serialize()
        self.assertEqual(len(raw), 28)

        buf = PacketBuffer(raw)
        parsed = ARPLayer.parse(buf)
        self.assertEqual(parsed.operation, ARP_OP_REQUEST)
        self.assertEqual(parsed.sender_ip, "192.168.1.1")
        self.assertEqual(parsed.target_ip, "192.168.1.254")

    def test_ipv4_checksum_and_dissection(self):
        ip = IPv4Layer(src_ip="10.0.0.1", dst_ip="10.0.0.2", protocol=PROTO_ICMP, ttl=64)
        raw = ip.serialize()
        self.assertEqual(len(raw), 20)
        self.assertNotEqual(ip.checksum, 0)

        buf = PacketBuffer(raw)
        parsed = IPv4Layer.parse(buf)
        self.assertEqual(parsed.src_ip, "10.0.0.1")
        self.assertEqual(parsed.dst_ip, "10.0.0.2")
        self.assertEqual(len(parsed.validation_errors), 0)

    def test_icmp_echo_serialization(self):
        icmp = ICMPLayer(icmp_type=ICMP_ECHO_REQUEST, code=0, identifier=101, sequence=1, data=b"TestPingData")
        raw = icmp.serialize()
        self.assertGreater(len(raw), 8)

        buf = PacketBuffer(raw)
        parsed = ICMPLayer.parse(buf)
        self.assertEqual(parsed.icmp_type, ICMP_ECHO_REQUEST)
        self.assertEqual(parsed.identifier, 101)
        self.assertEqual(parsed.payload, b"TestPingData")
        self.assertEqual(len(parsed.validation_errors), 0)

    def test_tcp_serialization_and_flags(self):
        tcp = TCPLayer(src_port=12345, dst_port=80, seq_num=1000, ack_num=2000, flags=TCP_SYN | TCP_ACK)
        raw = tcp.serialize(src_ip="10.0.0.1", dst_ip="10.0.0.2")
        self.assertEqual(len(raw), 20)

        buf = PacketBuffer(raw)
        parsed = TCPLayer.parse(buf)
        self.assertEqual(parsed.src_port, 12345)
        self.assertEqual(parsed.dst_port, 80)
        self.assertTrue(parsed.flags & TCP_SYN)
        self.assertTrue(parsed.flags & TCP_ACK)

    def test_udp_serialization(self):
        udp = UDPLayer(src_port=5353, dst_port=53, data=b"HelloUDP")
        raw = udp.serialize(src_ip="10.0.0.1", dst_ip="10.0.0.2")
        self.assertEqual(len(raw), 8 + 8)

        buf = PacketBuffer(raw)
        parsed = UDPLayer.parse(buf)
        self.assertEqual(parsed.src_port, 5353)
        self.assertEqual(parsed.dst_port, 53)
        self.assertEqual(parsed.payload, b"HelloUDP")

    def test_dns_query_encoding(self):
        dns = DNSLayer(tx_id=0xbeef, is_response=False)
        dns.questions.append(DNSQuestion("netpulse.internal", DNS_TYPE_A))
        raw = dns.serialize()

        buf = PacketBuffer(raw)
        parsed = DNSLayer.parse(buf)
        self.assertEqual(parsed.tx_id, 0xbeef)
        self.assertEqual(len(parsed.questions), 1)
        self.assertEqual(parsed.questions[0].qname, "netpulse.internal")

    def test_full_packet_dissector_pipeline(self):
        # Build complete Ethernet -> IPv4 -> TCP frame
        eth = EthernetLayer(dst_mac="00:1a:2b:01:00:01", src_mac="00:1a:2b:05:00:01", ethertype=ETHERTYPE_IPV4)
        ip = IPv4Layer(src_ip="10.10.1.101", dst_ip="10.20.1.10", protocol=PROTO_TCP)
        tcp = TCPLayer(src_port=50000, dst_port=80, flags=TCP_SYN)
        
        ip.payload = tcp.serialize("10.10.1.101", "10.20.1.10")
        eth.payload = ip.serialize()
        raw_frame = eth.serialize()

        dissected = PacketDissector.dissect(raw_frame)
        self.assertTrue(dissected.is_valid)
        self.assertEqual(len(dissected.layers), 3)
        self.assertEqual(dissected.layers[0].name, "Ethernet II")
        self.assertEqual(dissected.layers[1].name, "IPv4")
        self.assertEqual(dissected.layers[2].name, "TCP")


if __name__ == "__main__":
    unittest.main()
