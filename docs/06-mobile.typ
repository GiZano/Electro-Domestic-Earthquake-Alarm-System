= Mobile Client & Live Telemetry

The client-side presentation layer of QuakeGuard is a cross-platform mobile application built with React Native and the Expo framework[cite: 1]. It serves as the primary interface for users to monitor the seismic network and receive instantaneous Earthquake Early Warning (EEW) notifications[cite: 1].

== Real-Time Alerting (WebSockets)

To guarantee sub-second delivery of critical alerts, the mobile app maintains a persistent, full-duplex connection to the backend via WebSockets[cite: 1].
- *Connection Management:* The `WebSocketContext` initializes a connection to the `/ws/alerts` endpoint, authenticating via a secure query parameter (`MOBILE_WS_TOKEN`)[cite: 1]. The client implements an exponential backoff strategy for automatic reconnections up to a maximum delay of 30 seconds[cite: 1].
- *Native Haptics & Notifications:* When the WebSocket receives a payload tagged as `"CRITICAL"`, the application bypasses standard UI updates and immediately triggers native hardware APIs[cite: 1]. It executes an SOS vibration pattern (`Vibration.vibrate`) and schedules a high-priority system push notification using `expo-notifications` (`AndroidImportance.MAX`), ensuring the user is alerted even if the app is in the background[cite: 1].

== Telemetry Visualization & State

The dashboard provides a live view of the network's health and recent seismic activity, relying on a robust state management architecture[cite: 1].
- *Data Fetching (TanStack Query):* Standard REST operations, such as fetching the active sensor list and the latest telemetry points (`/readings/`), are managed by React Query[cite: 1]. This provides automatic caching, background refetching (every 2 seconds for live readings), and loading state management[cite: 1].
- *Per-Zone Live Seismograph:* Since v1.2.1 the dashboard no longer mixes network-wide telemetry. A horizontal strip of zone chips (`ZoneSelector`) lets the operator pick a monitored polygon, and a `VictoryChart` (`victory-native`) renders that zone's live trace from `GET /zones/{zone_id}/readings?limit=60`[cite: 1]. The trace is anchored to the wall clock: a 60-sample / 30-second sliding window that naturally drops stale readings, uses a linear MAG scale (MIN 3.5 / MED 4.0 / ALTO 4.5) with the axis pinned left, and always renders inside the plot[cite: 1]. Raw Z-axis acceleration is converted to magnitude with the same normalization used by the backend[cite: 1].
- *Geospatial Map:* The `react-native-maps` library maps the network topology, displaying custom markers for each sensor based on their exact PostGIS coordinates and coloring them according to their active/offline status[cite: 1].

== GPS Zone Detection & Alert Scoping

The Settings screen ships a "Detect my zone via GPS" action (`DETECT`)[cite: 1].
- *Flow:* `expo-location` requests foreground permission and captures a balanced-accuracy fix, then calls `GET /zones/locate?latitude=...&longitude=...` to resolve the fix into its containing monitored zone[cite: 1].
- *Outcome:* The resolved zone becomes the operator's `homeZoneId` (persisted in `usePreferencesStore`). Incoming CRITICAL alerts are gated by `ringsForZone()`: they ring, vibrate, and notify only when they match the home zone (or when no home zone is set — "ALL REGIONS")[cite: 1].
- *Error Handling:* A 404 ("coordinates outside any monitored polygon") prompts "Outside monitored area"; manual zone chips remain as a fallback[cite: 1].

== Dual Theme (MIC / RESEARCH Mode)

The appearance layer ships two operator modes toggled from Settings[cite: 1]:
- *MIC MODE (dark):* `themeMode: 'dark'` — a zinc-950 tactical palette with emerald/amber/red semantic accents[cite: 1].
- *RESEARCH MODE (light):* `themeMode: 'light'` — a slate-50 "scientific paper" palette for lab analysis[cite: 1].
The active theme propagates through `useAppTheme()` to every screen, the seismograph's Victory theme, the tab bar, and the Google Map styles (Android)[cite: 1].

== Resilience and Global State (Zustand)

Global application state, including alert history and user preferences, is managed using Zustand[cite: 1].
- *Alert Store:* The `useAlertStore` maintains a rolling history of the 10 most recent alerts, persisting them for the dashboard's activity log[cite: 1]. Each row can embed the matching AI Emergency Report (summary + per-item recommendations), and a dedicated `AiReportCard` renders the latest report banner inline[cite: 1].
- *Siren Audio:* On a matching CRITICAL alert the app plays a civil-defense siren (`expo-audio`, looping the bundled `alarm.wav` for a bounded 15-second window, auto-stopped and non-overlapping) alongside the native SOS `Vibration.vibrate` pattern and a MAX-priority push notification[cite: 1].
- *Offline Mode:* The `usePreferencesStore` controls a user-toggled "Offline Mode"[cite: 1]. When activated, the application cleanly and intentionally closes the active WebSocket connection and disables all React Query background polling (`enabled: !isOfflineMode`), effectively halting network traffic and conserving battery life during maintenance or low-power situations[cite: 1].