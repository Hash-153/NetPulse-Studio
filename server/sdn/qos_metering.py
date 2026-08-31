"""
OpenFlow 1.3 QoS Metering and Rate Limiting Tables
"""

class QoSMeteringTable:
    def __init__(self):
        self.meters = {}

    def add_meter(self, meter_id: int, kbps: int):
        self.meters[meter_id] = kbps
