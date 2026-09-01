= Cryptographic Security & Provisioning

QuakeGuard implements a Zero-Trust security model for its IoT edge nodes[cite: 1]. To prevent rogue devices from injecting false seismic data (spoofing) or re-transmitting old events (replay attacks), the system relies on asymmetric cryptography and strict temporal validation[cite: 1].

== Cryptographic Identity (ECDSA)

Upon its first boot, the ESP32-C3 utilizes the `mbedtls` library to generate a unique Elliptic Curve Digital Signature Algorithm (ECDSA) key pair using the NIST P-256 curve (`secp256r1`)[cite: 1]. 
- *Private Key:* Stored securely and permanently in the device's Non-Volatile Storage (NVS)[cite: 1]. It never leaves the device and is used exclusively to sign outgoing telemetry[cite: 1].
- *Public Key:* Extracted in DER format, converted to a hexadecimal string, and acts as the unforgeable cryptographic identity of the sensor within the backend database[cite: 1].

== Automated Provisioning Handshake

Before transmitting any seismic data, an unregistered sensor must complete an automated handshake with the Control Plane[cite: 1]:
+ The device sends a POST request to the `/devices/register` endpoint, providing its generated `public_key_hex`, MAC address, GPS coordinates, and a hardcoded `ENROLLMENT_TOKEN`[cite: 1].
+ The backend validates the factory enrollment token to ensure the device is authorized to join the network[cite: 1].
+ Using a geohash-based Redis fast-path index with an authoritative PostGIS fallback (`ST_Contains`), the backend spatially evaluates the provided GPS coordinates against the predefined zones and assigns the sensor to the smallest containing geographic polygon[cite: 1]. When a GNSS module is attached, the coordinates are the live fix (or the last-known fix persisted in NVS); otherwise the node reports a hardcoded placeholder until provisioned in place[cite: 1].
+ A unique `sensor_id` is returned to the device, which saves it to NVS for all future communications[cite: 1].

#figure(
  image("assets/03-security.png", width: 80%),
  caption: [_Provisioning Handshake Sequence_]
)

== Payload Authentication & Integrity

When a seismic event triggers the DSP pipeline, the firmware constructs a string containing the measured magnitude and the current timestamp (format: `value:timestamp`)[cite: 1]. Under normal operation the timestamp is the NTP-synchronized wall time; when the serial fallback drains the retention ring it is the software wall clock `epochAtSync + millis()` at drain time, and the payload is *re-signed* with the current time so the backend's replay window accepts it[cite: 1]. This string is hashed via SHA-256 and signed with the device's private key[cite: 1]. 

The resulting JSON payload includes the data, the timestamp, and the `signature_hex` — identical on the MQTT and serial data planes (`[QG:FB]` frames carry the same JSON behind the marker)[cite: 1]. Once received by the backend, the `validate_iot_payload` dependency pipeline enforces four security gates[cite: 1]:
- *API Key Verification:* Validates the `X-API-Key` header using a constant-time comparison (`hmac.compare_digest`) to prevent timing attacks[cite: 1].
- *Sensor Status:* Confirms the sensor ID exists and is marked as `active` in the PostgreSQL database[cite: 1].
- *Anti-Replay Protection:* Compares the device's timestamp against the server's UTC time. Payloads older than a 300-second threshold are outright rejected with a `403 Forbidden` error[cite: 1].
- *Signature Verification:* The backend utilizes the Python `cryptography` library to verify the ECDSA signature against the public key associated with that sensor[cite: 1]. The implementation robustly supports both DER-encoded signatures (native to MbedTLS) and raw concatenated $r || s$ signatures[cite: 1].