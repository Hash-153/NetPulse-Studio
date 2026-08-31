"""
NetPulse - Main Entrypoint & Server Launcher
Orchestrates background synthetic traffic generator, telemetry collector, and HTTP server.
"""

import sys
import os
import threading
import time
import argparse

# Ensure parent path in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.api.http_server import create_server
from server.api.routes import ctx
from server.simulator.traffic_gen import TrafficGenerator


def background_traffic_worker():
    """Generates synthetic background flows and ticks telemetry every second."""
    while True:
        try:
            if ctx.is_traffic_running:
                # Generate 1-2 random packets per tick
                pkt = TrafficGenerator.create_random_sample_packet()
                fw_res = ctx.firewall.evaluate_packet(pkt)
                pkt_dict = pkt.to_dict()
                pkt_dict["firewall_eval"] = fw_res
                
                ctx.packet_history.append(pkt_dict)
                ctx.bandwidth_meter.record_packet(len(pkt.raw_bytes))
                ctx.anomaly_detector.inspect_packet(pkt)

            # Telemetry sliding window update
            ctx.bandwidth_meter.tick()
        except Exception as e:
            print(f"[Worker Error] {e}")
        time.sleep(1.0)


def main():
    parser = argparse.ArgumentParser(description="NetPulse Enterprise Network Observability Platform")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    args = parser.parse_args()

    print("=" * 70)
    print("   [+] NetPulse - Enterprise Network Observability & Simulation Suite")
    print("=" * 70)
    print(f"[*] Starting background telemetry and simulation engine...")
    
    # Launch background worker
    worker_thread = threading.Thread(target=background_traffic_worker, daemon=True)
    worker_thread.start()

    print(f"[*] Initialized topology: {len(ctx.topology.nodes)} Nodes, {len(ctx.topology.links)} Links")
    print(f"[*] Initialized firewall: {len(ctx.firewall.rules)} Active ACL Rules")
    print(f"[*] HTTP Server listening at http://{args.host}:{args.port}")
    print(f"[*] Open your browser to explore the NetPulse Dashboard!")
    print("=" * 70)

    server = create_server(host=args.host, port=args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down NetPulse server...")
        server.server_close()


if __name__ == "__main__":
    main()
