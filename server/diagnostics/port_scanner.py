"""
NetPulse Diagnostics - Port Scanner & Service Discovery Engine
Simulates TCP SYN / Connect port scanning against target hosts to identify open services.
"""

from typing import Dict, Any, List, Optional
import random

WELL_KNOWN_PORTS = {
    21:   {"service": "FTP", "protocol": "TCP", "desc": "File Transfer Protocol"},
    22:   {"service": "SSH", "protocol": "TCP", "desc": "Secure Shell Remote Access"},
    23:   {"service": "Telnet", "protocol": "TCP", "desc": "Unencrypted Text Communications"},
    25:   {"service": "SMTP", "protocol": "TCP", "desc": "Simple Mail Transfer Protocol"},
    53:   {"service": "DNS", "protocol": "UDP/TCP", "desc": "Domain Name System"},
    80:   {"service": "HTTP", "protocol": "TCP", "desc": "World Wide Web Hypertext"},
    110:  {"service": "POP3", "protocol": "TCP", "desc": "Post Office Protocol"},
    143:  {"service": "IMAP", "protocol": "TCP", "desc": "Internet Message Access Protocol"},
    443:  {"service": "HTTPS", "protocol": "TCP", "desc": "HTTP over TLS/SSL"},
    445:  {"service": "SMB", "protocol": "TCP", "desc": "Server Message Block"},
    3306: {"service": "MySQL", "protocol": "TCP", "desc": "MySQL Database Server"},
    5432: {"service": "PostgreSQL", "protocol": "TCP", "desc": "PostgreSQL Relational DB"},
    6379: {"service": "Redis", "protocol": "TCP", "desc": "In-Memory Key-Value Store"},
    8080: {"service": "HTTP-Proxy", "protocol": "TCP", "desc": "Alternative HTTP / Web Proxy"},
    8443: {"service": "HTTPS-Alt", "protocol": "TCP", "desc": "Alternative HTTPS Web Port"},
}

# Node Type Default Open Ports
NODE_DEFAULT_SERVICES = {
    "server": [80, 443, 22, 5432, 8080],
    "router": [22, 53, 80],
    "gateway": [22, 53, 443],
    "host": [22],
    "switch": [22],
}


class PortScanResult:
    def __init__(self, port: int, state: str, service: str, description: str, latency_ms: float):
        self.port = port
        self.state = state  # 'OPEN', 'CLOSED', 'FILTERED'
        self.service = service
        self.description = description
        self.latency_ms = latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "port": self.port,
            "state": self.state,
            "service": self.service,
            "description": self.description,
            "latency_ms": round(self.latency_ms, 2),
        }


class PortScanner:
    """
    Simulates TCP Connect & SYN Port Scanning for Network Discovery.
    """

    @classmethod
    def scan_target(cls, target_ip: str, target_type: str = "server",
                    ports: Optional[List[int]] = None) -> Dict[str, Any]:
        if ports is None:
            ports = [21, 22, 23, 25, 53, 80, 110, 443, 445, 3306, 5432, 6379, 8080, 8443]

        open_target_ports = set(NODE_DEFAULT_SERVICES.get(target_type.lower(), [80, 443]))
        results: List[PortScanResult] = []

        open_count = 0
        closed_count = 0

        for p in ports:
            port_info = WELL_KNOWN_PORTS.get(p, {"service": f"port-{p}", "desc": "Custom Application Service"})
            latency = random.uniform(0.5, 4.0)

            if p in open_target_ports:
                state = "OPEN"
                open_count += 1
            else:
                state = "CLOSED"
                closed_count += 1

            results.append(PortScanResult(
                port=p,
                state=state,
                service=port_info["service"],
                description=port_info["desc"],
                latency_ms=latency
            ))

        return {
            "target_ip": target_ip,
            "target_type": target_type,
            "ports_scanned": len(ports),
            "open_ports": open_count,
            "closed_ports": closed_count,
            "scan_results": [r.to_dict() for r in results],
        }
