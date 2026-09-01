= Limitations & State of the Art Comparison

== Known Limitations
While QuakeGuard provides a robust foundation for community EEW, several limitations exist in the v2.0.0 architecture:
- *Single Point of Failure (Broker):* The system currently relies on a single HiveMQ Cloud cluster for MQTT telemetry. A network partition or broker outage breaks the data plane, though the Zero-Trust serial fallback mitigates this for local deployments.
- *TPR Limits on Cheap Hardware:* The ADXL345 sensor has an inherently higher noise floor compared to professional episensors, capping the theoretical True Positive Rate (TPR) at ~80% when validated against the INGV SIL dataset.
- *Macro-Region Alerting:* The triangulation algorithm computes the epicenter, but alerts are still broadcasted at the macro-zone level, potentially warning users who are outside the destructive radius.

== State of the Art Comparison
QuakeGuard sits between massive government systems and smartphone-based crowdsourcing.

#table(
  columns: (1fr, 1.2fr, 1fr, 1.3fr),
  [*Feature*], [*QuakeGuard (v2.0)*], [*ShakeAlert*], [*MyShake / EQN*],
  [Hardware], [Dedicated Edge IoT], [Professional], [Smartphones],
  [Latency], [< 200 ms], [< 5 s], [Variable (1-10 s)],
  [Coupling Noise], [Low (Rigid mount)], [Very Low], [High (Pockets, tables)],
  [Cost/Node], [~ $15 USD], [>$10,000 USD], [Free (BYOD)]
)

QuakeGuard offers deterministic latency and low coupling noise like ShakeAlert, but at the democratization scale of MyShake and Earthquake Network (EQN).
