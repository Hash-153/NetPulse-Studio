"""
BGP Flowspec (RFC 5575) Dissemination of Flow Specification Rules
"""

class BGPFlowspecEngine:
    def __init__(self):
        self.flowspec_rules = []

    def add_rule(self, rule_dict):
        self.flowspec_rules.append(rule_dict)
