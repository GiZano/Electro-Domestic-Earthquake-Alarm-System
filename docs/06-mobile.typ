= Mobile Client & Live Telemetry

The client-side presentation layer of QuakeGuard is a cross-platform mobile application built with React Native and the Expo framework[cite: 1]. It serves as the primary interface for users to monitor the seismic network and receive instantaneous Earthquake Early Warning (EEW) notifications[cite: 1].

== Real-Time Alerting (WebSockets)

To guarantee sub-second delivery of critical alerts, the mobile app maintains a persistent, full-duplex connection to the backend via WebSockets[cite: 1].
- *Connection Management:* The `WebSocketContext` initializes a connection to the `/ws/alerts` endpoint, authenticating via a secure query parameter (`MOBILE_WS_TOKEN`)[cite: 1]. The client implements an exponential backoff strategy for automatic reconnections up to a maximum delay of 30 seconds[cite: 1].
- *Native Haptics & Notifications:* When the WebSocket receives a payload tagged as `"CRITICAL"`, the application bypasses standard UI updates and immediately triggers native hardware APIs[cite: 1]. It executes an SOS vibration pattern (`Vibration.vibrate`) and schedules a high-priority system push notification using `expo-notifications` (`AndroidImportance.MAX`), ensuring the user is alerted even if the app is in the background[cite: 1].

== Telemetry Visualization & State

The dashboard provides a live view of the network's health and recent seismic activity, relying on a robust state management architecture[cite: 1].
- *Data Fetching (TanStack Query):* Standard REST operations, such as fetching the active sensor list and the latest telemetry points (`/readings/`), are managed by React Query[cite: 1]. This provides automatic caching, background refetching (every 2 seconds for live readings), and loading state management[cite: 1].
- *Live Seismograph:* The raw telemetry data is fed into a `VictoryChart` component (`victory-native`), which renders a dynamic line chart representing the network's aggregated seismic activity in real-time[cite: 1].
- *Geospatial Map:* The `react-native-maps` library maps the network topology, displaying custom markers for each sensor based on their exact PostGIS coordinates and coloring them according to their active/offline status[cite: 1].

== Resilience and Global State (Zustand)

Global application state, including alert history and user preferences, is managed using Zustand[cite: 1].
- *Alert Store:* The `useAlertStore` maintains a rolling history of the 10 most recent alerts, persisting them for the dashboard's activity log[cite: 1].
- *Offline Mode:* The `usePreferencesStore` controls a user-toggled "Offline Mode"[cite: 1]. When activated, the application cleanly and intentionally closes the active WebSocket connection and disables all React Query background polling (`enabled: !isOfflineMode`), effectively halting network traffic and conserving battery life during maintenance or low-power situations[cite: 1].