# ROADMAP — QuakeGuard

> Next steps and critical issues to resolve.

| # | Task | Description | Severity | Completion |
|---|------|-------------|----------|------------|
| 1 | Fix errors from PROBLEMI.md | Resolve all 111 cataloged issues (37 HIGH, 43 MEDIUM, 31 LOW) across backend, frontend, firmware, and CI/CD. Start with the TOP 5 absolute priorities. | 🔴 High | 0% |
| 2 | IoT sensor plane calibration | **Verification done:** no calibration code found in firmware. Implement ADXL345 offset calibration on boot (read resting values and subtract) to prevent false positives on flat surfaces. | 🟠 Medium | 0% |
| 3 | Firmware update mechanism | Calculate current firmware size and verify it's <50% of flash (ESP32-C3: 4MB → <2MB). Configure OTA dual-slot partition (active + fallback) in `platformio.ini` via `board_build.partitions`. | 🟠 Medium | 0% |
| 4 | Earthquake triangulation | Rework backend so alerts depend on multiple sensor triangulation rather than a single sensor. Implement spatial and temporal correlation logic. Notify mobile devices via WebSocket/Push. | 🔴 High | 0% |
| 5 | Remove bottlenecks | Eliminate MQTT queue as mandatory entry point. Parallelize Redis queue (already used for pub/sub) and API Gateway (direct HTTP ingress). Sync current workers and remove blocking sleeps (P1.3.1-2). | 🔴 High | 0% |
| 6 | Scalability infrastructure | Define architecture: Server → Load Balancer (e.g. Nginx/HAProxy) → Backend replicas → Redis Cluster → PostgreSQL with replica. Frontend via CDN. Auto-scaling via Kubernetes or Docker Swarm. | 🟠 Medium | 0% |
| 7 | Unique device identification | Find a reliable method to uniquely identify sensors and phones (e.g., serial number, network interface serial, secure element ID) for provisioning and anti-spoofing. | 🟠 Medium | 0% |
| 8 | Distribution strategy | Evaluate strategies: (a) Direct B2G sales to local authorities; (b) Partnership with external company for industrialization; (c) Grants and tenders (PNRR, EU funds, Civil Protection). Define Go-to-Market plan. | 🟠 Medium | 0% |
