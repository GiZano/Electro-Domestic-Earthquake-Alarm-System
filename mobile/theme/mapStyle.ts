/**
 * Google Maps styling for the mobile map (Android).
 * Apple Maps on iOS ignores customMapStyle — callouts/badges are themed separately.
 * Light style complements dark so RESEARCH MODE matches the light theme.
 */

type ThemeTokens = {
  geometry: string;
  labelsTextFill: string;
  labelsTextStroke: string;
  administrative: string;
  adminCountry: string;
  poi: string;
  road: string;
  roadHighway: string;
  water: string;
};

const lightTokens: ThemeTokens = {
  geometry: "#f5f5f4",
  labelsTextFill: "#52525b",
  labelsTextStroke: "#fafaf9",
  administrative: "#e4e4e7",
  adminCountry: "#a1a1aa",
  poi: "#e7e5e4",
  road: "#ffffff",
  roadHighway: "#d6d3d1",
  water: "#bae6fd",
};

const darkTokens: ThemeTokens = {
  geometry: "#0f0f12",
  labelsTextFill: "#a1a1aa",
  labelsTextStroke: "#09090b",
  administrative: "#27272a",
  adminCountry: "#3f3f46",
  poi: "#18181b",
  road: "#1c1c21",
  roadHighway: "#232328",
  water: "#0c0c10",
};

function commonEntries(t: ThemeTokens) {
  return [
    { elementType: "geometry", stylers: [{ color: t.geometry }] },
    { elementType: "labels.text.fill", stylers: [{ color: t.labelsTextFill }] },
    { elementType: "labels.text.stroke", stylers: [{ color: t.labelsTextStroke }] },
    { featureType: "administrative", elementType: "geometry", stylers: [{ color: t.administrative }] },
    { featureType: "administrative.country", elementType: "geometry.stroke", stylers: [{ color: t.adminCountry }] },
    { featureType: "poi", elementType: "geometry", stylers: [{ color: t.poi }] },
    { featureType: "road", elementType: "geometry", stylers: [{ color: t.road }] },
    { featureType: "road.highway", elementType: "geometry", stylers: [{ color: t.roadHighway }] },
    { featureType: "water", elementType: "geometry", stylers: [{ color: t.water }] },
  ];
}

export const lightMapStyle = commonEntries(lightTokens);

export const darkMapStyle = [
  ...commonEntries(darkTokens),
  { elementType: "labels.icon", stylers: [{ visibility: "off" }] },
  { featureType: "administrative.province", elementType: "geometry.stroke", stylers: [{ color: "#3f3f46" }] },
  { featureType: "landscape", elementType: "geometry", stylers: [{ color: "#101014" }] },
  { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#27272a" }] },
];
