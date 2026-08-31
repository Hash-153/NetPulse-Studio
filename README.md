# NetPulse: Enterprise Network Observability, Simulation & Protocol Diagnostics Suite

NetPulse is an enterprise-grade full-stack networking platform built from first principles. It delivers comprehensive protocol dissection (L2–L7), BGP/OSPF dynamic routing, OpenFlow 1.3 Software-Defined Networking (SDN), Web Application Firewall (WAF), Deep Packet Inspection (DPI), Constraint-based Shortest Path First (CSPF) traffic engineering, active network diagnostics (Ping, Traceroute, Port Scanning), and real-time telemetry streaming—with zero third-party open-source code reuse.

---

## Dependencies

- **Python**: Python 3.10+ (Standard Library runtime)
- **Containerization**: Docker 20.10+ & Docker Compose (Optional)
- **Node.js / NPM**: Node.js 18+ (For build scripts and frontend tooling)
- **Dependency Manifests**: `requirements.txt`, `pyproject.toml`, `poetry.lock`, `package.json`, `package-lock.json`

---

## Installation

### 1. Clone or Extract the Repository
```bash
git clone https://github.com/Hash-153/networking.git
cd networking
```

### 2. Set Up Python Virtual Environment
```bash
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
# Alternatively with Poetry:
poetry install
# For frontend asset management:
npm install
```

### 4. Configure Environment
```bash
# Configuration template is provided in example.env
```

---

## Build

### Build Application Bytecode & Manifests
```bash
# Using Makefile
make build

# Or using NPM scripts
npm run build

# Or manually
python -m py_compile server/main.py
```

### Build Docker Container
```bash
docker build -t netpulse-suite:latest .
```

---

## Run

### Option A: Local Development Server
```bash
# Direct python execution
python server/main.py --host 127.0.0.1 --port 8080

# Or using Makefile
make run

# Or using NPM
npm start
```

### Option B: Docker Compose (Production Deployment)
```bash
docker-compose up -d
```

### Option C: Run Automated Test Suite
```bash
python server/tests/run_all_tests.py
# Or with pytest
pytest server/tests/ -v
```

---

## Usage

1. **Web Dashboard**:
   - Open your browser to `http://127.0.0.1:8080`.
   - Access the interactive SVG network topology, live packet sniffer, diagnostics terminal, and firewall manager.

2. **REST API Endpoints**:
   - `GET /api/status`: System health, active nodes, packet counters, and bandwidth telemetry.
   - `GET /api/topology`: Node definitions, link latencies, and connectivity graph.
   - `GET /api/route?src=<node_a>&dst=<node_b>`: Compute shortest path with Dijkstra SPF.
   - `POST /api/packets/generate`: Inject multi-protocol synthetic flows (HTTP, DNS, ICMP, ARP).
   - `POST /api/packets/dissect-hex`: Dissect raw hexadecimal wire packets.
   - `GET /api/diagnostics/ping?src=<id>&dst=<id>`: Run 4-probe ICMP ping with jitter and loss stats.
   - `GET /api/diagnostics/traceroute?src=<id>&dst=<id>`: Run incremental TTL hop discovery.
   - `GET /api/diagnostics/portscan?ip=<ip>&type=<type>`: Run TCP SYN port scan.
   - `GET /api/firewall`: Retrieve stateful ACL security rules and match metrics.
   - `GET /api/telemetry`: Sliding window throughput (Kbps, PPS) and IDS intrusion alerts.

---

## Architectural Highlights

### 1. Protocol Parsing & Dissection Engine (`server/protocols/`, `server/core/`)
- **L2 / L3 / L4 / L7**: Ethernet II, 802.1Q VLAN, ARP, IPv4 (RFC 791), IPv6 (RFC 8200), ICMPv4 (RFC 792), TCP (RFC 793), UDP (RFC 768), DNS (RFC 1035), DHCP (RFC 2131).
- **Advanced Routing**: BGP-4 (RFC 4271), OSPFv2/v3 (RFC 2328/5340), IS-IS (ISO/IEC 10589), RIPv2 (RFC 2453), MPLS (RFC 3031/3032), LDP (RFC 5036).
- **Secure Transport**: TLS 1.3/1.2 (RFC 8446), IPSec AH/ESP (RFC 4301/4303), IKEv2 (RFC 7296), WireGuard, DNSSEC (RFC 4034).
- **Modern Web & IoT**: HTTP/2 (RFC 7540), QUIC / HTTP/3 (RFC 9000/9114), CoAP (RFC 7252), MQTT (v3.1.1/v5.0), SIP / SDP (RFC 3261/4566).
- **Management & Industrial**: SNMP v1/v2c/v3 (RFC 3416), NetFlow v5/v9 & IPFIX (RFC 7011), SCTP (RFC 4960), PTP IEEE 1588v2, STP / RSTP (IEEE 802.1D/w), LLDP (IEEE 802.1AB), RADIUS (RFC 2865), Diameter (RFC 6733).

### 2. Software-Defined Networking (SDN) & Traffic Engineering (`server/sdn/`, `server/traffic_engineering/`)
- OpenFlow 1.3 controller with match-action flow table pipeline.
- 5G / Virtual Network Slicing engine with tenant bandwidth guarantees.
- Constraint-based Shortest Path First (CSPF) and RSVP-TE signaling.
- Segment Routing (SR-MPLS / SRv6) policy enforcement.

### 3. Security Suite & Telemetry (`server/security_suite/`, `server/telemetry/`)
- Web Application Firewall (WAF) OWASP rule engine.
- Deep Packet Inspection (DPI) with Aho-Corasick multi-pattern search.
- DDoS mitigation with SYN Proxy defense.
- gNMI streaming telemetry, NETCONF / YANG data modeling, and PCAP reader/writer.
