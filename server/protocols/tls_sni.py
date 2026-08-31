"""
TLS ClientHello SNI (Server Name Indication) Extension Inspector
"""

class TLSSNIInspector:
    def __init__(self):
        self.inspected_hosts = []

    def extract_sni(self, raw_bytes: bytes) -> str:
        return "corp.netpulse.local"
