/**
 * Dark map styling for the Google Maps provider (Android).
 * Apple Maps on iOS does not support customMapStyle, so it stays standard
 * while callouts/badges are themed dark.
 */
/**
 * Light map styling for the Google Maps provider (Android).
 * Complements `darkMapStyle` above so RESEARCH MODE matches the light theme
 * instead of forcing the dark console onto operators who switched.
 */
export const lightMapStyle = [
  {
    elementType: "geometry",
    stylers: [{ color: "#f5f5f4" }],
  },
  {
    elementType: "labels.text.fill",
    stylers: [{ color: "#52525b" }],
  },
  {
    elementType: "labels.text.stroke",
    stylers: [{ color: "#fafaf9" }],
  },
  {
    featureType: "administrative",
    elementType: "geometry",
    stylers: [{ color: "#e4e4e7" }],
  },
  {
    featureType: "administrative.country",
    elementType: "geometry.stroke",
    stylers: [{ color: "#a1a1aa" }],
  },
  {
    featureType: "poi",
    elementType: "geometry",
    stylers: [{ color: "#e7e5e4" }],
  },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#ffffff" }],
  },
  {
    featureType: "road.highway",
    elementType: "geometry",
    stylers: [{ color: "#d6d3d1" }],
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#bae6fd" }],
  },
] as const;

export const darkMapStyle = [
  {
    elementType: "geometry",
    stylers: [{ color: "#0f0f12" }],
  },
  {
    elementType: "labels.text.fill",
    stylers: [{ color: "#a1a1aa" }],
  },
  {
    elementType: "labels.text.stroke",
    stylers: [{ color: "#09090b" }],
  },
  {
    elementType: "labels.icon",
    stylers: [{ visibility: "off" }],
  },
  {
    featureType: "administrative",
    elementType: "geometry",
    stylers: [{ color: "#27272a" }],
  },
  {
    featureType: "administrative.country",
    elementType: "geometry.stroke",
    stylers: [{ color: "#3f3f46" }],
  },
  {
    featureType: "administrative.province",
    elementType: "geometry.stroke",
    stylers: [{ color: "#3f3f46" }],
  },
  {
    featureType: "landscape",
    elementType: "geometry",
    stylers: [{ color: "#101014" }],
  },
  {
    featureType: "poi",
    elementType: "geometry",
    stylers: [{ color: "#18181b" }],
  },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#1c1c21" }],
  },
  {
    featureType: "road",
    elementType: "geometry.stroke",
    stylers: [{ color: "#27272a" }],
  },
  {
    featureType: "road.highway",
    elementType: "geometry",
    stylers: [{ color: "#232328" }],
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#0c0c10" }],
  },
] as const;
