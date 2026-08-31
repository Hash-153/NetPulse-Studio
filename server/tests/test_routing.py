"""
NetPulse Test Suite - Routing and Firewall Rule Evaluation
Validates Dijkstra SPF path computing and ACL filtering matches.
"""

import unittest
from server.simulator.topology import NetworkTopology, NetworkNode, NetworkLink
from server.simulator.routing import RoutingEngine
from server.simulator.firewall import FirewallEngine, ACLRule, ip_in_network, port_in_range
from server.simulator.traffic_gen import TrafficGenerator


class TestRoutingAndFirewall(unittest.TestCase):

    def setUp(self):
        self.topology = NetworkTopology.create_enterprise_sample()
        self.firewall = FirewallEngine(default_policy="DENY")

    def test_dijkstra_path_finding(self):
        # PC Eng1 to Web App Server
        result = RoutingEngine.compute_shortest_path(self.topology, "pc-eng1", "srv-web")
        self.assertTrue(result.reachable)
        self.assertGreater(result.total_hops, 2)
        
        # Verify node progression: pc-eng1 -> sw-corp -> r-core -> sw-dmz -> srv-web
        node_ids = [h.node.node_id for h in result.hops]
        self.assertEqual(node_ids[0], "pc-eng1")
        self.assertEqual(node_ids[-1], "srv-web")

    def test_isolated_node_unreachable(self):
        isolated = NetworkNode("iso-1", "Isolated Box", "host", "192.168.99.1", "00:99:99:99:99:99")
        self.topology.add_node(isolated)
        
        result = RoutingEngine.compute_shortest_path(self.topology, "pc-eng1", "iso-1")
        self.assertFalse(result.reachable)

    def test_ip_cidr_matching(self):
        self.assertTrue(ip_in_network("10.10.1.50", "10.10.1.0/24"))
        self.assertTrue(ip_in_network("10.10.1.50", "10.0.0.0/8"))
        self.assertTrue(ip_in_network("10.10.1.50", "any"))
        self.assertFalse(ip_in_network("10.20.1.50", "10.10.1.0/24"))

    def test_port_range_matching(self):
        self.assertTrue(port_in_range(80, "80"))
        self.assertTrue(port_in_range(8080, "8000-9000"))
        self.assertTrue(port_in_range(443, "any"))
        self.assertFalse(port_in_range(443, "80"))

    def test_firewall_rule_evaluation(self):
        # HTTP packet to web server should ALLOW (Rule #10)
        http_pkt = TrafficGenerator.create_http_request(dst_ip="10.20.1.10")
        res = self.firewall.evaluate_packet(http_pkt)
        self.assertEqual(res["action"], "ALLOW")

        # Custom block rule
        self.firewall.add_rule(ACLRule(5, "DENY", "TCP", "any", "10.20.1.10", "any", "80", "Emergency Web Block"))
        res_blocked = self.firewall.evaluate_packet(http_pkt)
        self.assertEqual(res_blocked["action"], "DENY")
        self.assertEqual(res_blocked["rule_id"], 5)


if __name__ == "__main__":
    unittest.main()
