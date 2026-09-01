= Executive Summary & Problem Statement

== The EEW Problem
Earthquake Early Warning (EEW) systems are critical infrastructures designed to detect the initial, less destructive P-waves of an earthquake and issue alerts before the damaging S-waves arrive. Historically, these systems have relied on extremely expensive, professional-grade seismometers deployed sparsely across national territories. This creates blind spots and high latency in areas far from the nearest professional sensor.

*QuakeGuard* solves this by democratizing seismic detection: it uses a dense network of low-cost IoT edge nodes (ESP32 + MEMS accelerometers) performing local DSP (Digital Signal Processing). By moving the initial detection to the edge and aggregating the triggers in a highly scalable, real-time cloud backend, QuakeGuard achieves the density required for instantaneous local warnings at a fraction of the cost.

== Target Users
- *Civil Protection & Emergency Responders:* For deploying rapid, dense sensor networks around critical infrastructure.
- *Seismological Researchers:* For gathering massive datasets of labeled MEMS accelerograms to complement professional networks.
- *Hobbyists & Citizen Scientists:* For contributing to a community-driven EEW network using inexpensive, off-the-shelf hardware.

== Key Performance Metrics
- *True Positive Rate (TPR):* ~80% (validated against INGV professional ground-truth data)
- *False Alarm Rate (FAR):* ~0% (achieved via multi-node spatial correlation and strict STA/LTA gating)
- *End-to-End Latency:* < 200ms from edge trigger to mobile alert broadcast

== Differentiators
While commercial and state-sponsored systems like *ShakeAlert*, or crowdsourced applications like *MyShake* and *Earthquake Network (EQN)* rely on smartphone sensors (which must filter out human movement, often restricting data collection to when the device is stationary and charging) or sparse professional seismometers, *QuakeGuard* occupies the "missing middle": dedicated, rigidly mounted IoT sensors running deterministic C++ DSP on bare-metal RTOS, ensuring zero latency variance and true always-on reliability.
