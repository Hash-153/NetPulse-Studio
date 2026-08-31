"""
NetPulse API - Native Standalone HTTP REST & Static File Web Server
Pure standard library implementation with zero external package dependencies.
"""

import http.server
import json
import os
import urllib.parse
from typing import Dict, Any, Optional

from server.api.routes import ApiRoutes


class NetPulseHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler dispatching REST API routes and serving static web assets."""

    def __init__(self, *args, directory=None, **kwargs):
        # Set static directory to client/
        if directory is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            directory = os.path.join(base_dir, "client")
        super().__init__(*args, directory=directory, **kwargs)

    def _send_json(self, data: Any, status_code: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # REST API Routes
        if path == "/api/status":
            self._send_json(ApiRoutes.get_status())
        elif path == "/api/topology":
            self._send_json(ApiRoutes.get_topology())
        elif path == "/api/route":
            src = query_params.get("src", ["gw-1"])[0]
            dst = query_params.get("dst", ["pc-eng1"])[0]
            self._send_json(ApiRoutes.compute_route(src, dst))
        elif path == "/api/packets":
            limit = int(query_params.get("limit", [50])[0])
            self._send_json(ApiRoutes.get_packets(limit))
        elif path == "/api/firewall":
            self._send_json(ApiRoutes.get_firewall_rules())
        elif path == "/api/telemetry":
            self._send_json(ApiRoutes.get_telemetry())
        elif path == "/api/diagnostics/ping":
            src = query_params.get("src", ["pc-eng1"])[0]
            dst = query_params.get("dst", ["srv-web"])[0]
            count = int(query_params.get("count", [4])[0])
            self._send_json(ApiRoutes.run_ping(src, dst, count))
        elif path == "/api/diagnostics/traceroute":
            src = query_params.get("src", ["pc-eng1"])[0]
            dst = query_params.get("dst", ["srv-web"])[0]
            self._send_json(ApiRoutes.run_traceroute(src, dst))
        elif path == "/api/diagnostics/portscan":
            ip = query_params.get("ip", ["10.20.1.10"])[0]
            ttype = query_params.get("type", ["server"])[0]
            self._send_json(ApiRoutes.run_portscan(ip, ttype))
        else:
            # Fallback to static asset serving
            super().do_GET()

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if path == "/api/packets/generate":
            proto = data.get("protocol", "random")
            self._send_json(ApiRoutes.generate_packet(proto))
        elif path == "/api/packets/dissect-hex":
            raw_hex = data.get("hex", "")
            self._send_json(ApiRoutes.dissect_hex(raw_hex))
        elif path == "/api/topology/node":
            self._send_json(ApiRoutes.add_node(data))
        elif path == "/api/topology/link":
            self._send_json(ApiRoutes.add_link(data))
        elif path == "/api/firewall/rule":
            self._send_json(ApiRoutes.add_firewall_rule(data))
        else:
            self._send_json({"error": "Endpoint not found"}, status_code=404)

    def do_DELETE(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if path == "/api/firewall/rule":
            rule_id = int(query_params.get("id", [0])[0])
            self._send_json(ApiRoutes.delete_firewall_rule(rule_id))
        else:
            self._send_json({"error": "Endpoint not found"}, status_code=404)


def create_server(host: str = "127.0.0.1", port: int = 8080) -> http.server.HTTPServer:
    server_address = (host, port)
    httpd = http.server.ThreadingHTTPServer(server_address, NetPulseHTTPRequestHandler)
    return httpd
