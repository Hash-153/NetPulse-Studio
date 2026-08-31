"""
IPFIX / NetFlow v9 Streaming UDP Telemetry Exporter
"""

class IPFIXStreamExporter:
    def __init__(self):
        self.active_templates = {}
