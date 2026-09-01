= Roadmap & Future Horizons

#table(
  columns: (auto, 1fr),
  [*Version*], [*Description*],
  [v1.0.0], [Edge Seismic Detection (STA/LTA on ESP32)],
  [v1.1.0], [Cloud & Security (MQTT, HTTPS, TLS, ECDSA)],
  [v1.2.x], [On-Premise AI, Geo-Zoning, Serial Fallback],
  [v1.3.0], [Synchronized GNSS (NTP + PPS Time Discipline)],
  [v2.0.0], [Epicenter Triangulation & Hardware Assembly]
)

== Next Steps
- *v2.1.0 - Data Dashboards:* Grafana integration for real-time visualization of seismic telemetry and multi-node network activity.
- *v2.2.0 - Edge AI (Two-Tier Cluster):* A hierarchical Decision Fusion network where ubiquitous ESP32-C3 sensors (Tier A) act as triggers, and intelligent ESP32-S3 nodes (Tier B) run quantized INT8 CNNs via ESP-DL to confirm or discard triggers.

== Future Horizon: Post-Research Cloud Infrastructure
Following the validation phase, the system targets an operational release focusing on real-time auto-scaling. The MQTT/REST/AI stack will be fully provisioned as Infrastructure-as-Code (Terraform) and orchestrated via Kubernetes. Real-time elastic burst handling will scale worker pods in response to alert spikes, while long-range analytics will be migrated to ClickHouse and Kafka for massive multi-node correlation.
