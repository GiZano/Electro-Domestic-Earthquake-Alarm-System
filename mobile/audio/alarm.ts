import { createAudioPlayer, setAudioModeAsync, AudioPlayer } from "expo-audio";

/**
 * Civil-defense siren player. Played on critical alerts matching the
 * operator's own zone (see WebSocketContext). Loops for a bounded window and
 * auto-stops, so it never rings forever and never overlaps a second alarm.
 */
let player: AudioPlayer | null = null;
let stopTimer: ReturnType<typeof setTimeout> | null = null;

const ALARM_SOURCE = require("../assets/sounds/alarm.wav");

function ensurePlayer(): AudioPlayer {
  if (!player) {
    player = createAudioPlayer(ALARM_SOURCE);
    player.loop = true;
    player.volume = 1;
  }
  return player;
}

export async function playAlarm(durationMs: number = 15000): Promise<void> {
  try {
    await setAudioModeAsync({ playsInSilentMode: true });
    const p = ensurePlayer();
    stopAlarm();
    await p.seekTo(0);
    p.play();
    if (durationMs > 0) {
      stopTimer = setTimeout(() => stopAlarm(), durationMs);
    }
  } catch (err) {
    console.warn("⚠️ Alarm playback failed:", err);
  }
}

export function stopAlarm(): void {
  if (stopTimer) {
    clearTimeout(stopTimer);
    stopTimer = null;
  }
  try {
    player?.pause();
  } catch {
    // ignore — player may already be released
  }
}