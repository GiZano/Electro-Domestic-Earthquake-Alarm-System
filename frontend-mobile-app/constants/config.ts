/**
 * Application Configuration.
 * Defines the base URL for the backend API.
 * * NOTE: Replace the IP address with your local machine's IP address
 * to ensure accessibility from physical devices or emulators.
 */

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL as string;

// Centralized Security Secrets
export const IOT_API_KEY = process.env.EXPO_PUBLIC_IOT_API_KEY as string;
export const MOBILE_WS_TOKEN = process.env.EXPO_PUBLIC_MOBILE_WS_TOKEN as string;

// Fail-fast logic for the frontend
if (!IOT_API_KEY || !MOBILE_WS_TOKEN) {
    console.warn("⚠️ CRITICAL WARNING: Missing EXPO_PUBLIC environment variables in frontend!")
}
