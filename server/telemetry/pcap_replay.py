"""
PCAP Network Stream Replay & Ingestion Accelerator
"""

class PCAPStreamReplay:
    def __init__(self, pcap_path: str):
        self.pcap_path = pcap_path
        self.replayed_count = 0
