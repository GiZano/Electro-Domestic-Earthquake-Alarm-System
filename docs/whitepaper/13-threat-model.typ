= Threat Model & Security Audit

QuakeGuard's architecture implements a Zero-Trust model where the network is assumed to be hostile. The security model explicitly addresses spoofing, tampering, and denial-of-service via cryptographic enforcement.

== STRIDE Threat Analysis

#table(
  columns: (auto, auto, auto, auto),
  [*Threat Type*], [*Vector*], [*Mitigation*], [*Section*],
  [Spoofing], [Attacker injects fake seismic data], [ECDSA signatures required on all telemetry], [§3.1],
  [Tampering], [MITM alters event magnitude], [Payload hash (SHA-256) checked against signature], [§3.1],
  [Repudiation], [Node denies sending a false alert], [Public key strictly bound to Sensor ID at provisioning], [§3.2],
  [Info Disclosure], [Sniffing telemetry over WAN], [Data plane strictly enforces TLS 1.2+], [§3.3],
  [Denial of Service], [Replay attacks causing false alerts], [±300s Timestamp validation & Redis Geohash rate limits], [§3.4],
  [Elevation of Priv], [Node attempts to provision others], [Enrollment Token required for `/devices/register`], [§3.2]
)

== Out of Scope
The following vectors are explicitly out of scope for the current threat model:
- *Physical Compromise:* If an attacker gains physical access to the node, they could theoretically extract the private key from the ESP32's NVS or perform side-channel attacks during signing. Hardware Secure Elements (e.g., ATECC608A) are recommended for production deployments to mitigate this.
- *Sensor Spoofing:* Physically shaking the sensor to induce a false positive. Spatial correlation (Triangulation) mitigates this at the system level.

== Key Rotation and Revocation
In v2.0.0, key rotation is performed via manual re-provisioning. If a node is compromised, its public key can be revoked from the PostgreSQL database, immediately invalidating any future payloads signed by that key. Automated over-the-air (OTA) key rotation is planned for v2.1.
