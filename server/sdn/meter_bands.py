"""
OpenFlow 1.3 Meter Table & Band Policing (Drop, DSCP Remark)
"""

class OpenFlowMeterBand:
    def __init__(self, meter_id: int, rate_kbps: int):
        self.meter_id = meter_id
        self.rate_kbps = rate_kbps
        self.burst_size = 1000
