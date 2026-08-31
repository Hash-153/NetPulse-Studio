"""
BGP EVPN Ethernet Segment Multi-Homing (RFC 7432)
"""

class BGPEVPNMultiHoming:
    def __init__(self):
        self.esi_table = {}

    def register_esi(self, esi_id: str):
        self.esi_table[esi_id] = "ACTIVE"
